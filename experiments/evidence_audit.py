"""Audit a Revon benchmark evidence bundle without altering source CSV rows."""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

from .final_benchmark import MODEL_KEYS, _percentile
from .workloads import build_workload, profile_specs


METRICS = (
    "initial_import_ms",
    "incremental_commit_ms",
    "diff_ms",
    "checkout_ms",
    "storage_bytes",
    "peak_memory_bytes",
    "work_examined",
)

DISPLAY_MODELS = {
    "snapshot": "Snapshot",
    "log": "Log-only",
    "revon-m": "Revon-M (forced Merkle)",
    "revon-h": "Revon-H",
    "revon-log": "Revon-log calibration",
    "dolt": "Dolt",
}

def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _numeric(value: str) -> float | None:
    return None if value == "" else float(value)


def expected_hybrid_strategy(operation_count: int, threshold: int) -> str:
    return "log" if operation_count <= threshold else "merkle"


def tukey_outliers(values: Iterable[float]) -> tuple[float, float, list[int]]:
    sequence = list(values)
    if len(sequence) < 4:
        return -math.inf, math.inf, []
    p25 = _percentile(sequence, 0.25)
    p75 = _percentile(sequence, 0.75)
    iqr = p75 - p25
    lower = p25 - 1.5 * iqr
    upper = p75 + 1.5 * iqr
    return lower, upper, [
        index for index, value in enumerate(sequence) if value < lower or value > upper
    ]


def _expected_workloads(manifest: dict[str, Any]) -> dict[tuple[str, str], Any]:
    profile = manifest["profile"]
    seed = int(manifest["base_seed"])
    expected: dict[tuple[str, str], Any] = {}
    for spec in profile_specs(profile, seed, phase="calibration"):
        expected[("calibration", spec.name)] = build_workload(spec)
    for spec in profile_specs(profile, seed + 10_000, phase="evaluation"):
        expected[("evaluation", spec.name)] = build_workload(spec)
    return expected


def _expected_record_keys(manifest: dict[str, Any]) -> set[tuple[str, str, str, str, int]]:
    profile = manifest["profile"]
    seed = int(manifest["base_seed"])
    warmups = int(manifest["warmups"])
    trials = int(manifest["measured_trials"])
    expected: set[tuple[str, str, str, str, int]] = set()
    for spec in profile_specs(profile, seed, phase="calibration"):
        for model in ("revon-log", "revon-m"):
            for kind, count in (("warmup", warmups), ("measured", trials)):
                for trial in range(1, count + 1):
                    expected.add(("calibration", spec.name, DISPLAY_MODELS[model], kind, trial))
    for spec in profile_specs(profile, seed + 10_000, phase="evaluation"):
        for model in manifest["models"]:
            for kind, count in (("warmup", warmups), ("measured", trials)):
                for trial in range(1, count + 1):
                    expected.add(("evaluation", spec.name, DISPLAY_MODELS[model], kind, trial))
    return expected


def _check_summary(
    raw: list[dict[str, str]], summary: list[dict[str, str]], issues: list[str]
) -> None:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in raw:
        if row["trial_kind"] == "measured" and row["status"] == "ok":
            groups[(row["phase"], row["scenario"], row["model"])].append(row)
    summary_map = {(row["phase"], row["scenario"], row["model"]): row for row in summary}
    if set(groups) != set(summary_map):
        issues.append("summary group keys do not exactly match measured successful raw groups")
        return
    for key, group in groups.items():
        row = summary_map[key]
        if int(row["trials"]) != len(group):
            issues.append(f"{key}: summary trial count does not match raw rows")
        expected_correct = str(all(item["correctness"] == "True" for item in group))
        if row["all_correct"] != expected_correct:
            issues.append(f"{key}: summary correctness does not match raw rows")
        expected_strategies = ";".join(sorted({item["strategy_selected"] for item in group}))
        if row["strategy_selected"] != expected_strategies:
            issues.append(f"{key}: summary strategy selection does not match raw rows")
        expected_units = ";".join(sorted({item["work_unit"] for item in group}))
        if row["work_unit"] != expected_units:
            issues.append(f"{key}: summary work unit does not match raw rows")
        for metric in METRICS:
            values = [value for item in group if (value := _numeric(item[metric])) is not None]
            expected_values = {
                "median": statistics.median(values) if values else None,
                "p25": _percentile(values, 0.25) if values else None,
                "p75": _percentile(values, 0.75) if values else None,
            }
            for suffix, expected in expected_values.items():
                actual = _numeric(row[f"{metric}_{suffix}"])
                if expected is None and actual is None:
                    continue
                if expected is None or actual is None or not math.isclose(
                    actual, expected, rel_tol=1e-12, abs_tol=1e-9
                ):
                    issues.append(f"{key}: {metric}_{suffix} disagrees with raw rows")


