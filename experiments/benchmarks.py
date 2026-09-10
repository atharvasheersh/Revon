"""Compare state, operational, and Revon key-value versioning models.

Reported storage is compact serialized size rather than Python process memory,
so Python object-header overhead does not distort the comparison.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from versioned_db import VersionedDatabase


@dataclass(frozen=True)
class Operation:
    key: str
    old_value: Any
    new_value: Any

    def as_record(self) -> dict[str, Any]:
        return {"key": self.key, "old": self.old_value, "new": self.new_value}


@dataclass(frozen=True)
class BenchmarkResult:
    model: str
    commit_ms: float
    diff_ms: float
    storage_bytes: int
    diff_work: int
    work_unit: str
    changed_keys: int


def canonical_size(value: Any) -> int:
    """Return deterministic compact-JSON size in bytes."""
    return len(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    )


class FullSnapshotModel:
    """Naive state model: every commit copies the complete table."""

    def __init__(self) -> None:
        self.versions: list[dict[str, Any]] = []
        self.last_diff_work = 0

    def commit(self, state: dict[str, Any]) -> int:
        self.versions.append(dict(state))
        return len(self.versions) - 1

    def diff(self, left: int, right: int) -> list[str]:
        left_state = self.versions[left]
        right_state = self.versions[right]
        keys = set(left_state) | set(right_state)
        self.last_diff_work = len(keys)
        missing = object()
        return sorted(
            key
            for key in keys
            if left_state.get(key, missing) != right_state.get(key, missing)
        )

    def storage_bytes(self) -> int:
        return sum(canonical_size(version) for version in self.versions)


class OperationLogModel:
    """Operational model: one base state followed by mutation records."""

    def __init__(self, initial_state: dict[str, Any]) -> None:
        self.initial_state = dict(initial_state)
        self.commits: list[list[Operation]] = []
        self.last_diff_work = 0

    def commit(self, operations: Iterable[Operation]) -> int:
        self.commits.append(list(operations))
        return len(self.commits)

    def diff(self, left: int, right: int) -> list[str]:
        if not 0 <= left <= right <= len(self.commits):
            raise IndexError("versions must satisfy 0 <= left <= right")

        first_values: dict[str, Any] = {}
        final_values: dict[str, Any] = {}
        self.last_diff_work = 0
        for batch in self.commits[left:right]:
            for operation in batch:
                self.last_diff_work += 1
                first_values.setdefault(operation.key, operation.old_value)
                final_values[operation.key] = operation.new_value

        return sorted(
            key for key in final_values if first_values[key] != final_values[key]
        )

    def storage_bytes(self) -> int:
        log_records = [
            [operation.as_record() for operation in batch]
            for batch in self.commits
        ]
        return canonical_size(self.initial_state) + canonical_size(log_records)


def build_workload(
    rows: int, versions: int, changes_per_commit: int
) -> tuple[dict[str, int], list[list[Operation]]]:
    if rows < 1:
        raise ValueError("rows must be positive")
    if versions < 2:
        raise ValueError("versions must be at least 2")
    if not 1 <= changes_per_commit <= rows:
        raise ValueError("changes must be between 1 and the number of rows")

    initial = {f"key-{index:08d}": index for index in range(rows)}
    working = dict(initial)
    batches: list[list[Operation]] = []

    # Spread mutations across the table and hash tree.
    stride = max(1, rows // changes_per_commit)
    for version in range(1, versions):
        batch: list[Operation] = []
        for offset in range(changes_per_commit):
            index = (offset * stride + version - 1) % rows
            key = f"key-{index:08d}"
            old_value = working[key]
            new_value = -(version * rows + index + 1)
            batch.append(Operation(key, old_value, new_value))
            working[key] = new_value
        batches.append(batch)
    return initial, batches


def apply_batch(state: dict[str, Any], batch: Iterable[Operation]) -> None:
    for operation in batch:
        state[operation.key] = operation.new_value


def median_time_ms(
    function: Callable[[], list[str]], repeats: int
) -> tuple[float, list[str]]:
    durations: list[float] = []
    result: list[str] = []
    for _ in range(repeats):
        started = time.perf_counter_ns()
        result = function()
        durations.append((time.perf_counter_ns() - started) / 1_000_000)
    return statistics.median(durations), result


def benchmark_state(
    initial: dict[str, int], batches: list[list[Operation]], diff_repeats: int
) -> tuple[BenchmarkResult, list[str]]:
    model = FullSnapshotModel()
    first = model.commit(initial)
    state: dict[str, Any] = dict(initial)
    commit_times: list[float] = []
    final = first
    for batch in batches:
        apply_batch(state, batch)
        started = time.perf_counter_ns()
        final = model.commit(state)
        commit_times.append((time.perf_counter_ns() - started) / 1_000_000)

    diff_ms, changed = median_time_ms(
        lambda: model.diff(first, final), diff_repeats
    )
    return (
        BenchmarkResult(
            model="State (full copies)",
            commit_ms=statistics.median(commit_times),
            diff_ms=diff_ms,
            storage_bytes=model.storage_bytes(),
            diff_work=model.last_diff_work,
            work_unit="keys",
            changed_keys=len(changed),
        ),
        changed,
    )


def benchmark_operations(
    initial: dict[str, int], batches: list[list[Operation]], diff_repeats: int
) -> tuple[BenchmarkResult, list[str]]:
    model = OperationLogModel(initial)
    commit_times: list[float] = []
    final = 0
    for batch in batches:
        started = time.perf_counter_ns()
        final = model.commit(batch)
        commit_times.append((time.perf_counter_ns() - started) / 1_000_000)

    diff_ms, changed = median_time_ms(lambda: model.diff(0, final), diff_repeats)
    return (
        BenchmarkResult(
            model="Operational (log)",
            commit_ms=statistics.median(commit_times),
            diff_ms=diff_ms,
            storage_bytes=model.storage_bytes(),
            diff_work=model.last_diff_work,
            work_unit="operations",
            changed_keys=len(changed),
        ),
        changed,
    )


def benchmark_revon(
    initial: dict[str, int], batches: list[list[Operation]], diff_repeats: int
) -> tuple[BenchmarkResult, list[str]]:
    model = VersionedDatabase(branching_factor=8, tree_depth=4)
    first = model.commit(initial)
    commit_times: list[float] = []
    final = first
    for batch in batches:
        started = time.perf_counter_ns()
        final = model.apply_changes(
            final,
            puts={operation.key: operation.new_value for operation in batch},
        )
        commit_times.append((time.perf_counter_ns() - started) / 1_000_000)

    def hybrid_diff() -> list[str]:
        return [
            entry.key
            for entry in model.diff_versions(1, len(model.versions), strategy="hybrid")
        ]

    diff_ms, changed = median_time_ms(hybrid_diff, diff_repeats)

    # Count unique serialized nodes, content-addressed changesets and commits.
    storage = sum(
        64 + canonical_size(node) for node in model.node_store.values()
    )
    storage += sum(
        64 + canonical_size([change.as_record() for change in changes])
        for changes in model.changeset_store.values()
    )
    storage += sum(
        64 + canonical_size(commit) for commit in model.commit_store.values()
    )
    if model.last_diff_stats.strategy == "log":
        diff_work = model.last_diff_stats.log_operations_examined
        work_unit = "log operations"
    else:
        diff_work = model.last_diff_stats.nodes_compared
        work_unit = "tree nodes"
    return (
        BenchmarkResult(
            model="Revon-H (hybrid)",
            commit_ms=statistics.median(commit_times),
            diff_ms=diff_ms,
            storage_bytes=storage,
            diff_work=diff_work,
            work_unit=work_unit,
            changed_keys=len(changed),
        ),
        changed,
    )


def run_scenario(
    rows: int,
    versions: int = 5,
    changes_per_commit: int = 10,
    diff_repeats: int = 7,
) -> list[BenchmarkResult]:
    if diff_repeats < 1:
        raise ValueError("diff_repeats must be positive")
    initial, batches = build_workload(rows, versions, changes_per_commit)
    measured = [
        benchmark_state(initial, batches, diff_repeats),
        benchmark_operations(initial, batches, diff_repeats),
        benchmark_revon(initial, batches, diff_repeats),
    ]

    expected = measured[0][1]
    for result, changed in measured[1:]:
        if changed != expected:
            raise AssertionError(f"{result.model} returned an incorrect diff")
    return [result for result, _ in measured]


def human_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB"):
        if value < 1024 or unit == "GiB":
            return f"{value:.1f} {unit}"
        value /= 1024
    raise AssertionError("unreachable")


def print_results(
    rows: int, versions: int, changes: int, results: list[BenchmarkResult]
) -> None:
    print()
    print(
        f"Dataset: {rows:,} rows | {versions} versions | "
        f"{changes} mutations per new version"
    )
    print("-" * 102)
    print(
        f"{'Model':<23} {'Commit ms':>11} {'Diff ms':>11} "
        f"{'Storage':>13} {'Diff examined':>23} {'Changed':>9}"
    )
    print("-" * 102)
    for result in results:
        examined = f"{result.diff_work:,} {result.work_unit}"
        print(
            f"{result.model:<23} {result.commit_ms:>11.3f} "
            f"{result.diff_ms:>11.3f} {human_bytes(result.storage_bytes):>13} "
            f"{examined:>23} {result.changed_keys:>9,}"
        )


def parse_sizes(raw: str) -> list[int]:
    try:
        sizes = [int(value.strip()) for value in raw.split(",") if value.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("sizes must be comma-separated integers") from exc
    if not sizes or any(size < 1 for size in sizes):
        raise argparse.ArgumentTypeError("sizes must contain positive integers")
    return sizes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sizes",
        type=parse_sizes,
        default=parse_sizes("1000,10000,100000"),
        help="comma-separated table sizes (default: 1000,10000,100000)",
    )
    parser.add_argument("--versions", type=int, default=5)
    parser.add_argument("--changes", type=int, default=10)
    parser.add_argument("--diff-repeats", type=int, default=7)
    args = parser.parse_args()

    print("Versioning benchmark: full state vs operation log vs Revon-H")
    print("Times are medians; storage is compact serialized data, not Python RAM.")
    for rows in args.sizes:
        results = run_scenario(
            rows,
            versions=args.versions,
            changes_per_commit=args.changes,
            diff_repeats=args.diff_repeats,
        )
        print_results(rows, args.versions, args.changes, results)

    print()
    print(
        "Diff examined uses each model's natural unit: keys, log operations, "
        "or tree-node pairs."
    )
    print("Revon-H commits use atomic incremental copy-on-write path updates.")


if __name__ == "__main__":
    main()
