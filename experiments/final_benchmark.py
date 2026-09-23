"""Run the final Snapshot / Log-only / Revon / Dolt experiment matrix.

Use ``python -m experiments.final_benchmark --profile smoke`` for a quick
validation and ``--profile paper`` for the full measurement matrix.
"""

from __future__ import annotations

import argparse
import csv
import gc
import json
import os
import platform
import random
import sqlite3
import shutil
import statistics
import subprocess
import sys
import threading
import time
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
    decode_diff_bytes,
    decode_state_bytes,
    value_digest,
)
from .workloads import Workload, WorkloadSpec, build_workload, profile_specs


MODEL_KEYS = ("snapshot", "log", "revon-m", "revon-h", "dolt", "dolt-bulk")


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
    execution_order: int
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
    logical_payload_bytes: Optional[int]
    storage_bytes_per_logical_payload_byte: Optional[float]
    storage_bytes_minus_logical_payload_bytes: Optional[int]
    storage_bytes_after_compaction: Optional[int]
    compaction_method: str
    compaction_ms: Optional[float]
    process_tree_peak_rss_bytes: Optional[int]
    process_tree_cpu_seconds: Optional[float]
    process_tree_read_bytes: Optional[int]
    process_tree_write_bytes: Optional[int]
    commit_operations_per_second: Optional[float]
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
    """Time one operation; memory is sampled externally by the parent worker."""
    gc.collect()
    started = time.perf_counter_ns()
    try:
        result = function()
    finally:
        elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
    return elapsed_ms, 0, result


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
    execution_order: int,
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
        execution_order=execution_order,
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
        logical_payload_bytes=None,
        storage_bytes_per_logical_payload_byte=None,
        storage_bytes_minus_logical_payload_bytes=None,
        storage_bytes_after_compaction=None,
        compaction_method="",
        compaction_ms=None,
        process_tree_peak_rss_bytes=None,
        process_tree_cpu_seconds=None,
        process_tree_read_bytes=None,
        process_tree_write_bytes=None,
        commit_operations_per_second=None,
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
    if model_key == "dolt-bulk":
        return DoltAdapter(path, bulk_import=True)
    raise ValueError(f"unknown model: {model_key}")


