"""Measure fixed-depth Merkle trie geometry without changing the final benchmark."""

from __future__ import annotations

import argparse
import csv
import json
import math
import platform
import shutil
import statistics
import uuid
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .adapters import RevonAdapter
from .final_benchmark import _measure, _percentile
from .workloads import Workload, WorkloadSpec, build_workload


@dataclass(frozen=True)
class TrieConfig:
    branching_factor: int
    tree_depth: int

    def validate(self) -> None:
        if self.branching_factor < 2 or self.branching_factor & (self.branching_factor - 1):
            raise ValueError("branching factor must be a power of two")
        if self.tree_depth < 1:
            raise ValueError("tree depth must be positive")
        if self.routing_bits > 256:
            raise ValueError("configuration consumes more than 256 routing bits")

    @property
    def leaf_buckets(self) -> int:
        return self.branching_factor**self.tree_depth

    @property
    def routing_bits(self) -> int:
        return int(math.log2(self.branching_factor)) * self.tree_depth

    @property
    def label(self) -> str:
        return f"b{self.branching_factor}-d{self.tree_depth}"


# Three configurations hold 4,096 leaf buckets constant, while b8-d3 and
# b8-d5 vary expected leaf occupancy around the current b8-d4 design.
DEFAULT_CONFIGS = (
    TrieConfig(4, 6),
    TrieConfig(8, 3),
    TrieConfig(8, 4),
    TrieConfig(8, 5),
    TrieConfig(16, 3),
)


@dataclass
class SensitivityRecord:
    run_id: str
    timestamp_utc: str
    status: str
    trial_kind: str
    trial: int
    config: str
    branching_factor: int
    tree_depth: int
    leaf_buckets: int
    routing_bits: int
    expected_leaf_occupancy: float
    seed: int
    rows: int
    commits: int
    changes_per_commit: int
    locality: str
    payload_bytes: int
    workload_sha256: str
    initial_import_ms: Optional[float]
    incremental_commit_ms: Optional[float]
    diff_ms: Optional[float]
    checkout_ms: Optional[float]
    storage_bytes: Optional[int]
    peak_memory_bytes: Optional[int]
    nodes_compared: Optional[int]
    matching_subtrees_skipped: Optional[int]
    leaf_entries_examined: Optional[int]
    new_nodes_per_commit: Optional[float]
    reused_references_per_commit: Optional[float]
    trie_bytes_per_commit: Optional[float]
    changed_keys: Optional[int]
    correctness: Optional[bool]
    notes: str
    python_version: str
    platform: str


def _empty_record(
    run_id: str,
    workload: Workload,
    config: TrieConfig,
    trial_kind: str,
    trial: int,
    *,
    status: str,
    notes: str,
) -> SensitivityRecord:
    spec = workload.spec
    return SensitivityRecord(
        run_id=run_id,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        status=status,
        trial_kind=trial_kind,
        trial=trial,
        config=config.label,
        branching_factor=config.branching_factor,
        tree_depth=config.tree_depth,
        leaf_buckets=config.leaf_buckets,
        routing_bits=config.routing_bits,
        expected_leaf_occupancy=spec.rows / config.leaf_buckets,
        seed=spec.seed,
        rows=spec.rows,
        commits=spec.commits,
        changes_per_commit=spec.changes_per_commit,
        locality=spec.locality,
        payload_bytes=spec.payload_bytes,
        workload_sha256=workload.digest,
        initial_import_ms=None,
        incremental_commit_ms=None,
        diff_ms=None,
        checkout_ms=None,
        storage_bytes=None,
        peak_memory_bytes=None,
        nodes_compared=None,
        matching_subtrees_skipped=None,
        leaf_entries_examined=None,
        new_nodes_per_commit=None,
        reused_references_per_commit=None,
        trie_bytes_per_commit=None,
        changed_keys=None,
        correctness=None,
        notes=notes,
        python_version=platform.python_version(),
        platform=platform.platform(),
    )


