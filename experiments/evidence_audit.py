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
from .workloads import WorkloadSpec, build_workload, profile_specs


METRICS = (
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
    "work_examined",
)

EXTRA_TELEMETRY_METRICS = (
    "process_tree_cpu_seconds",
    "process_tree_read_bytes",
    "process_tree_write_bytes",
    "commit_operations_per_second",
)

DISPLAY_MODELS = {
    "snapshot": "Snapshot",
    "log": "Log-only",
    "revon-m": "Revon-M (forced Merkle)",
    "revon-h": "Revon-H",
    "revon-log": "Revon-log calibration",
    "dolt": "Dolt",
    "dolt-bulk": "Dolt (bulk import)",
}

LEGACY_MODEL_KEYS = ("snapshot", "log", "revon-m", "revon-h", "dolt")


def _manifest_specs(manifest: dict[str, Any], seed: int, phase: str) -> list[WorkloadSpec]:
    specs = profile_specs(manifest["profile"], seed, phase=phase)
    # Schema versions 1-3 used the label large-hot for the same application-key
    # locality later renamed in schema 4. Preserve those runs' recorded identity.
    if int(manifest.get("schema_version", 1)) < 4 and phase == "evaluation":
        legacy_scenarios = {
            "small-sparse",
            "medium-sparse",
            "medium-dense",
            "large-sparse",
            "large-hot",
            "large-application-key-local",
        }
        specs = [
            WorkloadSpec(
                name="large-hot",
                rows=spec.rows,
                commits=spec.commits,
                changes_per_commit=spec.changes_per_commit,
                seed=spec.seed,
                payload_bytes=spec.payload_bytes,
                locality="hot",
            )
            if spec.name == "large-application-key-local"
            else spec
            for spec in specs
            if spec.name in legacy_scenarios
        ]
    return specs

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
    seed = int(manifest["base_seed"])
    expected: dict[tuple[str, str], Any] = {}
    for spec in _manifest_specs(manifest, seed, phase="calibration"):
        expected[("calibration", spec.name)] = build_workload(spec)
    for spec in _manifest_specs(manifest, seed + 10_000, phase="evaluation"):
        expected[("evaluation", spec.name)] = build_workload(spec)
    return expected


def _expected_record_keys(manifest: dict[str, Any]) -> set[tuple[str, str, str, str, int]]:
    seed = int(manifest["base_seed"])
    warmups = int(manifest["warmups"])
    trials = int(manifest["measured_trials"])
    expected: set[tuple[str, str, str, str, int]] = set()
    for spec in _manifest_specs(manifest, seed, phase="calibration"):
        for model in ("revon-log", "revon-m"):
            for kind, count in (("warmup", warmups), ("measured", trials)):
                for trial in range(1, count + 1):
                    expected.add(("calibration", spec.name, DISPLAY_MODELS[model], kind, trial))
    for spec in _manifest_specs(manifest, seed + 10_000, phase="evaluation"):
        for model in manifest["models"]:
            for kind, count in (("warmup", warmups), ("measured", trials)):
                for trial in range(1, count + 1):
                    expected.add(("evaluation", spec.name, DISPLAY_MODELS[model], kind, trial))
    return expected