def _run_trial_local(
    *,
    run_id: str,
    phase: str,
    workload: Workload,
    model_key: str,
    trial_kind: str,
    trial: int,
    threshold: int,
    execution_order: int = 1,
    scratch_root: Optional[Path] = None,
    trial_path_override: Optional[Path] = None,
    cleanup_on_exit: bool = True,
) -> TrialRecord:
    model_display = {
        "snapshot": "Snapshot",
        "log": "Log-only",
        "revon-m": "Revon-M (forced Merkle)",
        "revon-h": "Revon-H",
        "revon-log": "Revon-log calibration",
        "dolt": "Dolt",
        "dolt-bulk": "Dolt (bulk import)",
    }[model_key]
    scratch = (scratch_root or Path("tmp") / "experiment-work").resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    trial_path = trial_path_override or (scratch / f"revon-{model_key}-{uuid.uuid4().hex}")
    trial_path.mkdir()
    adapter: Any = None
    try:
        adapter = _adapter_factory(model_key, trial_path, threshold)
        dolt_version = adapter.version_text if model_key in {"dolt", "dolt-bulk"} else ""

        initial_ms, initial_memory, _ = _measure(
            lambda: adapter.initial_import(workload.initial)
        )
        operation_times: list[float] = []
        memory_peaks = [initial_memory]
        for batch in workload.batches:
            commit_ms, commit_memory, _ = _measure(
                lambda batch=batch: adapter.commit(batch)
            )
            operation_times.append(commit_ms)
            memory_peaks.append(commit_memory)

        diff_ms, diff_memory, diff_output = _measure(
            lambda: adapter.diff(1, adapter.version)
        )
        memory_peaks.append(diff_memory)

        checkout_ms, checkout_memory, final_output = _measure(
            lambda: adapter.checkout(adapter.version)
        )
        memory_peaks.append(checkout_memory)

        # Correctness is deliberately outside all timed regions.
        initial_state = decode_state_bytes(adapter.checkout(1))
        final_state = decode_state_bytes(final_output)
        observed_diff = decode_diff_bytes(diff_output)
        state_correct = (
            initial_state == workload.states[0]
            and final_state == workload.states[-1]
        )
        missing = object()
        expected_diff = {
            key: (
                value_digest(workload.states[0].get(key))
                if key in workload.states[0]
                else None,
                value_digest(workload.states[-1].get(key))
                if key in workload.states[-1]
                else None,
            )
            for key in set(workload.states[0]) | set(workload.states[-1])
            if workload.states[0].get(key, missing)
            != workload.states[-1].get(key, missing)
        }
        diff_correct = observed_diff == expected_diff
        correct = state_correct and diff_correct
        if not correct:
            raise AssertionError(
                "checkout or diff disagrees with the workload oracle"
            )

        peak_memory = max(memory_peaks)
        memory_method = "external parent process-tree RSS sampler (psutil, 10 ms; isolated trial)"
        storage_bytes = adapter.storage_bytes()
        logical_payload_bytes = sum(
            len(key.encode("utf-8")) + len(value.encode("utf-8"))
            for key, value in workload.states[-1].items()
        )

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
                        execution_order=execution_order,
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
                "storage_bytes": storage_bytes,
                "logical_payload_bytes": logical_payload_bytes,
                "storage_bytes_per_logical_payload_byte": (
                    storage_bytes / logical_payload_bytes if logical_payload_bytes else None
                ),
                "storage_bytes_minus_logical_payload_bytes": (
                    storage_bytes - logical_payload_bytes if logical_payload_bytes else None
                ),
                "process_tree_peak_rss_bytes": peak_memory,
                "process_tree_cpu_seconds": None,
                "process_tree_read_bytes": None,
                "process_tree_write_bytes": None,
                "commit_operations_per_second": (
                    len(operation_times) / (sum(operation_times) / 1000)
                    if operation_times and sum(operation_times) > 0
                    else None
                ),
                "memory_method": memory_method,
                "work_examined": adapter.work_examined,
                "work_unit": adapter.work_unit,
                "changed_keys": len(observed_diff),
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
            execution_order=execution_order,
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
            execution_order=execution_order,
            threshold=threshold,
            status="error",
            notes=f"{type(exc).__name__}: {exc}",
        )
    finally:
        try:
            if adapter is not None:
                adapter.close()
        finally:
            if cleanup_on_exit:
                shutil.rmtree(trial_path, ignore_errors=True)


def _compact_trial_repository(path: Path, model_key: str) -> tuple[Optional[int], str, Optional[float]]:
    if model_key in {"dolt", "dolt-bulk"}:
        executable = DoltAdapter.executable()
        if executable is None:
            return None, "unavailable", None
        method = "dolt gc (offline)"
        command = [executable, "gc"]
        started = time.perf_counter_ns()
        result = subprocess.run(command, cwd=path, capture_output=True, text=True)
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        if result.returncode != 0:
            raise RuntimeError(f"Dolt GC failed: {result.stderr.strip()}")
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()), method, elapsed
    if model_key in {"revon-m", "revon-h"}:
        method = "SQLite VACUUM"
        started = time.perf_counter_ns()
        connection = sqlite3.connect(path / "revon.sqlite")
        try:
            connection.execute("VACUUM")
        finally:
            connection.close()
        elapsed = (time.perf_counter_ns() - started) / 1_000_000
        return sum(item.stat().st_size for item in path.rglob("*") if item.is_file()), method, elapsed
    return None, "not applicable", None


