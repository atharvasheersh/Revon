"""Fixed-fanout hash trie versus content-defined chunking, head to head.

Both engines are content-addressed and share unchanged subtrees.  They differ
only in where node boundaries fall, so this isolates that one decision.
"""

from __future__ import annotations

import statistics
import time

from benchmarks import canonical_size
from prolly_db import ProllyStore
from versioned_db import VersionedDatabase

TARGET = 32


def ms(function):
    started = time.perf_counter_ns()
    result = function()
    return (time.perf_counter_ns() - started) / 1_000_000, result


def bytes_written(store, root, keys, put):
    """Bytes of new node content created by single-key writes."""
    written = 0
    for key in keys:
        before = set(store.node_store)
        root = put(root, key)
        written += sum(
            canonical_size(store.node_store[h])
            for h in set(store.node_store) - before
        )
    return written / len(keys), root


def scaling() -> None:
    print("=== Cost of changing ONE key, as the table grows ===")
    print(f"{'rows':>9} | {'trie: keys/leaf':>16} {'bytes/put':>10} {'depth':>6}"
          f" | {'prolly: keys/leaf':>18} {'bytes/put':>10} {'depth':>6}")
    for rows in (1_000, 10_000, 100_000, 400_000):
        state = {f"key-{i:08d}": i for i in range(rows)}
        probes = [f"key-{i:08d}" for i in (1, rows // 2, rows - 1)]

        trie = VersionedDatabase()
        trie_root = trie.commit(state)
        trie_leaves = [
            len(n["entries"]) for n in trie.node_store.values() if n["type"] == "leaf"
        ]
        trie_bytes, _ = bytes_written(
            trie, trie_root, probes, lambda r, k: trie.put(r, k, "changed")
        )

        prolly = ProllyStore(target_chunk_size=TARGET)
        prolly_root = prolly.commit(state)
        prolly_leaves = prolly.chunk_sizes(prolly_root)
        prolly_bytes, _ = bytes_written(
            prolly, prolly_root, probes, lambda r, k: prolly.put(r, k, "changed")
        )

        print(f"{rows:>9,} | {statistics.mean(trie_leaves):>16.1f} "
              f"{trie_bytes:>10,.0f} {trie.tree_depth + 1:>6}"
              f" | {statistics.mean(prolly_leaves):>18.1f} "
              f"{prolly_bytes:>10,.0f} {prolly.depth(prolly_root):>6}")


def sequential_insert() -> None:
    print()
    print("=== Bulk append: 200 consecutive new keys onto a 100,000-row table ===")
    state = {f"key-{i:08d}": i for i in range(100_000)}
    new_keys = [f"key-{i:08d}" for i in range(100_000, 100_200)]

    trie = VersionedDatabase()
    root = trie.commit(state)
    before = len(trie.node_store)
    elapsed, _ = ms(lambda: [trie.put(root, k, 1) for k in new_keys])
    print(f"  trie   : {len(trie.node_store) - before:>7,} new nodes  "
          f"{elapsed:>8.1f} ms")

    prolly = ProllyStore(target_chunk_size=TARGET)
    root = prolly.commit(state)
    before = len(prolly.node_store)
    elapsed, _ = ms(lambda: [prolly.put(root, k, 1) for k in new_keys])
    print(f"  prolly : {len(prolly.node_store) - before:>7,} new nodes  "
          f"{elapsed:>8.1f} ms")


def range_scans() -> None:
    print()
    print("=== Ordered range scan of 1,000 keys from a 100,000-row table ===")
    state = {f"key-{i:08d}": i for i in range(100_000)}

    trie = VersionedDatabase()
    trie_root = trie.commit(state)
    lo, hi = "key-00050000", "key-00051000"

    def trie_scan():
        # The trie destroys key order, so the only option is a full scan.
        return sorted(
            (k, v) for k, v in trie.materialize(trie_root).items() if lo <= k < hi
        )

    prolly = ProllyStore(target_chunk_size=TARGET)
    prolly_root = prolly.commit(state)

    trie_ms, trie_rows = ms(trie_scan)
    prolly_ms, prolly_rows = ms(lambda: prolly.range_scan(prolly_root, lo, hi))
    assert trie_rows == prolly_rows, "engines disagree on the scan result"
    print(f"  trie   : {trie_ms:>8.2f} ms  (full materialize + sort)")
    print(f"  prolly : {prolly_ms:>8.2f} ms  (ordered, pruned)")
    print(f"  speedup: {trie_ms / prolly_ms:>8.1f}x")


def diff_cost() -> None:
    print()
    print("=== Diff after 5 scattered edits on a 100,000-row table ===")
    state = {f"key-{i:08d}": i for i in range(100_000)}
    edits = [f"key-{i:08d}" for i in (10, 25_000, 50_000, 75_000, 99_000)]

    for name, store in (
        ("trie  ", VersionedDatabase()),
        ("prolly", ProllyStore(target_chunk_size=TARGET)),
    ):
        first = store.commit(state)
        root = first
        for key in edits:
            root = store.put(root, key, "changed")
        elapsed, changed = ms(lambda: store.diff(first, root))
        print(f"  {name} : {elapsed:>7.2f} ms  {len(changed)} keys  "
              f"{store.last_diff_stats}")


def main() -> None:
    scaling()
    sequential_insert()
    range_scans()
    diff_cost()


if __name__ == "__main__":
    main()