def _outlier_rows(raw: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in raw:
        if row["trial_kind"] == "measured" and row["status"] == "ok":
            groups[(row["phase"], row["scenario"], row["model"])].append(row)
    candidates: list[dict[str, Any]] = []
    for (phase, scenario, model), group in sorted(groups.items()):
        for metric in METRICS:
            pairs = [(row, _numeric(row[metric])) for row in group]
            pairs = [(row, value) for row, value in pairs if value is not None]
            values = [value for _, value in pairs]
            if len(values) < 4:
                continue
            p25 = _percentile(values, 0.25)
            median = statistics.median(values)
            p75 = _percentile(values, 0.75)
            lower, upper, indices = tukey_outliers(values)
            for index in indices:
                source, value = pairs[index]
                candidates.append(
                    {
                        "phase": phase,
                        "scenario": scenario,
                        "model": model,
                        "trial": int(source["trial"]),
                        "metric": metric,
                        "value": value,
                        "median": median,
                        "p25": p25,
                        "p75": p75,
                        "lower_fence": lower,
                        "upper_fence": upper,
                        "ratio_to_median": value / median if median else "",
                        "classification": (
                            "timing variability candidate; retained in summary"
                            if metric.endswith("_ms")
                            else "non-timing variability candidate; retained and reviewed"
                        ),
                    }
                )
    return candidates


def audit(directory: Path) -> dict[str, Any]:
    raw_path = directory / "raw_results.csv"
    summary_path = directory / "summary.csv"
    manifest_path = directory / "manifest.json"
    for path in (raw_path, summary_path, manifest_path):
        if not path.is_file():
            raise FileNotFoundError(path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw = _read_csv(raw_path)
    summary = _read_csv(summary_path)
    issues: list[str] = []

    if manifest.get("schema_version") != 1:
        issues.append("unsupported manifest schema version")
    if manifest.get("profile") not in {"smoke", "paper"}:
        issues.append("manifest profile is invalid")
    if tuple(manifest.get("models", ())) != MODEL_KEYS:
        issues.append("manifest model order differs from the benchmark contract")
    if not raw:
        issues.append("raw CSV is empty")

    expected_keys = _expected_record_keys(manifest)
    actual_keys = [
        (
            row["phase"],
            row["scenario"],
            row["model"],
            row["trial_kind"],
            int(row["trial"]),
        )
        for row in raw
    ]
    duplicate_keys = [key for key, count in Counter(actual_keys).items() if count != 1]
    if duplicate_keys:
        issues.append(f"raw CSV contains {len(duplicate_keys)} duplicate trial identities")
    if set(actual_keys) != expected_keys:
        issues.append("raw CSV trial matrix is incomplete or contains unexpected rows")

    if {row["run_id"] for row in raw} != {manifest["run_id"]}:
        issues.append("raw run IDs do not agree with the manifest")
    if {row["python_version"] for row in raw} != {manifest["python_version"]}:
        issues.append("raw Python versions do not agree with the manifest")
    if {row["platform"] for row in raw} != {manifest["platform"]}:
        issues.append("raw platform values do not agree with the manifest")

    status_counts = Counter(row["status"] for row in raw)
    if set(status_counts) != {"ok"}:
        issues.append(f"non-success trial statuses present: {dict(status_counts)}")
    incorrect = [row for row in raw if row["status"] == "ok" and row["correctness"] != "True"]
    if incorrect:
        issues.append(f"{len(incorrect)} successful rows failed the correctness oracle")

    workloads = _expected_workloads(manifest)
    for row in raw:
        workload = workloads.get((row["phase"], row["scenario"]))
        if workload is None:
            issues.append(f"unknown scenario in raw CSV: {(row['phase'], row['scenario'])}")
            continue
        spec = workload.spec
        expected_fields = {
            "seed": spec.seed,
            "rows": spec.rows,
            "commits": spec.commits,
            "changes_per_commit": spec.changes_per_commit,
            "locality": spec.locality,
            "payload_bytes": spec.payload_bytes,
            "workload_sha256": workload.digest,
            "changed_keys": len(workload.expected_diff_keys),
        }
        for field, expected in expected_fields.items():
            actual: Any = row[field]
            if isinstance(expected, int):
                actual = int(actual)
            if actual != expected:
                issues.append(f"{row['scenario']} / {row['model']}: {field} disagrees with regenerated workload")
                break

    threshold = int(manifest["hybrid_threshold_operations"])
    for row in raw:
        if row["status"] != "ok":
            continue
        expected_strategy = {
            "Snapshot": "full-scan",
            "Log-only": "operation-log",
            "Revon-M (forced Merkle)": "merkle",
            "Revon-log calibration": "log",
            "Dolt": "dolt-native",
        }.get(row["model"])
        if row["model"] == "Revon-H":
            operations = int(row["commits"]) * int(row["changes_per_commit"])
            expected_strategy = expected_hybrid_strategy(operations, threshold)
        if row["strategy_selected"] != expected_strategy:
            issues.append(
                f"{row['phase']} / {row['scenario']} / {row['model']} trial {row['trial']}: "
                f"selected {row['strategy_selected']!r}, expected {expected_strategy!r}"
            )

    dolt_rows = [row for row in raw if row["model"] == "Dolt"]
    dolt_versions = sorted({row["dolt_version"] for row in dolt_rows if row["dolt_version"]})
    if manifest["dolt_available"] is not True:
        issues.append("manifest does not record Dolt as available")
    if len(dolt_versions) != 1:
        issues.append("Dolt version is missing or inconsistent across trials")

    for row in raw:
        if row["status"] != "ok":
            continue
        required_metrics = [
            "initial_import_ms",
            "incremental_commit_ms",
            "diff_ms",
            "checkout_ms",
            "storage_bytes",
            "changed_keys",
        ]
        if row["model"] != "Dolt":
            required_metrics.extend(("peak_memory_bytes", "work_examined"))
        missing = [metric for metric in required_metrics if row[metric] == ""]
        if missing:
            issues.append(f"{row['scenario']} / {row['model']} trial {row['trial']}: missing {missing}")

    _check_summary(raw, summary, issues)
    outliers = _outlier_rows(raw)
    outlier_path = directory / "outlier_review.csv"
    outlier_columns = [
        "phase",
        "scenario",
        "model",
        "trial",
        "metric",
        "value",
        "median",
        "p25",
        "p75",
        "lower_fence",
        "upper_fence",
        "ratio_to_median",
        "classification",
    ]
    with outlier_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=outlier_columns)
        writer.writeheader()
        writer.writerows(outliers)

    report = {
        "passed": not issues,
        "directory": str(directory),
        "run_id": manifest["run_id"],
        "profile": manifest["profile"],
        "raw_rows": len(raw),
        "summary_rows": len(summary),
        "status_counts": dict(status_counts),
        "correct_rows": sum(row["correctness"] == "True" for row in raw),
        "dolt_versions": dolt_versions,
        "hybrid_threshold_operations": threshold,
        "revon_h_evaluation_strategies": {
            scenario: sorted(
                {
                    row["strategy_selected"]
                    for row in raw
                    if row["phase"] == "evaluation"
                    and row["model"] == "Revon-H"
                    and row["scenario"] == scenario
                }
            )
            for scenario in sorted(
                {row["scenario"] for row in raw if row["phase"] == "evaluation"}
            )
        },
        "outlier_method": "Tukey 1.5*IQR fences within each measured scenario/model/metric group",
        "outlier_candidates": len(outliers),
        "outlier_rows_retained": True,
        "issues": issues,
    }
    (directory / "evidence_audit.json").write_text(
        json.dumps(report, indent=2, sort_keys=True), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    report = audit(args.directory)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
