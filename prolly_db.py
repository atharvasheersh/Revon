"""A Prolly-tree store: content-defined chunk boundaries over sorted keys.

This is the Dolt/Noms-style alternative to the fixed-fanout hash trie in
`versioned_db.py`.  Both are content-addressed and share unchanged subtrees;
they differ only in how they decide where one node ends and the next begins.

    versioned_db.VersionedDatabase  hash the key, route it to a fixed slot.
                                    Fixed depth, 8^4 = 4096 leaves, maximum.
                                    Key order is destroyed.

    prolly_db.ProllyStore           keep keys sorted, cut a chunk wherever a
                                    hash of the item's own content hits a
                                    target pattern.  Chunk size stays near the
                                    target at any scale, and the tree grows
                                    deeper instead of fatter.

Because a boundary depends only on the item it follows, the tree is
history-independent: the same set of keys always produces the same tree, and
the same root hash, no matter what order the keys arrived in.  Sorted order
also makes ordered range scans possible, which the trie cannot do at all.

`versioned_db.py` is deliberately untouched: `_route`, `_node_hash`, and
`_canonical_bytes` there keep their exact behaviour so existing benchmark
numbers stay comparable.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import time
from typing import Any, Mapping, Optional

from versioned_db import Commit, CommitStats, DiffStats

# Node shapes, both stored under the SHA-256 of their canonical JSON form:
#   leaf      {"type": "leaf",     "entries":  [[key, value], ...]}
#   internal  {"type": "internal", "children": [[first_key, hash], ...]}
# Internal children are an ordered list, not a slot map, because this tree is
# ordered by key rather than by routed hash bits.


class ProllyStore:
    """A content-addressed Prolly tree with content-defined chunk boundaries."""

    def __init__(self, target_chunk_size: int = 32) -> None:
        if target_chunk_size < 2 or target_chunk_size & (target_chunk_size - 1):
            raise ValueError("target_chunk_size must be a power of two")

        self.target_chunk_size = target_chunk_size
        self.node_store: dict[str, dict[str, Any]] = {}
        self.versions: dict[int, str] = {}
        self.commits: dict[int, Commit] = {}
        self.head: Optional[int] = None
        self.commit_stats: dict[int, CommitStats] = {}
        self.last_diff_stats = DiffStats(0, 0)

        self._new_nodes = 0
        self._reused_nodes = 0

    # ---------------------------------------------------------------- hashing

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

    def _node_hash(self, node: dict[str, Any]) -> str:
        return hashlib.sha256(self._canonical_bytes(node)).hexdigest()

    def _intern(self, node: dict[str, Any]) -> str:
        node_hash = self._node_hash(node)
        if node_hash in self.node_store:
            self._reused_nodes += 1
        else:
            self.node_store[node_hash] = node
            self._new_nodes += 1
        return node_hash

    def _is_boundary(self, seed: bytes) -> bool:
        """True when this item should end its chunk.

        The decision depends only on the item's own content, never on its
        position or on its neighbours.  That is what makes the chunking
        history-independent and keeps an edit's effect local.
        """
        digest = hashlib.sha256(seed).digest()
        mask = self.target_chunk_size - 1
        return (int.from_bytes(digest[-4:], "big") & mask) == 0

    # ---------------------------------------------------------------- building

    def _build_leaves(self, items: list[tuple[str, Any]]) -> list[list[Any]]:
        """Chunk sorted (key, value) pairs into leaves."""
        entries: list[list[Any]] = []
        current: list[list[Any]] = []
        for key, value in items:
            current.append([key, value])
            if self._is_boundary(self._canonical_bytes([key, value])):
                entries.append(self._make_leaf(current))
                current = []
        if current or not entries:
            entries.append(self._make_leaf(current))
        return entries

    def _make_leaf(self, rows: list[list[Any]]) -> list[Any]:
        first_key = rows[0][0] if rows else ""
        return [first_key, self._intern({"type": "leaf", "entries": rows})]

    def _build_internal(self, entries: list[list[Any]]) -> list[list[Any]]:
        """Chunk one level of (first_key, hash) entries into parent nodes."""
        parents: list[list[Any]] = []
        current: list[list[Any]] = []
        for entry in entries:
            current.append(entry)
            if self._is_boundary(entry[1].encode("utf-8")):
                parents.append(self._make_internal(current))
                current = []
        if current:
            parents.append(self._make_internal(current))
        return parents

    def _make_internal(self, children: list[list[Any]]) -> list[Any]:
        return [
            children[0][0],
            self._intern({"type": "internal", "children": [list(c) for c in children]}),
        ]

    def _root_from_leaves(self, entries: list[list[Any]]) -> str:
        while len(entries) > 1:
            parents = self._build_internal(entries)
            if len(parents) >= len(entries):
                # Degenerate case: every entry was a boundary, so the level did
                # not shrink.  Collapse the whole level into a single node.
                parents = [self._make_internal(entries)]
            entries = parents
        return entries[0][1]

    # ----------------------------------------------------------------- commits

    def _record(
        self, root_hash: str, message: Optional[str], new: int, reused: int
    ) -> Commit:
        version = len(self.versions) + 1
        record = Commit(
            version=version,
            root_hash=root_hash,
            parent=self.head,
            message=message,
            timestamp=time.time(),
        )
        self.versions[version] = root_hash
        self.commits[version] = record
        self.commit_stats[version] = CommitStats(version, new, reused)
        self.head = version
        return record

    def commit(self, state: Mapping[str, Any], message: Optional[str] = None) -> str:
        """Build a whole tree from a complete state and return its root hash."""
        if any(not isinstance(key, str) for key in state):
            raise TypeError("all keys must be strings")
        self._canonical_bytes(dict(state))

        self._new_nodes = self._reused_nodes = 0
        items = sorted(state.items())
        root_hash = self._root_from_leaves(self._build_leaves(items))
        self._record(root_hash, message, self._new_nodes, self._reused_nodes)
        return root_hash

    # ------------------------------------------------------------- incremental

    def _leaf_entries(self, root_hash: str) -> list[list[Any]]:
        """Ordered (first_key, leaf_hash) entries for every leaf in the tree."""
        entries: list[list[Any]] = []

        def walk(node_hash: str) -> None:
            node = self.node_store[node_hash]
            if node["type"] == "leaf":
                entries.append([node["entries"][0][0] if node["entries"] else "",
                                node_hash])
                return
            for _, child_hash in node["children"]:
                walk(child_hash)

        walk(root_hash)
        return entries

    def _apply_one(
        self,
        root_hash: str,
        key: str,
        value: Any,
        remove: bool,
        message: Optional[str],
    ) -> str:
        if not isinstance(key, str):
            raise TypeError("all keys must be strings")
        if not remove:
            self._canonical_bytes({key: value})
        self._require_root(root_hash)

        self._new_nodes = self._reused_nodes = 0
        leaves = self._leaf_entries(root_hash)

        # Locate the leaf whose key range covers this key.
        first_keys = [entry[0] for entry in leaves]
        index = bisect.bisect_right(first_keys, key) - 1
        if index < 0:
            index = 0

        rows = [list(row) for row in self.node_store[leaves[index][1]]["entries"]]
        position = bisect.bisect_left([row[0] for row in rows], key)
        if position < len(rows) and rows[position][0] == key:
            if remove:
                rows.pop(position)
            else:
                rows[position][1] = value
        elif remove:
            raise KeyError(f"key not present in this version: {key}")
        else:
            rows.insert(position, [key, value])

        consumed = 1
        if not rows:
            # The leaf emptied out.  Drop it, unless it is the only one left,
            # in which case the tree collapses to a single empty leaf.
            rebuilt = self._build_leaves([]) if len(leaves) == 1 else []
        else:
            # A chunk ends at a boundary item.  If this leaf's last item is no
            # longer a boundary, its tail must merge into the following leaf.
            if not self._is_boundary(self._canonical_bytes(rows[-1])) and (
                index + 1 < len(leaves)
            ):
                rows.extend(
                    list(row)
                    for row in self.node_store[leaves[index + 1][1]]["entries"]
                )
                consumed = 2
            rebuilt = self._build_leaves([(row[0], row[1]) for row in rows])

        leaves[index:index + consumed] = rebuilt
        if not leaves:
            leaves = self._build_leaves([])

        root = self._root_from_leaves(leaves)
        self._record(root, message, self._new_nodes, self._reused_nodes)
        return root

    def put(
        self, root_hash: str, key: str, value: Any, message: Optional[str] = None
    ) -> str:
        """Set one key, re-chunking only the affected leaf neighbourhood.

        KNOWN LIMITATION: the leaf-level work is local, but the internal levels
        are currently rebuilt from the full ordered leaf list, so a write costs
        O(leaves) rather than the O(depth) a real Prolly cursor achieves.  The
        resulting root hash is exactly correct either way -- this is a speed
        gap, not a correctness one, and it is why writes here are slower than
        the trie's.  Closing it needs a cursor that can splice a leaf and walk
        the ascent locally, including the case where a merge crosses a parent
        boundary.  See BENCHMARK_RESULTS_ENGINES.md.
        """
        return self._apply_one(root_hash, key, value, False, message)

    def delete(self, root_hash: str, key: str, message: Optional[str] = None) -> str:
        """Remove one key.  Same O(leaves) write-cost limitation as put()."""
        return self._apply_one(root_hash, key, None, True, message)

    # ------------------------------------------------------------------ reading

    def materialize(self, root_hash: str) -> dict[str, Any]:
        self._require_root(root_hash)
        state: dict[str, Any] = {}
        for _, leaf_hash in self._leaf_entries(root_hash):
            state.update(self.node_store[leaf_hash]["entries"])
        return state

    def get(self, root_hash: str, key: str) -> Any:
        self._require_root(root_hash)
        node_hash = root_hash
        while True:
            node = self.node_store[node_hash]
            if node["type"] == "leaf":
                for entry_key, entry_value in node["entries"]:
                    if entry_key == key:
                        return entry_value
                raise KeyError(key)
            children = node["children"]
            index = bisect.bisect_right([c[0] for c in children], key) - 1
            node_hash = children[max(index, 0)][1]

    def range_scan(
        self, root_hash: str, start: str, end: str
    ) -> list[tuple[str, Any]]:
        """Ordered scan of [start, end).  The hash trie cannot do this at all."""
        self._require_root(root_hash)
        found: list[tuple[str, Any]] = []

        def walk(node_hash: str) -> None:
            node = self.node_store[node_hash]
            if node["type"] == "leaf":
                for entry_key, entry_value in node["entries"]:
                    if start <= entry_key < end:
                        found.append((entry_key, entry_value))
                return
            children = node["children"]
            for position, (first_key, child_hash) in enumerate(children):
                # Prune whole subtrees that fall outside the requested range.
                next_first = (
                    children[position + 1][0]
                    if position + 1 < len(children)
                    else None
                )
                if next_first is not None and next_first <= start:
                    continue
                if first_key >= end:
                    break
                walk(child_hash)

        walk(root_hash)
        return found

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

    # --------------------------------------------------------------------- diff

    def diff(self, left_root: str, right_root: str) -> list[str]:
        """Changed keys, skipping every subtree whose hashes already match."""
        self._require_root(left_root)
        self._require_root(right_root)

        nodes_compared = 0
        skipped = 0
        # Subtrees that could not be paired up are gathered here and compared
        # by key at the end, so a shifted chunk boundary never reports an
        # unchanged key as changed.
        left_loose: dict[str, Any] = {}
        right_loose: dict[str, Any] = {}

        def gather(node_hash: str, into: dict[str, Any]) -> None:
            node = self.node_store[node_hash]
            if node["type"] == "leaf":
                into.update(node["entries"])
                return
            for _, child_hash in node["children"]:
                gather(child_hash, into)

        def walk(left_hash: str, right_hash: str) -> None:
            nonlocal nodes_compared, skipped
            nodes_compared += 1
            if left_hash == right_hash:
                skipped += 1
                return

            left = self.node_store[left_hash]
            right = self.node_store[right_hash]
            if left["type"] != right["type"]:
                gather(left_hash, left_loose)
                gather(right_hash, right_loose)
                return

            if left["type"] == "leaf":
                left_loose.update(left["entries"])
                right_loose.update(right["entries"])
                return

            left_children = {first: h for first, h in left["children"]}
            right_children = {first: h for first, h in right["children"]}
            for first_key in sorted(set(left_children) | set(right_children)):
                left_child = left_children.get(first_key)
                right_child = right_children.get(first_key)
                if left_child == right_child:
                    if left_child is not None:
                        skipped += 1
                    continue
                if left_child is None:
                    gather(right_child, right_loose)
                elif right_child is None:
                    gather(left_child, left_loose)
                else:
                    walk(left_child, right_child)

        walk(left_root, right_root)
        self.last_diff_stats = DiffStats(nodes_compared, skipped)

        changed = {
            key
            for key in set(left_loose) | set(right_loose)
            if key not in left_loose
            or key not in right_loose
            or left_loose[key] != right_loose[key]
        }
        return sorted(changed)

    # -------------------------------------------------------------- diagnostics

    def chunk_sizes(self, root_hash: str) -> list[int]:
        """Entry count of every leaf, for chunk-size distribution reporting."""
        return [
            len(self.node_store[leaf_hash]["entries"])
            for _, leaf_hash in self._leaf_entries(root_hash)
        ]

    def depth(self, root_hash: str) -> int:
        depth = 1
        node_hash = root_hash
        while self.node_store[node_hash]["type"] == "internal":
            node_hash = self.node_store[node_hash]["children"][0][1]
            depth += 1
        return depth

    def _require_root(self, root_hash: str) -> None:
        if root_hash not in self.node_store:
            raise KeyError(f"unknown root hash: {root_hash}")
