"""A tiny in-memory, content-addressed versioned key-value database.

This is intentionally a demo, not a production database.  Nodes are immutable
Python dictionaries stored by the SHA-256 hash of their canonical JSON form.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class CommitStats:
    version: int
    new_nodes: int
    reused_nodes: int

    @property
    def total_nodes(self) -> int:
        return self.new_nodes + self.reused_nodes

    @property
    def shared_percent(self) -> float:
        if self.total_nodes == 0:
            return 0.0
        return 100.0 * self.reused_nodes / self.total_nodes

    def __str__(self) -> str:
        return (
            f"commit v{self.version}: {self.new_nodes} new nodes, "
            f"{self.reused_nodes} reused ({self.shared_percent:.1f}% shared)"
        )


@dataclass(frozen=True)
class DiffStats:
    nodes_compared: int
    matching_subtrees_skipped: int

    def __str__(self) -> str:
        return (
            f"{self.nodes_compared} node pairs compared, "
            f"{self.matching_subtrees_skipped} matching subtrees skipped"
        )


class VersionedDatabase:
    """An in-memory persistent hash trie with content-addressed nodes."""

    def __init__(self, branching_factor: int = 8, tree_depth: int = 4) -> None:
        if branching_factor < 2 or branching_factor & (branching_factor - 1):
            raise ValueError("branching_factor must be a power of two")
        if tree_depth < 1:
            raise ValueError("tree_depth must be at least 1")

        self.branching_factor = branching_factor
        self.tree_depth = tree_depth
        self._bits_per_level = int(math.log2(branching_factor))

        # Hash -> {"type": "internal", "children": {...}} or leaf entries.
        self.node_store: dict[str, dict[str, Any]] = {}
        self.versions: dict[int, str] = {}
        self.commit_stats: dict[int, CommitStats] = {}
        self.last_diff_stats = DiffStats(0, 0)

    @staticmethod
    def _canonical_bytes(value: Any) -> bytes:
        try:
            text = json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise TypeError("keys must be strings and values must be JSON-serializable") from exc
        return text.encode("utf-8")

    def _node_hash(self, node: dict[str, Any]) -> str:
        return hashlib.sha256(self._canonical_bytes(node)).hexdigest()

    def _route(self, key: str) -> tuple[int, ...]:
        digest_as_int = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest(), "big")
        total_bits = 256
        slots = []
        for level in range(self.tree_depth):
            shift = total_bits - self._bits_per_level * (level + 1)
            slots.append((digest_as_int >> shift) & (self.branching_factor - 1))
        return tuple(slots)

    def commit(self, state: Mapping[str, Any]) -> str:
        """Commit a complete key-value state and return its root hash."""
        if any(not isinstance(key, str) for key in state):
            raise TypeError("all keys must be strings")

        # Validate values before mutating the node store.
        self._canonical_bytes(dict(state))
        existing_before_commit = set(self.node_store)
        created_this_commit: set[str] = set()
        new_nodes = 0
        reused_nodes = 0

        def intern(node: dict[str, Any]) -> str:
            nonlocal new_nodes, reused_nodes
            node_hash = self._node_hash(node)
            if node_hash in existing_before_commit or node_hash in created_this_commit:
                reused_nodes += 1
            else:
                self.node_store[node_hash] = node
                created_this_commit.add(node_hash)
                new_nodes += 1
            return node_hash

        routed = [(self._route(key), key, value) for key, value in state.items()]

        def build(items: list[tuple[tuple[int, ...], str, Any]], depth: int) -> str:
            if depth == self.tree_depth:
                entries = [[key, value] for _, key, value in sorted(items, key=lambda row: row[1])]
                return intern({"type": "leaf", "entries": entries})

            groups: dict[int, list[tuple[tuple[int, ...], str, Any]]] = {}
            for item in items:
                groups.setdefault(item[0][depth], []).append(item)
            children = {
                str(slot): build(group, depth + 1)
                for slot, group in sorted(groups.items())
            }
            return intern({"type": "internal", "children": children})

        root_hash = build(routed, 0)
        version = len(self.versions) + 1
        self.versions[version] = root_hash
        self.commit_stats[version] = CommitStats(version, new_nodes, reused_nodes)
        return root_hash

    def diff(self, left_root: str, right_root: str) -> list[str]:
        """Return changed keys, pruning every subtree whose root hashes match."""
        self._require_root(left_root)
        self._require_root(right_root)
        changed: set[str] = set()
        nodes_compared = 0
        matching_subtrees_skipped = 0

        def all_entries(node_hash: Optional[str]) -> dict[str, Any]:
            if node_hash is None:
                return {}
            node = self.node_store[node_hash]
            if node["type"] == "leaf":
                return dict(node["entries"])
            result: dict[str, Any] = {}
            for child_hash in node["children"].values():
                result.update(all_entries(child_hash))
            return result

        def walk(left_hash: Optional[str], right_hash: Optional[str]) -> None:
            nonlocal nodes_compared, matching_subtrees_skipped
            nodes_compared += 1

            # The central optimization: equal hash means equal complete subtree.
            if left_hash == right_hash:
                if left_hash is not None:
                    matching_subtrees_skipped += 1
                return

            if left_hash is None or right_hash is None:
                changed.update(all_entries(left_hash))
                changed.update(all_entries(right_hash))
                return

            left = self.node_store[left_hash]
            right = self.node_store[right_hash]
            if left["type"] == "internal" and right["type"] == "internal":
                slots = set(left["children"]) | set(right["children"])
                for slot in sorted(slots, key=int):
                    walk(left["children"].get(slot), right["children"].get(slot))
                return

            if left["type"] == "leaf" and right["type"] == "leaf":
                left_entries = dict(left["entries"])
                right_entries = dict(right["entries"])
            else:
                # Defensive fallback if differently configured trees are ever mixed.
                left_entries = all_entries(left_hash)
                right_entries = all_entries(right_hash)

            for key in set(left_entries) | set(right_entries):
                if key not in left_entries or key not in right_entries:
                    changed.add(key)
                elif left_entries[key] != right_entries[key]:
                    changed.add(key)

        walk(left_root, right_root)
        self.last_diff_stats = DiffStats(nodes_compared, matching_subtrees_skipped)
        return sorted(changed)

    def _require_root(self, root_hash: str) -> None:
        if root_hash not in self.node_store:
            raise KeyError(f"unknown root hash: {root_hash}")

