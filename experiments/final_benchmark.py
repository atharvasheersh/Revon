"""Run the final Snapshot / Log-only / Revon / Dolt experiment matrix.

Use ``python -m experiments.final_benchmark --profile smoke`` for a quick
validation and ``--profile paper`` for the full measurement matrix.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import platform
import shutil
import statistics
import time
import tracemalloc
import uuid
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from .adapters import (
    RevonAdapter,
    DoltAdapter,
    DoltUnavailableError,
    LogOnlyAdapter,
    SnapshotAdapter,
)
from .workloads import Workload, WorkloadSpec, build_workload, profile_specs


MODEL_KEYS = ("snapshot", "log", "revon-m", "revon-h", "dolt")


@dataclass
class TrialRecord:
    run_id: str
    timestamp_utc: str
    phase: str
    scenario: str
    model: str
    status: str
    trial_kind: str
    trial: int
    seed: int
    rows: int
    commits: int
    changes_per_commit: int
    locality: str
    payload_bytes: int
    workload_sha256: str
    strategy_requested: str
    strategy_selected: str
    hybrid_threshold: int
    initial_import_ms: Optional[float]
    incremental_commit_ms: Optional[float]
    diff_ms: Optional[float]
    checkout_ms: Optional[float]
    storage_bytes: Optional[int]
    peak_memory_bytes: Optional[int]
    memory_method: str
    work_examined: Optional[int]
    work_unit: str
    changed_keys: Optional[int]
    correctness: Optional[bool]
    notes: str
    python_version: str
    platform: str
    dolt_version: str


def _measure(function: Callable[[], Any]) -> tuple[float, int, Any]:
    """Measure elapsed time and incremental traced Python allocations."""

    gc.collect()
    tracemalloc.start()
    before, _ = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    started = time.perf_counter_ns()
    try:
        result = function()
    finally:
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    return elapsed_ms, max(0, peak - before), result


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    location = (len(ordered) - 1) * fraction
    lower = int(location)
    upper = min(lower + 1, len(ordered) - 1)
    weight = location - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _empty_record(
    *,
    run_id: str,
    phase: str,
    workload: Workload,
    model: str,
    trial_kind: str,
    trial: int,
    threshold: int,
    status: str,
    notes: str,
    dolt_version: str = "",
) -> TrialRecord:
    spec = workload.spec
    return TrialRecord(
        run_id=run_id,
        timestamp_utc=datetime.now(timezone.utc).isoformat(),
        phase=phase,
        scenario=spec.name,
        model=model,
        status=status,
        trial_kind=trial_kind,
        trial=trial,
        seed=spec.seed,
        rows=spec.rows,
        commits=spec.commits,
        changes_per_commit=spec.changes_per_commit,
        locality=spec.locality,
        payload_bytes=spec.payload_bytes,
        workload_sha256=workload.digest,
        strategy_requested="",
        strategy_selected="",
        hybrid_threshold=threshold,
        initial_import_ms=None,
        incremental_commit_ms=None,
        diff_ms=None,
        checkout_ms=None,
        storage_bytes=None,
        peak_memory_bytes=None,
        memory_method="",
        work_examined=None,
        work_unit="",
        changed_keys=None,
        correctness=None,
        notes=notes,
        python_version=platform.python_version(),
        platform=platform.platform(),
        dolt_version=dolt_version,
    )


def _adapter_factory(model_key: str, path: Path, threshold: int) -> Any:
    if model_key == "snapshot":
        return SnapshotAdapter(path)
    if model_key == "log":
        return LogOnlyAdapter(path)
    if model_key == "revon-m":
        return RevonAdapter(path, strategy="merkle", hybrid_threshold=threshold)
    if model_key == "revon-h":
        return RevonAdapter(path, strategy="hybrid", hybrid_threshold=threshold)
    if model_key == "revon-log":
        return RevonAdapter(path, strategy="log", hybrid_threshold=threshold)
    if model_key == "dolt":
        return DoltAdapter(path)
    raise ValueError(f"unknown model: {model_key}")


def run_trial(
    *,
    run_id: str,
    phase: str,
    workload: Workload,
    model_key: str,
    trial_kind: str,
    trial: int,
    threshold: int,
    scratch_root: Optional[Path] = None,
) -> TrialRecord:
    model_display = {
        "snapshot": "Snapshot",
        "log": "Log-only",
        "revon-m": "Revon-M (forced Merkle)",
        "revon-h": "Revon-H",
        "revon-log": "Revon-log calibration",
        "dolt": "Dolt",
    }[model_key]
    scratch = (scratch_root or Path("tmp") / "experiment-work").resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    trial_path = scratch / f"revon-{model_key}-{uuid.uuid4().hex}"
    trial_path.mkdir()
    adapter: Any = None
    try:
        adapter = _adapter_factory(model_key, trial_path, threshold)
        dolt_version = adapter.version_text if model_key == "dolt" else ""

        initial_ms, initial_memory, _ = _measure(
            lambda: adapter.initial_import(workload.initial)
        )
        operation_times: list[float] = []
        memory_peaks = [initial_memory]
        external_peaks: list[int] = []
        if adapter.external_peak_memory is not None:
            external_peaks.append(adapter.external_peak_memory)
        for batch in workload.batches:
            commit_ms, commit_memory, _ = _measure(
                lambda batch=batch: adapter.commit(batch)
            )
            operation_times.append(commit_ms)
            memory_peaks.append(commit_memory)
            if adapter.external_peak_memory is not None:
                external_peaks.append(adapter.external_peak_memory)

        diff_ms, diff_memory, diff_keys = _measure(
            lambda: adapter.diff(1, adapter.version)
        )
        memory_peaks.append(diff_memory)
        if adapter.external_peak_memory is not None:
            external_peaks.append(adapter.external_peak_memory)

        checkout_ms, checkout_memory, final_state = _measure(
            lambda: adapter.checkout(adapter.version)
        )
        memory_peaks.append(checkout_memory)
        if adapter.external_peak_memory is not None:
            external_peaks.append(adapter.external_peak_memory)

        # Correctness is deliberately outside all timed regions.
        initial_state = adapter.checkout(1)
        state_correct = (
            initial_state == workload.states[0]
            and final_state == workload.states[-1]
        )
        diff_correct = (
            diff_keys is None
            or sorted(diff_keys) == workload.expected_diff_keys
        )
        correct = state_correct and diff_correct
        if not correct:
            raise AssertionError(
                "checkout or diff disagrees with the workload oracle"
            )

        if model_key == "dolt":
            peak_memory = max(external_peaks) if external_peaks else None
            memory_method = (
                "process-tree RSS via optional psutil"
                if external_peaks
                else "unavailable (install psutil)"
            )
        else:
            peak_memory = max(memory_peaks)
            memory_method = "incremental Python allocations via tracemalloc"

        return TrialRecord(
            **{
                **asdict(
                    _empty_record(
                        run_id=run_id,
                        phase=phase,
                        workload=workload,
                        model=model_display,
                        trial_kind=trial_kind,
                        trial=trial,
                        threshold=threshold,
                        status="ok",
                        notes="",
                        dolt_version=dolt_version,
                    )
                ),
                "strategy_requested": adapter.strategy_requested,
                "strategy_selected": adapter.strategy_selected,
                "initial_import_ms": initial_ms,
                "incremental_commit_ms": statistics.median(operation_times),
                "diff_ms": diff_ms,
                "checkout_ms": checkout_ms,
                "storage_bytes": adapter.storage_bytes(),
                "peak_memory_bytes": peak_memory,
                "memory_method": memory_method,
                "work_examined": adapter.work_examined,
                "work_unit": adapter.work_unit,
                "changed_keys": len(workload.expected_diff_keys),
                "correctness": correct,
            }
        )
    except DoltUnavailableError as exc:
        return _empty_record(
            run_id=run_id,
            phase=phase,
            workload=workload,
            model=model_display,
            trial_kind=trial_kind,
            trial=trial,
            threshold=threshold,
            status="unavailable",
            notes=str(exc),
        )
    except Exception as exc:
        return _empty_record(
            run_id=run_id,
            phase=phase,
            workload=workload,
            model=model_display,
            trial_kind=trial_kind,
            trial=trial,
            threshold=threshold,
            status="error",
            notes=f"{type(exc).__name__}: {exc}",
        )
    finally:
        try:
            if adapter is not None:
                adapter.close()
        finally:
            shutil.rmtree(trial_path, ignore_errors=True)


def _write_csv(path: Path, records: list[TrialRecord]) -> None:
    columns = [field.name for field in fields(TrialRecord)]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)


def _write_summary(path: Path, records: list[TrialRecord]) -> None:
    metrics = (
        "initial_import_ms",
        "incremental_commit_ms",
        "diff_ms",
        "checkout_ms",
        "storage_bytes",
        "peak_memory_bytes",
        "work_examined",
    )
    groups: dict[tuple[str, str, str], list[TrialRecord]] = {}
    for record in records:
        if record.trial_kind == "measured" and record.status == "ok":
            groups.setdefault((record.phase, record.scenario, record.model), []).append(record)
    columns = [
        "phase",
        "scenario",
        "model",
        "trials",
        "all_correct",
        "strategy_selected",
        "work_unit",
    ]
    for metric in metrics:
        columns.extend((f"{metric}_median", f"{metric}_p25", f"{metric}_p75"))
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for (phase, scenario, model), group in sorted(groups.items()):
            row: dict[str, Any] = {
                "phase": phase,
                "scenario": scenario,
                "model": model,
                "trials": len(group),
                "all_correct": all(record.correctness for record in group),
                "strategy_selected": ";".join(
                    sorted({record.strategy_selected for record in group})
                ),
                "work_unit": ";".join(
                    sorted({record.work_unit for record in group})
                ),
            }
            for metric in metrics:
                values = [
                    float(value)
                    for record in group
                    if (value := getattr(record, metric)) is not None
                ]
                row[f"{metric}_median"] = statistics.median(values) if values else ""
                row[f"{metric}_p25"] = _percentile(values, 0.25) if values else ""
                row[f"{metric}_p75"] = _percentile(values, 0.75) if values else ""
            writer.writerow(row)


def calibrate_threshold(records: list[TrialRecord]) -> int:
    """Select the largest tested operation count at which log is no slower."""

    grouped: dict[tuple[str, str], list[float]] = {}
    operation_counts: dict[str, int] = {}
    for record in records:
        if (
            record.phase != "calibration"
            or record.trial_kind != "measured"
            or record.status != "ok"
        ):
            continue
        grouped.setdefault(
            (record.scenario, record.strategy_requested), []
        ).append(record.diff_ms or 0.0)
        operation_counts[record.scenario] = record.commits * record.changes_per_commit
    winning_counts: list[int] = []
    for scenario, operation_count in operation_counts.items():
        log = grouped.get((scenario, "log"), [])
        merkle = grouped.get((scenario, "merkle"), [])
        if log and merkle and statistics.median(log) <= statistics.median(merkle):
            winning_counts.append(operation_count)
    return max(winning_counts, default=0)


def execute(
    *,
    profile: str,
    output_dir: Path,
    warmups: int,
    trials: int,
    seed: int,
    models: tuple[str, ...],
) -> tuple[list[TrialRecord], int]:
    if warmups < 0 or trials < 1:
        raise ValueError("warmups must be non-negative and trials must be positive")
    invalid = set(models) - set(MODEL_KEYS)
    if invalid:
        raise ValueError(f"unknown models: {sorted(invalid)}")
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch_root = output_dir / ".work"
    scratch_root.mkdir(exist_ok=True)
    run_id = uuid.uuid4().hex
    records: list[TrialRecord] = []

    calibration_models = ("revon-log", "revon-m")
    for spec in profile_specs(profile, seed, phase="calibration"):
        workload = build_workload(spec)
        for model_key in calibration_models:
            for trial_kind, count in (("warmup", warmups), ("measured", trials)):
                for trial in range(1, count + 1):
                    print(
                        f"[{phase_label('calibration', trial_kind)}] "
                        f"{spec.name} / {model_key} / {trial}"
                    )
                    records.append(
                        run_trial(
                            run_id=run_id,
                            phase="calibration",
                            workload=workload,
                            model_key=model_key,
                            trial_kind=trial_kind,
                            trial=trial,
                            threshold=0,
                            scratch_root=scratch_root,
                        )
                    )
    threshold = calibrate_threshold(records)
    print(f"Calibrated Revon-H log threshold: {threshold} operations")

    for spec in profile_specs(profile, seed + 10_000, phase="evaluation"):
        workload = build_workload(spec)
        for model_key in models:
            for trial_kind, count in (("warmup", warmups), ("measured", trials)):
                for trial in range(1, count + 1):
                    print(
                        f"[{phase_label('evaluation', trial_kind)}] "
                        f"{spec.name} / {model_key} / {trial}"
                    )
                    records.append(
                        run_trial(
                            run_id=run_id,
                            phase="evaluation",
                            workload=workload,
                            model_key=model_key,
                            trial_kind=trial_kind,
                            trial=trial,
                            threshold=threshold,
                            scratch_root=scratch_root,
                        )
                    )

    _write_csv(output_dir / "raw_results.csv", records)
    _write_summary(output_dir / "summary.csv", records)
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "profile": profile,
        "warmups": warmups,
        "measured_trials": trials,
        "base_seed": seed,
        "models": list(models),
        "hybrid_threshold_operations": threshold,
        "dolt_available": DoltAdapter.executable() is not None,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "processor": platform.processor(),
        "metric_contract": {
            "setup": "excluded",
            "initial_import": "first durable state and version",
            "incremental_commit": "median durable commit within one trial",
            "diff": "complete version diff",
            "checkout": "full target-version materialization",
            "storage": "bytes in the adapter repository directory",
            "correctness": "initial/final checkout and changed-key oracle",
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    try:
        scratch_root.rmdir()
    except OSError:
        # Failed trial cleanup is non-fatal and remains isolated under output.
        pass
    return records, threshold


def phase_label(phase: str, trial_kind: str) -> str:
    return f"{phase}:{trial_kind}"


def parse_models(raw: str) -> tuple[str, ...]:
    models = tuple(value.strip() for value in raw.split(",") if value.strip())
    if not models:
        raise argparse.ArgumentTypeError("at least one model is required")
    invalid = set(models) - set(MODEL_KEYS)
    if invalid:
        raise argparse.ArgumentTypeError(f"unknown models: {sorted(invalid)}")
    return models


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("smoke", "paper"), default="smoke")
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--seed", type=int, default=20260822)
    parser.add_argument("--models", type=parse_models, default=MODEL_KEYS)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output") / "benchmarks" / datetime.now().strftime("%Y%m%d-%H%M%S"),
    )
    args = parser.parse_args()
    records, threshold = execute(
        profile=args.profile,
        output_dir=args.output_dir,
        warmups=args.warmups,
        trials=args.trials,
        seed=args.seed,
        models=args.models,
    )
    errors = [record for record in records if record.status == "error"]
    unavailable = [record for record in records if record.status == "unavailable"]
    print(f"Raw results: {args.output_dir / 'raw_results.csv'}")
    print(f"Summary:     {args.output_dir / 'summary.csv'}")
    print(f"Manifest:    {args.output_dir / 'manifest.json'}")
    print(f"Revon-H threshold: {threshold} operations")
    if unavailable:
        print("Dolt rows were marked unavailable because the dolt executable is not on PATH.")
    if errors:
        print(f"ERROR: {len(errors)} trial(s) failed; inspect raw_results.csv")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