def _linux_process_tree_sample(root_pid: int) -> list[tuple[int, int, float, int, int]]:
    """Read RSS, CPU, and I/O counters for root_pid and its descendants from /proc."""
    process_root = Path("/proc")
    page_size = int(os.sysconf("SC_PAGE_SIZE"))
    ticks_per_second = int(os.sysconf("SC_CLK_TCK"))
    parents: dict[int, int] = {}
    stats: dict[int, tuple[int, float, int, int]] = {}
    for entry in process_root.iterdir():
        if not entry.name.isdigit():
            continue
        pid = int(entry.name)
        try:
            raw = (entry / "stat").read_text(encoding="ascii")
            after_comm = raw[raw.rfind(")") + 2 :].split()
            ppid = int(after_comm[1])
            user_ticks = int(after_comm[11])
            system_ticks = int(after_comm[12])
            resident_pages = int(after_comm[21])
            io_fields = {}
            for line in (entry / "io").read_text(encoding="ascii").splitlines():
                name, value = line.split(":", 1)
                io_fields[name] = int(value.strip())
            parents[pid] = ppid
            stats[pid] = (
                resident_pages * page_size,
                (user_ticks + system_ticks) / ticks_per_second,
                io_fields.get("read_bytes", 0),
                io_fields.get("write_bytes", 0),
            )
        except (OSError, ValueError, IndexError):
            continue
    descendants = {root_pid}
    changed = True
    while changed:
        changed = False
        for pid, ppid in parents.items():
            if ppid in descendants and pid not in descendants:
                descendants.add(pid)
                changed = True
    return [
        (pid, *stats[pid])
        for pid in descendants
        if pid in stats
    ]


