"""Paired bootstrap intervals for within-trial benchmark latency ratios.

Ratios use matching scenario/trial observations and resample those paired
observations. They are exploratory intervals over repeated runs of the same
fixed workload, not population-level intervals over datasets or machines.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Iterable


COMPARISONS = (
    ("Dolt", "Revon-H", ("initial_import_ms", "incremental_commit_ms", "diff_ms", "checkout_ms")),
    ("Revon-M (forced Merkle)", "Revon-H", ("diff_ms",)),
    ("Dolt", "Dolt (bulk import)", ("initial_import_ms",)),
)
METRICS = tuple(sorted({metric for _, _, metrics in COMPARISONS for metric in metrics}))


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    location = (len(ordered) - 1) * fraction
    lo = int(location)
    hi = min(lo + 1, len(ordered) - 1)
    weight = location - lo
    return ordered[lo] * (1 - weight) + ordered[hi] * weight


def paired_median_ratio_interval(
    ratios: Iterable[float], *, seed: int = 20260923, draws: int = 20_000
) -> tuple[float, float, float]:
    values = list(ratios)
    if not values or any(value <= 0 for value in values):
        raise ValueError("paired latency ratios must be positive and non-empty")
    rng = random.Random(seed)
    boot = [
        statistics.median(rng.choices(values, k=len(values)))
        for _ in range(draws)
    ]
    return statistics.median(values), percentile(boot, 0.025), percentile(boot, 0.975)


def classify(median: float, low: float, high: float, practical_margin: float = 0.05) -> str:
    """For latency ratios numerator/denominator, values above 1 favor denominator."""
    if low <= 1.0 <= high:
        return "inconclusive: interval includes parity"
    if median >= 1 + practical_margin and low > 1:
        return "denominator faster by a practically relevant margin"
    if median <= 1 - practical_margin and high < 1:
        return "numerator faster by a practically relevant margin"
    return "statistically separated but below the 5% practical margin"


def analyze(raw_path: Path, out_path: Path, *, draws: int = 20_000) -> list[dict[str, str]]:
    with raw_path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    paired: dict[tuple[str, str, str], dict[tuple[str, int], float]] = defaultdict(dict)
    for row in rows:
        if row["phase"] != "evaluation" or row["trial_kind"] != "measured" or row["status"] != "ok":
            continue
        for metric in METRICS:
            value = row.get(metric, "")
            if value:
                paired[(row["scenario"], row["model"], metric)][
                    (row["trial_kind"], int(row["trial"]))
                ] = float(value)

    output: list[dict[str, str]] = []
    for scenario in sorted({row["scenario"] for row in rows if row["phase"] == "evaluation"}):
        for numerator, denominator, metrics in COMPARISONS:
            for metric in metrics:
                left = paired.get((scenario, numerator, metric), {})
                right = paired.get((scenario, denominator, metric), {})
                keys = sorted(set(left) & set(right))
                ratios = [left[key] / right[key] for key in keys]
                if not ratios:
                    continue
                median, low, high = paired_median_ratio_interval(
                    ratios, seed=20260923 + sum(map(ord, scenario + metric + numerator)), draws=draws
                )
                output.append({
                    "scenario": scenario,
                    "numerator_model": numerator,
                    "denominator_model": denominator,
                    "metric": metric,
                    "paired_trials": str(len(ratios)),
                    "median_paired_ratio": f"{median:.6g}",
                    "ci95_low": f"{low:.6g}",
                    "ci95_high": f"{high:.6g}",
                    "interpretation": classify(median, low, high),
                    "ratio_direction": f"latency {numerator}/{denominator}; above 1 favors {denominator}",
                    "interval_method": f"paired percentile bootstrap of median trial ratio; {draws} resamples",
                })
    if not output:
        raise ValueError("no paired measured evaluation rows found")
    with out_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--draws", type=int, default=20_000)
    args = parser.parse_args()
    output = args.evidence / "paired_ratio_uncertainty.csv"
    results = analyze(args.evidence / "raw_results.csv", output, draws=args.draws)
    summary = {
        "interval_unit": "paired repeated-trial ratios within each fixed scenario",
        "generalization": "does not cover workload-population or cross-machine uncertainty",
        "paired_rows": len(results),
        "inconclusive_rows": sum("inconclusive" in row["interpretation"] for row in results),
        "bootstrap_resamples": args.draws,
        "file": output.name,
    }
    (args.evidence / "paired_ratio_uncertainty.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
