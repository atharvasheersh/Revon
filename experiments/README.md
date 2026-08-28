# Final experimental harness

This harness produces the raw evidence for the final Chronos evaluation. The
primary comparison is Snapshot vs Log-only vs Chronos-H vs Dolt. The forced
Merkle variant is reported as **Chronos-M (forced Merkle)** and is an ablation,
not a separate product claim.

## Run it

Quick correctness and pipeline check:

```powershell
python -m experiments.final_benchmark --profile smoke --warmups 1 --trials 3
```

Final paper run (prefer an idle machine on AC power):

```powershell
python -m experiments.final_benchmark --profile paper --warmups 2 --trials 7
```

Every run creates an ignored timestamped directory under
`output/benchmarks/` containing:

- `raw_results.csv`: one row per warmup or measured trial;
- `summary.csv`: measured-trial median, 25th percentile, and 75th percentile;
- `manifest.json`: environment, seed, model list, metric definitions, and the
  calibrated Chronos-H threshold.

Timestamped working CSV files are intentionally ignored by Git. The reviewed,
anonymized paper and trie-sensitivity bundles are versioned under `evidence/`
so the published metrics can be audited from a fresh clone.

## Variants

| Label | Durable representation | Diff path |
| --- | --- | --- |
| Snapshot | Canonical full-state JSON per version | Full key scan |
| Log-only | Canonical base JSON plus fsynced JSONL changesets | Log replay/aggregation |
| Chronos-M | SQLite-backed fixed-depth Merkle hash trie | Forced hash-pruned tree diff |
| Chronos-H | Same trie plus changesets | Calibrated adaptive log/Merkle choice |
| Dolt | Native Dolt repository and table | Native `dolt diff` |

Chronos-M exists only to answer the ablation question: does adaptive selection
improve the Merkle-only design? The paper's main system is Chronos-H.

## Reproducibility protocol

- Calibration and evaluation workloads are disjoint. Calibration sweeps
  operation counts and selects the largest tested count for which median log
  diff is no slower than median Merkle diff.
- A scenario is generated once from a fixed seed. Its initial state, mixed
  update/delete/insert batches, expected versions, and SHA-256 workload digest
  are reused unchanged by every adapter and every repetition.
- Warmups are recorded but excluded from summaries. Measured trials use fresh
  repositories and report medians with interquartile ranges.
- Repository setup is excluded. Initial import includes the first durable
  state/version. Incremental commit is the median durable commit in a trial.
  Diff and checkout consume their complete results.
- Correctness requires exact initial and final checkout equality and exact
  changed-key equality where the adapter exposes structured keys. Dolt's
  native diff must succeed and its historical checkouts must match the same
  oracle.
- Storage is the total regular-file size in the fresh repository directory.
  Work examined uses natural units (keys, log operations, or trie-node pairs).
  Dolt's CLI does not expose a directly comparable internal counter, so that
  cell is blank rather than estimated.

## Dolt adapter

Install Dolt and make `dolt` available on `PATH` before the final run. The
adapter records `dolt version`, creates a fresh repository, uses a keyed SQL
table, commits/tags every version, performs historical `AS OF` checkout, and
times native `dolt diff`. If Dolt is absent, its rows are marked `unavailable`
and all result cells remain blank.

Dolt documents Windows installation and its Git-style commands in the
[official repository](https://github.com/dolthub/dolt). Its official import
benchmark documentation distinguishes `LOAD DATA INFILE`, `dolt table import`,
and SQL imports: [Dolt import benchmarks](https://docs.dolthub.com/sql-reference/benchmarks/import).
This adapter intentionally measures a repeatable CLI-facing workflow. Describe
it as such; it is not an isolated engine-only microbenchmark.

The exact commands and flags are grounded in Dolt's
[CLI reference](https://www.dolthub.com/docs/cli-reference/cli/), and historical
validation uses the documented
[`AS OF` query syntax](https://www.dolthub.com/docs/sql-reference/version-control/querying-history/).

The adapter can optionally use `psutil` to sample the Dolt process tree's RSS.
Without it, Dolt peak memory is blank. Python variants use `tracemalloc` and
the CSV records the measurement method. Do not put these two memory numbers on
one comparative chart until all variants are run under the same external RSS
monitor; retain them as diagnostic evidence meanwhile.

## Interpretation rules

Do not claim that Chronos is “faster than Dolt” from one workload or from the
smoke profile. Report the dataset size, mutation density, history distance,
locality, payload size, machine, versions, warmups, trial count, distribution,
and Dolt version. Discuss where Chronos-H wins, ties, or loses. Dolt is a mature
SQL database; Chronos is a Python research prototype testing whether adaptive
log/Merkle differencing and fixed-depth copy-on-write indexing are useful.

## Audit a completed evidence bundle

The audit regenerates workloads from the manifest, verifies the exact trial
matrix, recomputes every summary statistic, checks Chronos-H strategy
selection, confirms Dolt metadata, and writes a non-destructive Tukey outlier
review:

```powershell
python -m experiments.evidence_audit evidence/paper-final-20260824
```

It adds `evidence_audit.json` and `outlier_review.csv` beside the original
bundle. It never edits or removes rows from `raw_results.csv`.

## Fixed-trie parameter sensitivity

Run the separate forced-Merkle geometry study with:

```powershell
python -m experiments.trie_sensitivity --output-dir output/benchmarks/trie-sensitivity-20260824 --rows 10000 --commits 10 --changes-per-commit 100 --warmups 2 --trials 7 --seed 20260824
```

The predefined configurations are `b4-d6`, `b8-d3`, `b8-d4`, `b8-d5`, and
`b16-d3`. Three have exactly 4,096 theoretical leaf buckets so fanout/depth can
be compared at constant bucket count. This experiment is an ablation and must
not be mixed into the primary Snapshot/Log-only/Chronos-H/Dolt result table.
