"""Measure the incremental put() path against the old full-rebuild commit().

Three experiments, all reported as raw numbers:
  1. Node counts and commit time for a 3-key change at 100,000 rows.
  2. Commit time at 1,000 / 10,000 / 100,000 rows, before vs after.
  3. Hot-key and spread-key diff cost, as a sanity check that diff is unchanged.
"""

from __future__ import annotations

import statistics
import time

from experiments.benchmarks import build_workload, benchmark_revon
from versioned_db import VersionedDatabase

CHANGED_KEYS = ("key-00000001", "key-00050000", "key-00099999")


def _median_ms(samples: list[float]) -> float:
    return statistics.median(samples)


def three_key_change(rows: int = 100_000, repeats: int = 5) -> dict[str, float]:
    """Old full rebuild vs new put() path for a 3-key change."""
    state = {f"key-{index:08d}": index for index in range(rows)}

    rebuild_times: list[float] = []
    rebuild_new_nodes = 0
    for attempt in range(repeats):
        db = VersionedDatabase()
        db.commit(state)
        baseline_nodes = len(db.node_store)
        mutated = dict(state)
        for index, key in enumerate(CHANGED_KEYS):
            mutated[key] = f"changed-{attempt}-{index}"
        started = time.perf_counter_ns()
        db.commit(mutated)
        rebuild_times.append((time.perf_counter_ns() - started) / 1_000_000)
        rebuild_new_nodes = len(db.node_store) - baseline_nodes

    put_times: list[float] = []
    put_new_nodes = 0
    tree_nodes = 0
    for attempt in range(repeats):
        db = VersionedDatabase()
        root = db.commit(state)
        baseline_nodes = len(db.node_store)
        tree_nodes = baseline_nodes
        started = time.perf_counter_ns()
        for index, key in enumerate(CHANGED_KEYS):
            root = db.put(root, key, f"changed-{attempt}-{index}")
        put_times.append((time.perf_counter_ns() - started) / 1_000_000)
        put_new_nodes = len(db.node_store) - baseline_nodes

    return {
        "rows": rows,
        "tree_nodes": tree_nodes,
        "rebuild_ms": _median_ms(rebuild_times),
        "rebuild_new_nodes": rebuild_new_nodes,
        "put_ms": _median_ms(put_times),
        "put_new_nodes": put_new_nodes,
        "budget": len(CHANGED_KEYS) * (VersionedDatabase().tree_depth + 1),
    }


def commit_time_by_scale(
    sizes: tuple[int, ...] = (1_000, 10_000, 100_000),
    versions: int = 5,
    changes: int = 10,
) -> list[dict[str, float]]:
    """Commit ms at each scale, full-rebuild path vs incremental path."""
    rows_out: list[dict[str, float]] = []
    for rows in sizes:
        initial, batches = build_workload(rows, versions, changes)
        before, _ = benchmark_revon(initial, batches, 3, incremental=False)
        after, _ = benchmark_revon(initial, batches, 3, incremental=True)
        rows_out.append(
            {
                "rows": rows,
                "before_ms": before.commit_ms,
                "after_ms": after.commit_ms,
                "diff_ms": after.diff_ms,
                "diff_nodes": after.diff_work,
            }
        )
    return rows_out


def key_spread_experiment(
    hot: bool, rows: int = 10_000, commits: int = 100, changes: int = 5
) -> list[dict[str, float]]:
    """Diff cost at increasing commit distance, hot keys vs fresh keys."""
    db = VersionedDatabase()
    state = {f"key-{index:08d}": index for index in range(rows)}
    first = db.commit(state)
    root = first

    for step in range(1, commits + 1):
        for offset in range(changes):
            if hot:
                key = f"key-{offset:08d}"          # same 5 keys, every commit
            else:
                key = f"fresh-{step:04d}-{offset}"  # 5 brand-new keys each time
            root = db.put(root, key, f"v{step}")

    samples: list[dict[str, float]] = []
    for distance in (1, 10, 50, 100):
        if distance > commits:
            continue
        target = db.commits[1 + distance * changes].root_hash
        changed = db.diff(first, target)
        samples.append(
            {
                "distance": distance,
                "changed_keys": len(changed),
                "nodes_compared": db.last_diff_stats.nodes_compared,
                "skipped": db.last_diff_stats.matching_subtrees_skipped,
            }
        )
    return samples


def main() -> None:
    headline = three_key_change()
    print("=== 3-key change at 100,000 rows ===")
    print(f"  full tree nodes:            {headline['tree_nodes']:,}")
    print(f"  full rebuild new nodes:     {headline['rebuild_new_nodes']:,}")
    print(f"  incremental new nodes:      {headline['put_new_nodes']:,} "
          f"(budget {headline['budget']})")
    print(f"  full rebuild commit ms:     {headline['rebuild_ms']:.3f}")
    print(f"  incremental commit ms:      {headline['put_ms']:.3f}")
    print(f"  speedup:                    "
          f"{headline['rebuild_ms'] / headline['put_ms']:.1f}x")

    print()
    print("=== Commit time by scale (5 versions, 10 changes each) ===")
    print(f"{'rows':>8} {'before ms':>11} {'after ms':>11} {'speedup':>9}")
    for row in commit_time_by_scale():
        print(f"{row['rows']:>8,} {row['before_ms']:>11.3f} "
              f"{row['after_ms']:>11.3f} "
              f"{row['before_ms'] / row['after_ms']:>8.1f}x")

    for label, hot in (("hot-key", True), ("spread-key", False)):
        print()
        print(f"=== {label} diff cost ===")
        print(f"{'distance':>9} {'changed':>9} {'nodes cmp':>11} {'skipped':>9}")
        for sample in key_spread_experiment(hot=hot):
            print(f"{sample['distance']:>9} {sample['changed_keys']:>9,} "
                  f"{sample['nodes_compared']:>11,} {sample['skipped']:>9,}")


if __name__ == "__main__":
    main()
