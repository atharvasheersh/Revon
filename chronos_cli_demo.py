"""Run a deterministic, self-checking Chronos-H CLI demonstration.

Examples:
    python chronos_cli_demo.py
    python chronos_cli_demo.py --rows 10000 --updates 10 --show-changes
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass

from versioned_db import DiffEntry, VersionedDatabase


@dataclass(frozen=True)
class DemoResult:
    rows: int
    changed_keys: int
    initial_ms: float
    incremental_ms: float
    initial_root: str
    incremental_root: str
    commit_hash: str
    new_nodes: int
    maximum_path_nodes: int
    shared_nodes: int
    version_two_nodes: int
    shared_percent: float
    hybrid_strategy: str
    hybrid_work: int
    changes: tuple[DiffEntry, ...]


def run_demo(
    rows: int = 1_000,
    updates: int = 3,
    hybrid_threshold: int = 128,
) -> DemoResult:
    """Execute the demonstration and raise if any correctness check fails."""
    if rows < 10:
        raise ValueError("rows must be at least 10")
    if not 1 <= updates <= rows - 2:
        raise ValueError("updates must be between 1 and rows - 2")

    state = {
        f"row-{index:08d}": {
            "id": index,
            "status": "active",
            "score": index % 100,
        }
        for index in range(rows)
    }
    db = VersionedDatabase(hybrid_log_threshold=hybrid_threshold)

    started = time.perf_counter_ns()
    root_v1 = db.commit(state, message="initial import")
    initial_ms = (time.perf_counter_ns() - started) / 1_000_000

    # Spread changed keys across the hash-routed trie, then add and delete one.
    update_indices = [
        max(0, min(rows - 2, ((offset + 1) * rows) // (updates + 1)))
        for offset in range(updates)
    ]
    update_indices = list(dict.fromkeys(update_indices))
    if len(update_indices) != updates:
        raise RuntimeError("unable to select unique deterministic update keys")

    puts = {
        f"row-{index:08d}": {
            "id": index,
            "status": "reviewed",
            "score": (index % 100) + 1,
        }
        for index in update_indices
    }
    added_key = f"row-{rows:08d}"
    deleted_key = f"row-{rows - 1:08d}"
    puts[added_key] = {"id": rows, "status": "new", "score": 0}

    started = time.perf_counter_ns()
    root_v2 = db.apply_changes(
        root_v1,
        puts=puts,
        deletes={deleted_key},
        message="mixed incremental batch",
    )
    incremental_ms = (time.perf_counter_ns() - started) / 1_000_000

    expected = dict(state)
    expected.update(puts)
    del expected[deleted_key]

    # A canonical rebuild must produce exactly the same root as path copying.
    rebuilt = VersionedDatabase(
        branching_factor=db.branching_factor,
        tree_depth=db.tree_depth,
    )
    rebuilt_root = rebuilt.commit(expected)
    if root_v2 != rebuilt_root:
        raise RuntimeError("incremental root differs from canonical full rebuild")
    if db.checkout(1) != state or db.checkout(2) != expected:
        raise RuntimeError("historical checkout did not reproduce an exact state")

    log_changes = db.diff_versions(1, 2, strategy="log")
    merkle_changes = db.diff_versions(1, 2, strategy="merkle")
    hybrid_changes = db.diff_versions(1, 2, strategy="hybrid")
    if log_changes != merkle_changes or log_changes != hybrid_changes:
        raise RuntimeError("Log, Merkle, and Hybrid diffs disagree")

    expected_keys = set(puts) | {deleted_key}
    if {entry.key for entry in hybrid_changes} != expected_keys:
        raise RuntimeError("diff did not return exactly the submitted changes")

    sharing = db.structural_sharing(root_v1, root_v2)
    stats = db.commit_stats[2]
    maximum_path_nodes = len(expected_keys) * (db.tree_depth + 1)
    hybrid_work = (
        db.last_diff_stats.log_operations_examined
        if db.last_diff_stats.strategy == "log"
        else db.last_diff_stats.nodes_compared
    )
    return DemoResult(
        rows=rows,
        changed_keys=len(expected_keys),
        initial_ms=initial_ms,
        incremental_ms=incremental_ms,
        initial_root=root_v1,
        incremental_root=root_v2,
        commit_hash=db.commits[2].commit_hash,
        new_nodes=stats.new_nodes,
        maximum_path_nodes=maximum_path_nodes,
        shared_nodes=sharing.shared_nodes,
        version_two_nodes=sharing.right_nodes,
        shared_percent=sharing.right_shared_percent,
        hybrid_strategy=db.last_diff_stats.strategy,
        hybrid_work=hybrid_work,
        changes=tuple(hybrid_changes),
    )


def print_report(result: DemoResult, show_changes: bool = False) -> None:
    work_unit = "operations" if result.hybrid_strategy == "log" else "node pairs"
    print("Chronos-H incremental Merkle trie verification")
    print("=" * 54)
    print(f"Dataset                  {result.rows:,} rows")
    print(f"Mixed batch              {result.changed_keys} changed keys")
    print(f"Initial build            {result.initial_ms:.3f} ms")
    print(f"Incremental commit       {result.incremental_ms:.3f} ms")
    print(f"New trie nodes           {result.new_nodes}")
    print(f"Path-copy upper bound    {result.maximum_path_nodes}")
    print(
        f"Exact structural sharing {result.shared_nodes}/{result.version_two_nodes} "
        f"nodes ({result.shared_percent:.2f}%)"
    )
    print(f"Hybrid selected          {result.hybrid_strategy}")
    print(f"Hybrid diff work         {result.hybrid_work} {work_unit}")
    print(f"Root v1                  {result.initial_root[:20]}...")
    print(f"Root v2                  {result.incremental_root[:20]}...")
    print(f"Commit v2                {result.commit_hash[:20]}...")
    print()
    print("PASS  incremental root equals canonical full rebuild")
    print("PASS  Log, Merkle, and Hybrid diffs agree")
    print("PASS  v1 and v2 checkout reproduce exact states")
    if show_changes:
        print()
        print("Structured changes")
        for entry in result.changes:
            print(f"  {entry.change_type.upper():8} {entry.key}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=1_000)
    parser.add_argument("--updates", type=int, default=3)
    parser.add_argument("--hybrid-threshold", type=int, default=128)
    parser.add_argument("--show-changes", action="store_true")
    args = parser.parse_args()

    result = run_demo(args.rows, args.updates, args.hybrid_threshold)
    print_report(result, args.show_changes)


if __name__ == "__main__":
    main()