def run_sensitivity_trial(
    *,
    run_id: str,
    workload: Workload,
    config: TrieConfig,
    trial_kind: str,
    trial: int,
    scratch_root: Path,
) -> SensitivityRecord:
    trial_path = scratch_root / f"{config.label}-{uuid.uuid4().hex}"
    trial_path.mkdir(parents=True)
    adapter: Optional[RevonAdapter] = None
    try:
        adapter = RevonAdapter(
            trial_path,
            strategy="merkle",
            hybrid_threshold=0,
            branching_factor=config.branching_factor,
            tree_depth=config.tree_depth,
        )
        initial_ms, initial_memory, _ = _measure(
            lambda: adapter.initial_import(workload.initial)
        )
        commit_times: list[float] = []
        memory_peaks = [initial_memory]
        for batch in workload.batches:
            commit_ms, commit_memory, _ = _measure(
                lambda batch=batch: adapter.commit(batch)
            )
            commit_times.append(commit_ms)
            memory_peaks.append(commit_memory)

        diff_ms, diff_memory, diff_keys = _measure(
            lambda: adapter.diff(1, adapter.version)
        )
        memory_peaks.append(diff_memory)
        diff_stats = adapter.repository.last_diff_stats
        checkout_ms, checkout_memory, final_state = _measure(
            lambda: adapter.checkout(adapter.version)
        )
        memory_peaks.append(checkout_memory)

        initial_state = adapter.checkout(1)
        correct = (
            initial_state == workload.states[0]
            and final_state == workload.states[-1]
            and sorted(diff_keys) == workload.expected_diff_keys
        )
        if not correct:
            raise AssertionError("checkout or diff disagrees with the shared workload oracle")

        incremental_stats = [
            stat
            for version, stat in sorted(adapter.repository.commit_stats.items())
            if version > 1
        ]
        record = _empty_record(
            run_id,
            workload,
            config,
            trial_kind,
            trial,
            status="ok",
            notes="",
        )
        return SensitivityRecord(
            **{
                **asdict(record),
                "initial_import_ms": initial_ms,
                "incremental_commit_ms": statistics.median(commit_times),
                "diff_ms": diff_ms,
                "checkout_ms": checkout_ms,
                "storage_bytes": adapter.storage_bytes(),
                "peak_memory_bytes": max(memory_peaks),
                "nodes_compared": diff_stats.nodes_compared,
                "matching_subtrees_skipped": diff_stats.matching_subtrees_skipped,
                "leaf_entries_examined": diff_stats.leaf_entries_examined,
                "new_nodes_per_commit": statistics.median(
                    stat.new_nodes for stat in incremental_stats
                ),
                "reused_references_per_commit": statistics.median(
                    stat.reused_nodes for stat in incremental_stats
                ),
                "trie_bytes_per_commit": statistics.median(
                    stat.bytes_written for stat in incremental_stats
                ),
                "changed_keys": len(workload.expected_diff_keys),
                "correctness": True,
            }
        )
    except Exception as exc:
        return _empty_record(
            run_id,
            workload,
            config,
            trial_kind,
            trial,
            status="error",
            notes=f"{type(exc).__name__}: {exc}",
        )
    finally:
        if adapter is not None:
            adapter.close()
        shutil.rmtree(trial_path, ignore_errors=True)


def _write_raw(path: Path, records: list[SensitivityRecord]) -> None:
    columns = [field.name for field in fields(SensitivityRecord)]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def _write_summary(path: Path, records: list[SensitivityRecord]) -> None:
    metric_names = (
        "initial_import_ms",
        "incremental_commit_ms",
        "diff_ms",
        "checkout_ms",
        "storage_bytes",
        "peak_memory_bytes",
        "nodes_compared",
        "matching_subtrees_skipped",
        "leaf_entries_examined",
        "new_nodes_per_commit",
        "reused_references_per_commit",
        "trie_bytes_per_commit",
    )
    columns = [
        "config",
        "branching_factor",
        "tree_depth",
        "leaf_buckets",
        "routing_bits",
        "expected_leaf_occupancy",
        "trials",
        "all_correct",
    ]
    for metric in metric_names:
        columns.extend((f"{metric}_median", f"{metric}_p25", f"{metric}_p75"))
    groups: dict[str, list[SensitivityRecord]] = {}
    for record in records:
        if record.trial_kind == "measured" and record.status == "ok":
            groups.setdefault(record.config, []).append(record)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for config in sorted(groups, key=lambda label: (int(label.split("-d")[0][1:]), int(label.split("-d")[1]))):
            group = groups[config]
            first = group[0]
            row: dict[str, Any] = {
                "config": config,
                "branching_factor": first.branching_factor,
                "tree_depth": first.tree_depth,
                "leaf_buckets": first.leaf_buckets,
                "routing_bits": first.routing_bits,
                "expected_leaf_occupancy": first.expected_leaf_occupancy,
                "trials": len(group),
                "all_correct": all(record.correctness for record in group),
            }
            for metric in metric_names:
                values = [
                    float(value)
                    for record in group
                    if (value := getattr(record, metric)) is not None
                ]
                row[f"{metric}_median"] = statistics.median(values)
                row[f"{metric}_p25"] = _percentile(values, 0.25)
                row[f"{metric}_p75"] = _percentile(values, 0.75)
            writer.writerow(row)


