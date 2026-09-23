"""Audit and summarize cross-seed ratios from a robustness-study bundle."""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path


def cluster_bootstrap_interval(
    ratios_by_seed: dict[int, list[float]], *, seed: int, draws: int = 20_000
) -> tuple[float, float, float]:
    if len(ratios_by_seed) < 2 or any(not values for values in ratios_by_seed.values()):
        raise ValueError("at least two non-empty seed clusters are required")
    observed = [ratio for values in ratios_by_seed.values() for ratio in values]
    rng = random.Random(seed)
    seed_ids = sorted(ratios_by_seed)
    boot_medians = []
    for _ in range(draws):
        sampled_seeds = rng.choices(seed_ids, k=len(seed_ids))
        sample = []
        for sampled_seed in sampled_seeds:
            cluster = ratios_by_seed[sampled_seed]
            sample.extend(rng.choices(cluster, k=len(cluster)))
        boot_medians.append(statistics.median(sample))
    boot_medians.sort()
    q = lambda p: boot_medians[round((draws - 1) * p)]
    return statistics.median(observed), q(0.025), q(0.975)


def analyze(directory: Path, *, draws: int = 20_000) -> list[dict[str, str]]:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    audit = json.loads((directory / "audit.json").read_text(encoding="utf-8"))
    if not audit.get("passed"):
        raise ValueError("robustness bundle must pass audit before analysis")
    with (directory / "raw_results.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    factor_by_scenario = {
        item["name"]: item["name"].split("-", 2)[-1]
        for item in manifest["workloads"]
    }
    groups: dict[tuple[str, str, int, int], dict[str, float]] = defaultdict(dict)
    for row in rows:
        if row["trial_kind"] != "measured" or row["status"] != "ok":
            continue
        if row["model"] not in {"Revon-M (forced Merkle)", "Revon-H"}:
            continue
        key = (factor_by_scenario[row["scenario"]], row["metric"] if "metric" in row else "diff_ms", int(row["seed"]), int(row["trial"]))
        groups[key][row["model"]] = float(row["diff_ms"])

    ratios: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for (factor, _metric, seed, trial), values in groups.items():
        if set(values) == {"Revon-M (forced Merkle)", "Revon-H"}:
            ratios[factor][seed].append(values["Revon-M (forced Merkle)"] / values["Revon-H"])
    output: list[dict[str, str]] = []
    for factor, by_seed in sorted(ratios.items()):
        median, low, high = cluster_bootstrap_interval(
            by_seed,
            seed=20260923 + sum(map(ord, factor)),
            draws=draws,
        )
        output.append({
            "workload_factor": factor,
            "seeds": str(len(by_seed)),
            "paired_trials": str(sum(map(len, by_seed.values()))),
            "median_paired_ratio_rev_m_over_rev_h": f"{median:.6g}",
            "ci95_low": f"{low:.6g}",
            "ci95_high": f"{high:.6g}",
            "interpretation": (
                "inconclusive across sampled seeds"
                if low <= 1 <= high
                else "Revon-M slower" if median > 1 else "Revon-H slower"
            ),
            "interval_method": f"hierarchical bootstrap by seed then paired trial; {draws} resamples",
            "scope": f"10,000-row synthetic flat key-value workloads on {manifest.get('platform', 'unknown platform')}",
        })
    out = directory / "factor_bootstrap.csv"
    with out.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--draws", type=int, default=20_000)
    args = parser.parse_args()
    result = analyze(args.evidence, draws=args.draws)
    print(json.dumps({"factors": len(result), "output": "factor_bootstrap.csv", "rows": result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