def _check_summary(
    raw: list[dict[str, str]],
    summary: list[dict[str, str]],
    issues: list[str],
    metrics: tuple[str, ...],
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
        for metric in metrics:
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


def _outlier_rows(raw: list[dict[str, str]], metrics: tuple[str, ...]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in raw:
        if row["trial_kind"] == "measured" and row["status"] == "ok":
            groups[(row["phase"], row["scenario"], row["model"])].append(row)
    candidates: list[dict[str, Any]] = []
    for (phase, scenario, model), group in sorted(groups.items()):
        for metric in metrics:
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

    schema_version = manifest.get("schema_version")
    if schema_version not in (1, 2, 3, 4, 5):
        issues.append("unsupported manifest schema version")
    if manifest.get("profile") not in {"smoke", "paper"}:
        issues.append("manifest profile is invalid")
    expected_models = MODEL_KEYS if int(schema_version or 0) >= 4 else LEGACY_MODEL_KEYS
    if tuple(manifest.get("models", ())) != expected_models:
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

    if schema_version >= 4:
        order_groups: dict[tuple[str, str, str, int], list[int]] = defaultdict(list)
        for row in raw:
            order_groups[
                (row["phase"], row["scenario"], row["trial_kind"], int(row["trial"]))
            ].append(int(row.get("execution_order", "0")))
        for block, orders in order_groups.items():
            if sorted(orders) != list(range(1, len(orders) + 1)):
                issues.append(f"{block}: execution_order is not a unique contiguous block order")

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
        }
        if schema_version >= 4:
            expected_fields["logical_payload_bytes"] = sum(
                len(key.encode("utf-8")) + len(value.encode("utf-8"))
                for key, value in workload.states[-1].items()
            )
        # Version 1 copied the oracle count into Dolt rows. It cannot be
        # checked as an observation, even when its number is correct.
        if row["model"] != "Dolt" or schema_version >= 2:
            expected_fields["changed_keys"] = len(workload.expected_diff_keys)
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
            "Dolt (bulk import)": "dolt-native",
        }.get(row["model"])
        if row["model"] == "Revon-H":
            operations = int(row["commits"]) * int(row["changes_per_commit"])
            expected_strategy = expected_hybrid_strategy(operations, threshold)
        if row["strategy_selected"] != expected_strategy:
            issues.append(
                f"{row['phase']} / {row['scenario']} / {row['model']} trial {row['trial']}: "
                f"selected {row['strategy_selected']!r}, expected {expected_strategy!r}"
            )

    dolt_rows = [row for row in raw if row["model"].startswith("Dolt")]
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
        if schema_version >= 3:
            required_metrics.append("process_tree_peak_rss_bytes")
            if not row["model"].startswith("Dolt"):
                required_metrics.append("work_examined")
        if schema_version >= 4:
            required_metrics.append("execution_order")
        elif schema_version < 3 and row["model"] != "Dolt":
            required_metrics.extend(("peak_memory_bytes", "work_examined"))
        if schema_version >= 5:
            required_metrics.extend(("process_tree_cpu_seconds", "commit_operations_per_second"))
        missing = [metric for metric in required_metrics if row[metric] == ""]
        if missing:
            issues.append(f"{row['scenario']} / {row['model']} trial {row['trial']}: missing {missing}")
        if schema_version >= 4:
            storage = _numeric(row["storage_bytes"])
            payload = _numeric(row["logical_payload_bytes"])
            ratio = _numeric(row["storage_bytes_per_logical_payload_byte"])
            if storage is None or payload is None or ratio is None or not math.isclose(
                ratio, storage / payload, rel_tol=1e-12, abs_tol=1e-12
            ):
                issues.append(f"{row['scenario']} / {row['model']}: storage normalization is invalid")
            residual = _numeric(row["storage_bytes_minus_logical_payload_bytes"])
            if storage is None or payload is None or residual != storage - payload:
                issues.append(f"{row['scenario']} / {row['model']}: storage residual is invalid")
            compact_applicable = row["model"] in {
                "Revon-M (forced Merkle)", "Revon-H", "Dolt", "Dolt (bulk import)"
            }
            compaction_sample = (
                row["phase"] == "evaluation"
                and row["trial_kind"] == "measured"
                and int(row["trial"]) == 1
                and compact_applicable
            )
            if compaction_sample and (
                row["storage_bytes_after_compaction"] == ""
                or row["compaction_ms"] == ""
                or row["compaction_method"] in ("", "not sampled", "not applicable")
            ):
                issues.append(f"{row['scenario']} / {row['model']}: compaction measurement is missing")
            if not compaction_sample:
                expected_compaction_label = "not sampled" if compact_applicable else "not applicable"
                if (
                    row["storage_bytes_after_compaction"] != ""
                    or row["compaction_ms"] != ""
                    or row["compaction_method"] != expected_compaction_label
                ):
                    issues.append(f"{row['scenario']} / {row['model']}: compaction applicability label is wrong")
        if schema_version >= 5:
            for metric in EXTRA_TELEMETRY_METRICS:
                value = _numeric(row[metric])
                if value is not None and value < 0:
                    issues.append(f"{row['scenario']} / {row['model']}: {metric} is negative")
            throughput = _numeric(row["commit_operations_per_second"])
            if throughput is None or throughput <= 0:
                issues.append(f"{row['scenario']} / {row['model']}: commit throughput is missing or invalid")

    metrics = (
        "initial_import_ms",
        "incremental_commit_ms",
        "diff_ms",
        "checkout_ms",
        "storage_bytes",
        "process_tree_peak_rss_bytes" if schema_version >= 3 else "peak_memory_bytes",
        "work_examined",
    ) + (
        (
            "logical_payload_bytes",
            "storage_bytes_per_logical_payload_byte",
            "storage_bytes_minus_logical_payload_bytes",
            "storage_bytes_after_compaction",
            "compaction_ms",
        )
        if schema_version >= 4
        else ()
    ) + (EXTRA_TELEMETRY_METRICS if schema_version >= 5 else ())
    _check_summary(raw, summary, issues, metrics)
    outliers = _outlier_rows(raw, metrics)
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
        "recorded_correctness_true_rows": sum(row["correctness"] == "True" for row in raw),
        "execution_counts": {
            "warmups": sum(row["trial_kind"] == "warmup" for row in raw),
            "measured": sum(row["trial_kind"] == "measured" for row in raw),
            "primary_evaluation_measured": sum(
                row["phase"] == "evaluation" and row["trial_kind"] == "measured"
                and row["model"] != "Dolt (bulk import)"
                for row in raw
            ),
            "dolt_evaluation_measured": sum(
                row["phase"] == "evaluation" and row["trial_kind"] == "measured"
                and row["model"] == "Dolt" for row in raw
            ),
            "dolt_bulk_evaluation_measured": sum(
                row["phase"] == "evaluation" and row["trial_kind"] == "measured"
                and row["model"] == "Dolt (bulk import)" for row in raw
            ),
        },
        "dolt_diff_semantically_validated_by_harness": schema_version >= 2,
        "legacy_dolt_diff_unverified_rows": sum(
            row["model"] == "Dolt" for row in raw
        ) if schema_version == 1 else 0,
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
