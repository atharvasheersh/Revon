"""Run a compact seed, payload, history, and locality sensitivity study."""

from __future__ import annotations

import argparse
import json
import platform
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .adapters import DoltAdapter
from .final_benchmark import (
    _blocked_model_order,
    _write_csv,
    _write_summary,
    run_trial,
)
from .workloads import WorkloadSpec


SEEDS = (20260923, 20261017, 20261111)
MODELS = ("revon-m", "revon-h", "dolt")
THRESHOLD = 4096  # frozen from the separately audited paper calibration


def specs() -> list[WorkloadSpec]:
    cases = (
        ("baseline", 10, 32, "spread"),
        ("payload-128", 10, 128, "spread"),
        ("history-50", 50, 32, "spread"),
        ("range-local", 10, 32, "range-local"),
        ("repeated-key", 10, 32, "repeated-key"),
    )
    result = []
    for seed_index, seed in enumerate(SEEDS):
        for name, commits, payload_bytes, locality in cases:
            result.append(
                WorkloadSpec(
                    name=f"robust-s{seed_index + 1}-{name}",
                    rows=10_000,
                    commits=commits,
                    changes_per_commit=100,
                    seed=seed,
                    payload_bytes=payload_bytes,
                    locality=locality,
                )
            )
    return result


def execute(
    output_dir: Path,
    *,
    warmups: int = 2,
    trials: int = 7,
    scratch_dir: Path | None = None,
) -> dict:
    if warmups < 0 or trials < 1:
        raise ValueError("warmups must be non-negative and trials must be positive")
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    scratch = (scratch_dir or (output_dir / ".work")).resolve()
    scratch.mkdir(exist_ok=True)
    records = []
    for spec in specs():
        from .workloads import build_workload

        workload = build_workload(spec)
        for kind, count in (("warmup", warmups), ("measured", trials)):
            for trial in range(1, count + 1):
                order = _blocked_model_order(
                    MODELS,
                    seed=spec.seed,
                    phase="robustness",
                    scenario=spec.name,
                    kind=kind,
                    trial=trial,
                )
                for position, model in enumerate(order, start=1):
                    print(f"[{kind}] {spec.name} / {model} / {trial} / order {position}", flush=True)
                    records.append(
                        run_trial(
                            run_id=run_id,
                            phase="robustness",
                            workload=workload,
                            model_key=model,
                            trial_kind=kind,
                            trial=trial,
                            execution_order=position,
                            threshold=THRESHOLD,
                            scratch_root=scratch,
                        )
                    )
    _write_csv(output_dir / "raw_results.csv", records)
    _write_summary(output_dir / "summary.csv", records)
    manifest = {
        "schema_version": 2,
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "study": "robustness",
        "warmups": warmups,
        "measured_trials": trials,
        "seeds": list(SEEDS),
        "models": list(MODELS),
        "frozen_hybrid_threshold_operations": THRESHOLD,
        "workloads": [asdict(spec) for spec in specs()],
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "dolt_executable_available": DoltAdapter.executable() is not None,
        "limitations": [
            "single Windows host",
            "synthetic flat key-value table only",
            "10,000 rows only; not a one-million-row scale test",
            "no public multi-table dataset",
        ],
        "scope": "sensitivity evidence only; do not pool with the paper's eight primary scenarios",
        "operational_telemetry": "external parent process-tree CPU seconds and read/write bytes sampled every 10 ms, when supported; commit-operation throughput is commits divided by summed timed commit intervals",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return {"rows": len(records), "ok": sum(row.status == "ok" for row in records), "run_id": run_id}


def audit(directory: Path) -> dict:
    import csv
    from .workloads import build_workload

    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    with (directory / "raw_results.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    issues: list[str] = []
    expected_rows = len(manifest["workloads"]) * len(MODELS) * (manifest["warmups"] + manifest["measured_trials"])
    if len(rows) != expected_rows:
        issues.append(f"row count {len(rows)} != expected {expected_rows}")
    expected_hashes = {
        item["name"]: build_workload(WorkloadSpec(**item)).digest
        for item in manifest["workloads"]
    }
    for row in rows:
        if row["status"] != "ok" or row["correctness"] != "True":
            issues.append(f"{row['scenario']}/{row['model']}/{row['trial_kind']}/{row['trial']}: unsuccessful or incorrect")
        if row["workload_sha256"] != expected_hashes.get(row["scenario"]):
            issues.append(f"{row['scenario']}: workload digest mismatch")
        if manifest.get("schema_version", 1) >= 2:
            cpu = row["process_tree_cpu_seconds"]
            throughput = row["commit_operations_per_second"]
            if cpu == "" or float(cpu) < 0:
                issues.append(f"{row['scenario']}/{row['model']}: missing or invalid external CPU sample")
            if throughput == "" or float(throughput) <= 0:
                issues.append(f"{row['scenario']}/{row['model']}: missing or invalid commit throughput")
    measured = [row for row in rows if row["trial_kind"] == "measured"]
    (directory / "audit.json").write_text(json.dumps({
        "passed": not issues,
        "issues": issues,
        "rows": len(rows),
        "measured_rows": len(measured),
        "all_correct": all(row["correctness"] == "True" for row in rows),
    }, indent=2), encoding="utf-8")
    if issues:
        raise RuntimeError(f"robustness audit failed: {issues[:5]}")
    return {"passed": True, "rows": len(rows), "measured_rows": len(measured)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--trials", type=int, default=7)
    parser.add_argument("--scratch-dir", type=Path)
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    result = audit(args.output_dir) if args.audit else execute(
        args.output_dir,
        warmups=args.warmups,
        trials=args.trials,
        scratch_dir=args.scratch_dir,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
