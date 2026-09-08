"""Revon: a content-addressed, incrementally versioned key-value store.

The state index is a persistent fixed-depth Merkle hash trie. A batch update
copies only the paths touched by changed keys; every unaffected subtree is
reused by hash. Commits and changesets are content-addressed as well, while
small integer versions remain available as convenient display identifiers.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Optional


@dataclass(frozen=True)
class CommitStats:
    """Construction work for one version."""

    version: int
    new_nodes: int
    reused_nodes: int
    bytes_written: int = 0
    changed_keys: int = 0

    @property
    def total_nodes(self) -> int:
        return self.new_nodes + self.reused_nodes

    @property
    def shared_percent(self) -> float:
        if self.total_nodes == 0:
            return 100.0
        return 100.0 * self.reused_nodes / self.total_nodes

    def __str__(self) -> str:
        return (
            f"commit v{self.version}: {self.new_nodes} new nodes, "
            f"{self.reused_nodes} existing references encountered, "
            f"{self.bytes_written} trie bytes written"
        )


@dataclass(frozen=True)
class ChangeOperation:
    """One effective key transition stored in a commit changeset."""

    key: str
    old_exists: bool
    old_value: Any
    new_exists: bool
    new_value: Any

    @property
    def change_type(self) -> str:
        if not self.old_exists:
            return "added"
        if not self.new_exists:
            return "deleted"
        return "modified"

    def as_record(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "old_exists": self.old_exists,
            "old": self.old_value,
            "new_exists": self.new_exists,
            "new": self.new_value,
        }


@dataclass(frozen=True)
class DiffEntry:
    """A structured, frontend-ready difference between two versions."""

    key: str
    change_type: str
    old_value: Any
    new_value: Any


@dataclass(frozen=True)
class Commit:
    version: int
    commit_hash: str
    root_hash: str
    parent: Optional[int]
    parent_hash: Optional[str]
    message: Optional[str]
    timestamp_ns: int
    changeset_hash: str

    @property
    def timestamp(self) -> float:
        """Compatibility view for callers that expect seconds."""
        return self.timestamp_ns / 1_000_000_000

    def __str__(self) -> str:
        parent = f"v{self.parent}" if self.parent is not None else "(root)"
        return (
            f"v{self.version} <- {parent} {self.commit_hash[:12]} "
            f"root={self.root_hash[:12]} {self.message or '(no message)'}"
        )


@dataclass(frozen=True)
class DiffStats:
    nodes_compared: int = 0
    matching_subtrees_skipped: int = 0
    leaf_entries_examined: int = 0
    log_operations_examined: int = 0
    strategy: str = "merkle"

    def __str__(self) -> str:
        if self.strategy == "log":
            return f"log diff: {self.log_operations_examined} operations examined"
        return (
            f"Merkle diff: {self.nodes_compared} node pairs compared, "
            f"{self.matching_subtrees_skipped} matching subtrees skipped, "
            f"{self.leaf_entries_examined} leaf entries examined"
        )


@dataclass(frozen=True)
class StructuralSharingStats:
    """Exact reachable-node overlap between two immutable roots."""

    left_nodes: int
    right_nodes: int
    shared_nodes: int

    @property
    def right_shared_percent(self) -> float:
        if self.right_nodes == 0:
            return 100.0
        return 100.0 * self.shared_nodes / self.right_nodes


class VersionedDatabase:
    """An in-memory persistent fixed-depth Merkle hash trie."""

    def __init__(
        self,
        branching_factor: int = 8,
        tree_depth: int = 4,
        hybrid_log_threshold: int = 128,
    ) -> None:
        if branching_factor < 2 or branching_factor & (branching_factor - 1):
            raise ValueError("branching_factor must be a power of two")
        if tree_depth < 1:
            raise ValueError("tree_depth must be at least 1")
        if int(math.log2(branching_factor)) * tree_depth > 256:
            raise ValueError("tree routing cannot consume more than 256 hash bits")
        if hybrid_log_threshold < 0:
            raise ValueError("hybrid_log_threshold cannot be negative")

        self.branching_factor = branching_factor
        self.tree_depth = tree_depth
        self.hybrid_log_threshold = hybrid_log_threshold
        self._bits_per_level = int(math.log2(branching_factor))

        self.node_store: dict[str, dict[str, Any]] = {}
        self.versions: dict[int, str] = {}
        self.commits: dict[int, Commit] = {}
        self.commit_store: dict[str, dict[str, Any]] = {}
        self.changeset_store: dict[str, tuple[ChangeOperation, ...]] = {}
        self.version_commits: dict[int, str] = {}
        self.head: Optional[int] = None
        self.head_hash: Optional[str] = None
        self.commit_stats: dict[int, CommitStats] = {}
        self.last_diff_stats = DiffStats()
        # Newly interned trie objects from the latest successful write. Durable
        # stores use this delta so an incremental commit never scans all nodes.
        self.last_new_node_hashes: tuple[str, ...] = ()

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
            raise TypeError(
                "keys must be strings and values must be JSON-serializable"
            ) from exc
        return text.encode("utf-8")

    @classmethod
    def _content_hash(cls, kind: str, value: Any) -> str:
        payload = b"revon:" + kind.encode("ascii") + b":v1\x00"
        return hashlib.sha256(payload + cls._canonical_bytes(value)).hexdigest()

    def _node_hash(self, node: dict[str, Any]) -> str:
        # Trie node hashes remain stable across repository operations.
        return hashlib.sha256(self._canonical_bytes(node)).hexdigest()

    def _route(self, key: str) -> tuple[int, ...]:
        digest_as_int = int.from_bytes(
            hashlib.sha256(key.encode("utf-8")).digest(), "big"
        )
        slots = []
        for level in range(self.tree_depth):
            shift = 256 - self._bits_per_level * (level + 1)
            slots.append((digest_as_int >> shift) & (self.branching_factor - 1))
        return tuple(slots)

    def _record_version(
        self,
        root_hash: str,
        message: Optional[str],
        changes: Iterable[ChangeOperation],
        new_nodes: int,
        reused_nodes: int,
        bytes_written: int,
    ) -> Commit:
        version = len(self.versions) + 1
        parent_version = self.head
        parent_hash = (
            self.version_commits[parent_version]
            if parent_version is not None
            else None
        )
        ordered_changes = tuple(sorted(changes, key=lambda change: change.key))
        change_records = [change.as_record() for change in ordered_changes]
        changeset_hash = self._content_hash("changeset", change_records)
        self.changeset_store.setdefault(changeset_hash, ordered_changes)

        timestamp_ns = time.time_ns()
        commit_payload = {
            "type": "commit",
            "root": root_hash,
            "parent": parent_hash,
            "message": message or "",
            "timestamp_ns": timestamp_ns,
            "changeset": changeset_hash,
        }
        commit_hash = self._content_hash("commit", commit_payload)
        self.commit_store[commit_hash] = commit_payload
        record = Commit(
            version=version,
            commit_hash=commit_hash,
            root_hash=root_hash,
            parent=parent_version,
            parent_hash=parent_hash,
            message=message,
            timestamp_ns=timestamp_ns,
            changeset_hash=changeset_hash,
        )
        self.versions[version] = root_hash
        self.commits[version] = record
        self.version_commits[version] = commit_hash
        self.commit_stats[version] = CommitStats(
            version,
            new_nodes,
            reused_nodes,
            bytes_written,
            len(ordered_changes),
        )
        self.head = version
        self.head_hash = commit_hash
        return record

    def _changes_between_states(
        self, old: Mapping[str, Any], new: Mapping[str, Any]
    ) -> tuple[ChangeOperation, ...]:
        changes: list[ChangeOperation] = []
        for key in sorted(set(old) | set(new)):
            old_exists = key in old
            new_exists = key in new
            if old_exists and new_exists and old[key] == new[key]:
                continue
            changes.append(
                ChangeOperation(
                    key,
                    old_exists,
                    old.get(key),
                    new_exists,
                    new.get(key),
                )
            )
        return tuple(changes)

    def commit(self, state: Mapping[str, Any], message: Optional[str] = None) -> str:
        """Build a complete state; use ``apply_changes`` for later updates."""
        if any(not isinstance(key, str) for key in state):
            raise TypeError("all keys must be strings")
        self._canonical_bytes(dict(state))

        previous = self.materialize(self.versions[self.head]) if self.head else {}
        changes = self._changes_between_states(previous, state)
        existing_before_commit = set(self.node_store)
        created_this_commit: set[str] = set()
        new_nodes = 0
        reused_nodes = 0
        bytes_written = 0

        def intern(node: dict[str, Any]) -> str:
            nonlocal new_nodes, reused_nodes, bytes_written
            encoded = self._canonical_bytes(node)
            node_hash = hashlib.sha256(encoded).hexdigest()
            if node_hash in existing_before_commit or node_hash in created_this_commit:
                reused_nodes += 1
            else:
                self.node_store[node_hash] = node
                created_this_commit.add(node_hash)
                new_nodes += 1
                bytes_written += len(encoded)
            return node_hash

        routed = [(self._route(key), key, value) for key, value in state.items()]

        def build(items: list[tuple[tuple[int, ...], str, Any]], depth: int) -> str:
            if depth == self.tree_depth:
                entries = [
                    [key, value]
                    for _, key, value in sorted(items, key=lambda row: row[1])
                ]
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
        self.last_new_node_hashes = tuple(sorted(created_this_commit))
        self._record_version(
            root_hash,
            message,
            changes,
            new_nodes,
            reused_nodes,
            bytes_written,
        )
        return root_hash

    def get(self, root_hash: str, key: str) -> Any:
        """Read one key from one immutable root without materializing it."""
        if not isinstance(key, str):
            raise TypeError("all keys must be strings")
        self._require_root(root_hash)
        current: Optional[str] = root_hash
        path = self._route(key)
        for level in range(self.tree_depth):
            node = self.node_store[current] if current is not None else None
            if node is None or node["type"] != "internal":
                raise KeyError(key)
            current = node["children"].get(str(path[level]))
            if current is None:
                raise KeyError(key)
        leaf = self.node_store[current]
        for entry_key, entry_value in leaf["entries"]:
            if entry_key == key:
                return entry_value
        raise KeyError(key)

    def apply_changes(
        self,
        root_hash: str,
        *,
        puts: Optional[Mapping[str, Any]] = None,
        deletes: Optional[Iterable[str]] = None,
        message: Optional[str] = None,
    ) -> str:
        """Atomically apply a batch by copying only its unique routed paths."""
        self._require_root(root_hash)
        if self.head is not None and self.versions[self.head] != root_hash:
            raise ValueError(
                "writes must target HEAD; branch creation is not implemented"
            )
        put_values = dict(puts or {})
        delete_keys = set(deletes or ())
        if any(not isinstance(key, str) for key in put_values) or any(
            not isinstance(key, str) for key in delete_keys
        ):
            raise TypeError("all keys must be strings")
        overlap = set(put_values) & delete_keys
        if overlap:
            raise ValueError(f"keys cannot be both put and deleted: {sorted(overlap)}")
        self._canonical_bytes(put_values)

        operations: list[ChangeOperation] = []
        effective_puts: dict[str, Any] = {}
        for key in sorted(put_values):
            try:
                old_value = self.get(root_hash, key)
                old_exists = True
            except KeyError:
                old_value = None
                old_exists = False
            if old_exists and old_value == put_values[key]:
                continue
            effective_puts[key] = put_values[key]
            operations.append(
                ChangeOperation(key, old_exists, old_value, True, put_values[key])
            )

        for key in sorted(delete_keys):
            try:
                old_value = self.get(root_hash, key)
            except KeyError as exc:
                raise KeyError(f"key not present in this version: {key}") from exc
            operations.append(ChangeOperation(key, True, old_value, False, None))

        mutations: dict[tuple[int, ...], dict[str, tuple[bool, Any]]] = {}
        for key, value in effective_puts.items():
            mutations.setdefault(self._route(key), {})[key] = (True, value)
        for key in delete_keys:
            mutations.setdefault(self._route(key), {})[key] = (False, None)

        new_nodes = 0
        reused_nodes = 0
        bytes_written = 0
        created_this_commit: set[str] = set()

        def intern(node: dict[str, Any]) -> str:
            nonlocal new_nodes, reused_nodes, bytes_written
            encoded = self._canonical_bytes(node)
            node_hash = hashlib.sha256(encoded).hexdigest()
            if node_hash in self.node_store:
                reused_nodes += 1
            else:
                self.node_store[node_hash] = node
                created_this_commit.add(node_hash)
                new_nodes += 1
                bytes_written += len(encoded)
            return node_hash

        def rewrite(
            node_hash: Optional[str],
            level: int,
            routed_changes: dict[tuple[int, ...], dict[str, tuple[bool, Any]]],
        ) -> Optional[str]:
            nonlocal reused_nodes
            if level == self.tree_depth:
                leaf = self.node_store[node_hash] if node_hash is not None else None
                entries = dict(leaf["entries"]) if leaf is not None else {}
                for changes_for_leaf in routed_changes.values():
                    for key, (exists, value) in changes_for_leaf.items():
                        if exists:
                            entries[key] = value
                        else:
                            entries.pop(key, None)
                if not entries:
                    return None
                return intern(
                    {
                        "type": "leaf",
                        "entries": [[key, entries[key]] for key in sorted(entries)],
                    }
                )

            node = self.node_store[node_hash] if node_hash is not None else None
            children = dict(node["children"]) if node is not None else {}
            grouped: dict[int, dict[tuple[int, ...], dict[str, tuple[bool, Any]]]] = {}
            for path, changes_for_leaf in routed_changes.items():
                grouped.setdefault(path[level], {})[path] = changes_for_leaf

            untouched_slots = set(children) - {str(slot) for slot in grouped}
            reused_nodes += len(untouched_slots)
            for slot, slot_changes in grouped.items():
                slot_name = str(slot)
                child_hash = rewrite(children.get(slot_name), level + 1, slot_changes)
                if child_hash is None:
                    children.pop(slot_name, None)
                else:
                    children[slot_name] = child_hash

            if not children and level > 0:
                return None
            return intern({"type": "internal", "children": children})

        if mutations:
            rewritten = rewrite(root_hash, 0, mutations)
            assert rewritten is not None
            new_root = rewritten
        else:
            new_root = root_hash
            reused_nodes = 1

        self.last_new_node_hashes = tuple(sorted(created_this_commit))
        self._record_version(
            new_root,
            message,
            operations,
            new_nodes,
            reused_nodes,
            bytes_written,
        )
        return new_root

    def put(
        self,
        root_hash: str,
        key: str,
        value: Any,
        message: Optional[str] = None,
    ) -> str:
        return self.apply_changes(root_hash, puts={key: value}, message=message)

    def delete(self, root_hash: str, key: str, message: Optional[str] = None) -> str:
        return self.apply_changes(root_hash, deletes={key}, message=message)

    def materialize(self, root_hash: str) -> dict[str, Any]:
        self._require_root(root_hash)
        state: dict[str, Any] = {}

        def walk(node_hash: str) -> None:
            node = self.node_store[node_hash]
            if node["type"] == "leaf":
                state.update(node["entries"])
                return
            for child_hash in node["children"].values():
                walk(child_hash)

        walk(root_hash)
        return state

    def log(self) -> list[Commit]:
        history: list[Commit] = []
        version = self.head
        while version is not None:
            record = self.commits[version]
            history.append(record)
            version = record.parent
        return history

    def checkout(self, version: int) -> dict[str, Any]:
        if version not in self.commits:
            raise KeyError(f"unknown version: {version}")
        return self.materialize(self.commits[version].root_hash)

    def reachable_nodes(self, root_hash: str) -> set[str]:
        """Return exact reachable hashes for diagnostics, not the write path."""
        self._require_root(root_hash)
        reachable: set[str] = set()
        pending = [root_hash]
        while pending:
            node_hash = pending.pop()
            if node_hash in reachable:
                continue
            reachable.add(node_hash)
            node = self.node_store[node_hash]
            if node["type"] == "internal":
                pending.extend(node["children"].values())
        return reachable

    def structural_sharing(
        self, left_root: str, right_root: str
    ) -> StructuralSharingStats:
        """Measure exact node sharing separately from incremental write timing."""
        left = self.reachable_nodes(left_root)
        right = self.reachable_nodes(right_root)
        return StructuralSharingStats(len(left), len(right), len(left & right))

    @staticmethod
    def _entry(
        key: str,
        old_exists: bool,
        old_value: Any,
        new_exists: bool,
        new_value: Any,
    ) -> DiffEntry:
        if not old_exists:
            change_type = "added"
        elif not new_exists:
            change_type = "deleted"
        else:
            change_type = "modified"
        return DiffEntry(key, change_type, old_value, new_value)

    def diff_structured(self, left_root: str, right_root: str) -> list[DiffEntry]:
        """Merkle diff with hash pruning and structured old/new values."""
        self._require_root(left_root)
        self._require_root(right_root)
        nodes_compared = 0
        skipped = 0
        leaf_entries_examined = 0
        changes: dict[str, DiffEntry] = {}

        def all_entries(node_hash: Optional[str]) -> dict[str, Any]:
            nonlocal leaf_entries_examined
            if node_hash is None:
                return {}
            node = self.node_store[node_hash]
            if node["type"] == "leaf":
                leaf_entries_examined += len(node["entries"])
                return dict(node["entries"])
            result: dict[str, Any] = {}
            for child_hash in node["children"].values():
                result.update(all_entries(child_hash))
            return result

        def compare_maps(left: Mapping[str, Any], right: Mapping[str, Any]) -> None:
            for key in set(left) | set(right):
                left_exists = key in left
                right_exists = key in right
                if left_exists and right_exists and left[key] == right[key]:
                    continue
                changes[key] = self._entry(
                    key,
                    left_exists,
                    left.get(key),
                    right_exists,
                    right.get(key),
                )

        def walk(left_hash: Optional[str], right_hash: Optional[str]) -> None:
            nonlocal nodes_compared, skipped, leaf_entries_examined
            nodes_compared += 1
            if left_hash == right_hash:
                if left_hash is not None:
                    skipped += 1
                return
            if left_hash is None or right_hash is None:
                compare_maps(all_entries(left_hash), all_entries(right_hash))
                return

            left = self.node_store[left_hash]
            right = self.node_store[right_hash]
            if left["type"] == "internal" and right["type"] == "internal":
                slots = set(left["children"]) | set(right["children"])
                for slot in sorted(slots, key=int):
                    walk(left["children"].get(slot), right["children"].get(slot))
                return
            if left["type"] == "leaf" and right["type"] == "leaf":
                leaf_entries_examined += len(left["entries"]) + len(right["entries"])
                compare_maps(dict(left["entries"]), dict(right["entries"]))
                return
            compare_maps(all_entries(left_hash), all_entries(right_hash))

        walk(left_root, right_root)
        self.last_diff_stats = DiffStats(
            nodes_compared,
            skipped,
            leaf_entries_examined,
            0,
            "merkle",
        )
        return [changes[key] for key in sorted(changes)]

    def diff(self, left_root: str, right_root: str) -> list[str]:
        """Backward-compatible key-only Merkle diff."""
        return [entry.key for entry in self.diff_structured(left_root, right_root)]

    def _ancestor_path(
        self, ancestor: int, descendant: int
    ) -> Optional[list[int]]:
        path: list[int] = []
        current: Optional[int] = descendant
        while current is not None and current != ancestor:
            path.append(current)
            current = self.commits[current].parent
        if current != ancestor:
            return None
        return list(reversed(path))

    def _log_diff(self, left_version: int, right_version: int) -> list[DiffEntry]:
        path = self._ancestor_path(left_version, right_version)
        if path is None:
            raise ValueError("log diff requires left_version to be an ancestor")
        first: dict[str, ChangeOperation] = {}
        final: dict[str, ChangeOperation] = {}
        examined = 0
        for version in path:
            changes = self.changeset_store[self.commits[version].changeset_hash]
            for change in changes:
                examined += 1
                first.setdefault(change.key, change)
                final[change.key] = change

        entries: list[DiffEntry] = []
        for key in sorted(final):
            initial = first[key]
            latest = final[key]
            if (
                initial.old_exists == latest.new_exists
                and initial.old_value == latest.new_value
            ):
                continue
            entries.append(
                self._entry(
                    key,
                    initial.old_exists,
                    initial.old_value,
                    latest.new_exists,
                    latest.new_value,
                )
            )
        self.last_diff_stats = DiffStats(
            log_operations_examined=examined,
            strategy="log",
        )
        return entries

    @staticmethod
    def _reverse_entries(entries: list[DiffEntry]) -> list[DiffEntry]:
        reversed_entries: list[DiffEntry] = []
        for entry in entries:
            if entry.change_type == "added":
                change_type = "deleted"
            elif entry.change_type == "deleted":
                change_type = "added"
            else:
                change_type = "modified"
            reversed_entries.append(
                DiffEntry(entry.key, change_type, entry.new_value, entry.old_value)
            )
        return reversed_entries

    def diff_versions(
        self,
        left_version: int,
        right_version: int,
        strategy: str = "hybrid",
    ) -> list[DiffEntry]:
        """Compare commits using forced Merkle, forced log, or Revon-H mode."""
        if left_version not in self.commits or right_version not in self.commits:
            raise KeyError("unknown commit version")
        if strategy not in {"hybrid", "log", "merkle"}:
            raise ValueError("strategy must be 'hybrid', 'log', or 'merkle'")

        forward_path = self._ancestor_path(left_version, right_version)
        reverse = False
        if forward_path is None:
            path = self._ancestor_path(right_version, left_version)
            reverse = path is not None
        else:
            path = forward_path

        selected = strategy
        if strategy == "hybrid":
            operation_count = (
                sum(
                    len(self.changeset_store[self.commits[v].changeset_hash])
                    for v in path
                )
                if path is not None
                else self.hybrid_log_threshold + 1
            )
            selected = "log" if operation_count <= self.hybrid_log_threshold else "merkle"

        if selected == "log":
            if path is None:
                if strategy == "log":
                    raise ValueError("log diff requires an ancestor relationship")
                selected = "merkle"
            elif reverse:
                return self._reverse_entries(self._log_diff(right_version, left_version))
            else:
                return self._log_diff(left_version, right_version)

        return self.diff_structured(
            self.commits[left_version].root_hash,
            self.commits[right_version].root_hash,
        )

    def _require_root(self, root_hash: str) -> None:
        if root_hash not in self.node_store:
            raise KeyError(f"unknown root hash: {root_hash}")