def run_trial(
    *,
    run_id: str,
    phase: str,
    workload: Workload,
    model_key: str,
    trial_kind: str,
    trial: int,
    threshold: int,
    execution_order: int = 1,
    scratch_root: Optional[Path] = None,
) -> TrialRecord:
    """Run one isolated trial so prior models cannot inflate its RSS baseline."""
    scratch = (scratch_root or Path("tmp") / "experiment-work").resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    config_path = scratch / f"worker-{token}.json"
    result_path = scratch / f"worker-{token}.result.json"
    trial_path = scratch / f"repository-{token}"
    config = {
        "run_id": run_id,
        "phase": phase,
        "workload_spec": asdict(workload.spec),
        "workload_sha256": workload.digest,
        "model_key": model_key,
        "trial_kind": trial_kind,
        "trial": trial,
        "execution_order": execution_order,
        "threshold": threshold,
        "scratch_root": str(scratch),
        "trial_path": str(trial_path),
        "result_path": str(result_path),
    }
    config_path.write_text(json.dumps(config), encoding="utf-8")
    try:
        try:
            import psutil
        except ImportError:
            psutil = None
        if psutil is None and not Path("/proc").is_dir():
            raise RuntimeError("process-tree sampling requires psutil or Linux /proc")

        process = subprocess.Popen(
            [sys.executable, "-m", "experiments.final_benchmark", "--worker-config", str(config_path)],
            cwd=Path(__file__).resolve().parents[1],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        tracked = psutil.Process(process.pid) if psutil is not None else None
        stop = threading.Event()
        sampled_peak = [0]
        sampled_counters: dict[int, tuple[float, int, int]] = {}

        def sample_process_tree() -> None:
            while not stop.is_set():
                if psutil is None:
                    samples = _linux_process_tree_sample(process.pid)
                    rss = 0
                    for pid, resident, cpu_seconds, read_bytes, write_bytes in samples:
                        rss += resident
                        previous = sampled_counters.get(pid, (0.0, 0, 0))
                        sampled_counters[pid] = (
                            max(previous[0], cpu_seconds),
                            max(previous[1], read_bytes),
                            max(previous[2], write_bytes),
                        )
                    sampled_peak[0] = max(sampled_peak[0], rss)
                else:
                    try:
                        processes = [tracked, *tracked.children(recursive=True)]
                        rss = 0
                        for child in processes:
                            try:
                                rss += child.memory_info().rss
                                cpu = child.cpu_times()
                                io = child.io_counters()
                                previous = sampled_counters.get(child.pid, (0.0, 0, 0))
                                sampled_counters[child.pid] = (
                                    max(previous[0], cpu.user + cpu.system),
                                    max(previous[1], int(io.read_bytes)),
                                    max(previous[2], int(io.write_bytes)),
                                )
                            except (psutil.NoSuchProcess, psutil.AccessDenied):
                                continue
                            except (AttributeError, NotImplementedError, OSError):
                                try:
                                    cpu = child.cpu_times()
                                    previous = sampled_counters.get(child.pid, (0.0, 0, 0))
                                    sampled_counters[child.pid] = (
                                        max(previous[0], cpu.user + cpu.system),
                                        previous[1],
                                        previous[2],
                                    )
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass
                        sampled_peak[0] = max(sampled_peak[0], rss)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                stop.wait(0.010)

        monitor = threading.Thread(target=sample_process_tree, daemon=True)
        monitor.start()
        stdout, stderr = process.communicate()
        stop.set()
        monitor.join(timeout=0.1)
        if process.returncode != 0 or not result_path.exists():
            raise RuntimeError(
                f"isolated trial worker failed ({process.returncode}): "
                f"{stderr.strip()} {stdout.strip()}"
            )
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        if payload["status"] == "ok":
            if sampled_peak[0] <= 0:
                raise RuntimeError("external RSS monitor recorded no process samples")
            payload["process_tree_peak_rss_bytes"] = sampled_peak[0]
            payload["process_tree_cpu_seconds"] = sum(item[0] for item in sampled_counters.values())
            payload["process_tree_read_bytes"] = (
                sum(item[1] for item in sampled_counters.values())
                if any(item[1] for item in sampled_counters.values())
                else None
            )
            payload["process_tree_write_bytes"] = (
                sum(item[2] for item in sampled_counters.values())
                if any(item[2] for item in sampled_counters.values())
                else None
            )
            payload["memory_method"] = (
                "external parent process-tree RSS/CPU/I-O sampler (10 ms; psutil or Linux /proc; isolated trial)"
            )
            if phase == "evaluation" and trial_kind == "measured" and trial == 1:
                compacted, method, elapsed = _compact_trial_repository(trial_path, model_key)
                payload["storage_bytes_after_compaction"] = compacted
                payload["compaction_method"] = method
                payload["compaction_ms"] = elapsed
            elif model_key in {"dolt", "dolt-bulk", "revon-m", "revon-h"}:
                payload["compaction_method"] = "not sampled"
            else:
                payload["compaction_method"] = "not applicable"
        return TrialRecord(**payload)
    except Exception as exc:
        return _empty_record(
            run_id=run_id,
            phase=phase,
            workload=workload,
            model={
                "snapshot": "Snapshot",
                "log": "Log-only",
                "revon-m": "Revon-M (forced Merkle)",
                "revon-h": "Revon-H",
                "revon-log": "Revon-log calibration",
                "dolt": "Dolt",
                "dolt-bulk": "Dolt (bulk import)",
            }[model_key],
            trial_kind=trial_kind,
            trial=trial,
            execution_order=execution_order,
            threshold=threshold,
            status="error",
            notes=f"{type(exc).__name__}: {exc}",
        )
    finally:
        shutil.rmtree(trial_path, ignore_errors=True)
        config_path.unlink(missing_ok=True)
        result_path.unlink(missing_ok=True)


def _run_worker_config(path: Path) -> int:
    config = json.loads(path.read_text(encoding="utf-8"))
    workload = build_workload(WorkloadSpec(**config["workload_spec"]))
    if workload.digest != config["workload_sha256"]:
        raise ValueError("isolated worker regenerated a different workload digest")
    record = _run_trial_local(
        run_id=config["run_id"],
        phase=config["phase"],
        workload=workload,
        model_key=config["model_key"],
        trial_kind=config["trial_kind"],
        trial=int(config["trial"]),
        execution_order=int(config["execution_order"]),
        threshold=int(config["threshold"]),
        scratch_root=Path(config["scratch_root"]),
        trial_path_override=Path(config["trial_path"]),
        cleanup_on_exit=False,
    )
    Path(config["result_path"]).write_text(
        json.dumps(asdict(record), sort_keys=True), encoding="utf-8"
    )
    return 0


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
        "logical_payload_bytes",
        "storage_bytes_per_logical_payload_byte",
        "storage_bytes_minus_logical_payload_bytes",
        "storage_bytes_after_compaction",
        "compaction_ms",
        "process_tree_peak_rss_bytes",
        "process_tree_cpu_seconds",
        "process_tree_read_bytes",
        "process_tree_write_bytes",
        "commit_operations_per_second",
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


def _blocked_model_order(
    models: tuple[str, ...], *, seed: int, phase: str, scenario: str, kind: str, trial: int
) -> list[str]:
    """Randomize a base order, then rotate it to balance positions across trials."""
    order = list(models)
    random.Random(f"{seed}|{phase}|{scenario}|{kind}").shuffle(order)
    offset = (trial - 1) % len(order)
    return order[offset:] + order[:offset]


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
        for trial_kind, count in (("warmup", warmups), ("measured", trials)):
            for trial in range(1, count + 1):
                order = _blocked_model_order(
                    calibration_models,
                    seed=seed,
                    phase="calibration",
                    scenario=spec.name,
                    kind=trial_kind,
                    trial=trial,
                )
                for execution_order, model_key in enumerate(order, start=1):
                    print(
                        f"[{phase_label('calibration', trial_kind)}] "
                        f"{spec.name} / {model_key} / {trial} / order {execution_order}"
                    )
                    records.append(
                        run_trial(
                            run_id=run_id,
                            phase="calibration",
                            workload=workload,
                            model_key=model_key,
                            trial_kind=trial_kind,
                            trial=trial,
                            execution_order=execution_order,
                            threshold=0,
                            scratch_root=scratch_root,
                        )
                    )
    threshold = calibrate_threshold(records)
    print(f"Calibrated Revon-H log threshold: {threshold} operations")

    for spec in profile_specs(profile, seed + 10_000, phase="evaluation"):
        workload = build_workload(spec)
        for trial_kind, count in (("warmup", warmups), ("measured", trials)):
            for trial in range(1, count + 1):
                order = _blocked_model_order(
                    models,
                    seed=seed,
                    phase="evaluation",
                    scenario=spec.name,
                    kind=trial_kind,
                    trial=trial,
                )
                for execution_order, model_key in enumerate(order, start=1):
                    print(
                        f"[{phase_label('evaluation', trial_kind)}] "
                        f"{spec.name} / {model_key} / {trial} / order {execution_order}"
                    )
                    records.append(
                        run_trial(
                            run_id=run_id,
                            phase="evaluation",
                            workload=workload,
                            model_key=model_key,
                            trial_kind=trial_kind,
                            trial=trial,
                            execution_order=execution_order,
                            threshold=threshold,
                            scratch_root=scratch_root,
                        )
                    )

    _write_csv(output_dir / "raw_results.csv", records)
    _write_summary(output_dir / "summary.csv", records)
    manifest = {
        "schema_version": 5,
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
            "diff": "sorted changed keys and old/new SHA-256 value hashes, fully materialized as canonical JSON inside the timed region for every system",
            "checkout": "full target-version state, sorted and materialized as canonical UTF-8 JSON inside the timed region for every system",
            "storage": "bytes in the adapter repository directory",
            "storage_normalization": "total repository bytes divided by UTF-8 key/value state bytes at the final version; a workflow ratio, not an isolated index efficiency score",
            "storage_residual": "repository bytes minus raw UTF-8 key/value bytes; includes encoding, indexing, metadata, and compression effects and is not pure metadata overhead",
            "post_compaction_storage": "measured on the first measured trial per evaluation scenario after offline dolt gc for both Dolt import modes and SQLite VACUUM for Revon-M and Revon-H; compaction timing is outside benchmark operation timing and RSS sampling; not applicable to Snapshot and Log-only file baselines",
            "process_tree_peak_rss": "sampled externally by the parent every 10 ms for isolated per-trial processes, including Dolt child processes; sampling is outside the timed worker operations",
            "process_tree_cpu_io": "cumulative process-tree CPU time and bytes read/written sampled externally by the parent every 10 ms; includes setup and correctness checks, not operation-specific counters; some platforms may not expose per-process I/O counters",
            "commit_operation_throughput": "number of durable commits divided by the sum of their individual timed intervals; serial commit-only rate, not concurrent or end-to-end throughput",
            "correctness": "initial/final checkout and observed common diff contract; old/new value hashes checked against the workload oracle",
            "dolt_commit": "SQL mutation, add, and commit; no per-version tag command",
            "comparison_scope": "in-process Revon API versus Dolt CLI workflow; not an engine-only algorithm comparison",
            "model_order": "models are deterministically randomized within scenario/trial blocks; raw execution_order records each model's position",
            "dolt_initial_import": "Dolt uses the SQL INSERT workflow; Dolt (bulk import) uses dolt table import -r. These import workflows are reported separately",
            "audit_scope": "internal evidence-integrity check; does not independently reproduce raw timings",
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
    parser.add_argument("--worker-config", type=Path, help=argparse.SUPPRESS)
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
    if args.worker_config is not None:
        return _run_worker_config(args.worker_config)
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