def execute_sensitivity(
    *,
    output_dir: Path,
    spec: WorkloadSpec,
    configs: tuple[TrieConfig, ...] = DEFAULT_CONFIGS,
    warmups: int = 2,
    trials: int = 7,
) -> list[SensitivityRecord]:
    if warmups < 0 or trials < 1:
        raise ValueError("warmups must be non-negative and trials must be positive")
    if not configs:
        raise ValueError("at least one trie configuration is required")
    for config in configs:
        config.validate()
    if len({config.label for config in configs}) != len(configs):
        raise ValueError("trie configurations must be unique")
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch_root = output_dir / ".work"
    scratch_root.mkdir(exist_ok=True)
    workload = build_workload(spec)
    run_id = uuid.uuid4().hex
    records: list[SensitivityRecord] = []
    for config in configs:
        for kind, count in (("warmup", warmups), ("measured", trials)):
            for trial in range(1, count + 1):
                print(f"[{kind}] {config.label} / {trial}")
                records.append(
                    run_sensitivity_trial(
                        run_id=run_id,
                        workload=workload,
                        config=config,
                        trial_kind=kind,
                        trial=trial,
                        scratch_root=scratch_root,
                    )
                )
    _write_raw(output_dir / "raw_results.csv", records)
    _write_summary(output_dir / "summary.csv", records)
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "purpose": "fixed-depth Merkle trie branching-factor/depth sensitivity",
        "warmups": warmups,
        "measured_trials": trials,
        "workload": asdict(spec),
        "workload_sha256": workload.digest,
        "configs": [
            {
                **asdict(config),
                "label": config.label,
                "leaf_buckets": config.leaf_buckets,
                "routing_bits": config.routing_bits,
                "expected_leaf_occupancy": spec.rows / config.leaf_buckets,
            }
            for config in configs
        ],
        "controlled_variables": {
            "state_and_mutations": "identical workload digest for every configuration and repetition",
            "diff_strategy": "forced Merkle",
            "persistence": "SQLiteRevonRepository",
            "summary": "warmups excluded; median, p25, and p75 over measured trials",
        },
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    try:
        scratch_root.rmdir()
    except OSError:
        pass
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output") / "benchmarks" / f"trie-sensitivity-{datetime.now():%Y%m%d-%H%M%S}",
    )
    parser.add_argument("--rows", type=int, default=10_000)
    parser.add_argument("--commits", type=int, default=10)
    parser.add_argument("--changes-per-commit", type=int, default=100)
    parser.add_argument("--seed", type=int, default=20260824)
    parser.add_argument("--payload-bytes", type=int, default=32)
    parser.add_argument("--locality", choices=("spread", "hot"), default="spread")
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--trials", type=int, default=7)
    args = parser.parse_args()
    spec = WorkloadSpec(
        "trie-sensitivity",
        rows=args.rows,
        commits=args.commits,
        changes_per_commit=args.changes_per_commit,
        seed=args.seed,
        payload_bytes=args.payload_bytes,
        locality=args.locality,
    )
    records = execute_sensitivity(
        output_dir=args.output_dir,
        spec=spec,
        warmups=args.warmups,
        trials=args.trials,
    )
    errors = [record for record in records if record.status != "ok"]
    print(f"Raw results: {args.output_dir / 'raw_results.csv'}")
    print(f"Summary:     {args.output_dir / 'summary.csv'}")
    print(f"Manifest:    {args.output_dir / 'manifest.json'}")
    if errors:
        print(f"ERROR: {len(errors)} trial(s) failed; inspect raw_results.csv")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
