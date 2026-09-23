# Final experimental harness

This harness produces the raw evidence for the final Revon evaluation. The
primary comparison is Snapshot vs Log-only vs Revon-H vs Dolt. The forced
Merkle variant is reported as **Revon-M (forced Merkle)** and is an ablation,
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
  calibrated Revon-H threshold.

Timestamped working CSV files are intentionally ignored by Git. The reviewed,
anonymized paper and trie-sensitivity bundles are versioned under `evidence/`
so the published metrics can be audited from a fresh clone.

## Variants

| Label | Durable representation | Diff path |
| --- | --- | --- |
| Snapshot | Canonical full-state JSON per version | Full key scan |
| Log-only | Canonical base JSON plus fsynced JSONL changesets | Log replay/aggregation |
| Revon-M | SQLite-backed fixed-depth Merkle hash trie | Forced hash-pruned tree diff |
| Revon-H | Same trie plus changesets | Calibrated adaptive log/Merkle choice |
| Dolt | Native Dolt repository and table | Batched SQL `INSERT`; native `dolt diff` |
| Dolt (bulk import) | Same Dolt repository and table | CSV input via `dolt table import -r`; same later operations |

Revon-M exists only to answer the ablation question: does adaptive selection
improve the Merkle-only design? The paper's main system is Revon-H.

## Reproducibility protocol

- Calibration and evaluation workloads are disjoint. Calibration sweeps
  operation counts and selects the largest tested count for which median log
  diff is no slower than median Merkle diff.
- A scenario is generated once from a fixed seed. Its initial state, mixed
  update/delete/insert batches, expected versions, and SHA-256 workload digest
  are reused unchanged by every adapter and every repetition.
- Warmups are recorded but excluded from summaries. Measured trials use fresh
  repositories and report medians with interquartile ranges.
- The current paper profile has 540 executions: 120 warm-ups and 420 measured
  runs. Calibration contributes 84 measured runs; eight evaluation scenarios
  contribute 280 primary five-system runs, 56 SQL-path Dolt runs, and 56
  additional Dolt bulk-import runs.
- Within a scenario and trial kind, the model order is seeded and shuffled once,
  then rotated by trial. The six evaluation variants occupy every position once
  in the first six measured trials. `execution_order` is stored in raw results
  and checked by the evidence audit.
- Evaluation includes spread workloads plus application-key-local, range-local,
  repeated-key, and hash-route-local updates. The former `large-hot` workload
  was lexical adjacency and is now labeled `large-application-key-local`.
- Repository setup is excluded. Initial import includes the first durable
  state/version. Incremental commit is the median durable commit in a trial.
  Diff and checkout consume their complete results.
- Correctness requires exact initial and final checkout equality and exact
  changed-key equality for every adapter. Dolt's JSON diff is parsed into
  observed keys and old/new values, which must match the workload oracle.
  `changed_keys` is the length of the observed diff, never the oracle count.
- Storage reports total fresh repository-directory size, bytes per final UTF-8
  key/value payload byte, and their residual. The residual includes encoding,
  indexes, metadata, and compression; it is not pure metadata overhead. A
  representative trial per scenario is also measured after `dolt gc` or SQLite
  `VACUUM`, outside operation timing and RSS sampling.
  Work examined uses natural units (keys, log operations, or trie-node pairs).
  Dolt's CLI does not expose a directly comparable internal counter, so that
  cell is blank rather than estimated.

## Dolt adapter

Install Dolt and make `dolt` available on `PATH` before the final run. The
adapter records `dolt version`, creates a fresh repository, uses a keyed SQL
table, commits every version, performs historical `AS OF` checkout, and times
native `dolt diff -r json`, including JSON parsing. Both Dolt import variants
run the same later-operation protocol. The SQL path uses batched `INSERT`; the
bulk path writes CSV and times CSV serialization, `dolt table import -r`, and
the initial commit as one workflow. The import timings are reported separately.
If Dolt is absent,
its rows are marked `unavailable`
and all result cells remain blank.

Schema-version-2 runs use this structured Dolt diff protocol. The older
`paper-final-20260824` bundle used tabular output, did not parse Dolt's diff,
and copied its expected changed-key count into the Dolt rows. Its timings
are historical workflow measurements; its Dolt diff correctness and changed-key
field must not be cited as observed results.

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

Every paper-profile model now runs in an isolated worker process. The parent
uses one external `psutil` sampler to record process-tree RSS for Python and
Dolt during each trial, including Dolt child processes. This is workflow-level
peak RSS sampled every 10 ms, not allocation volume; peaks shorter than the
sampling interval may be missed. The
sampler runs outside the worker's timed operations, though it can still create
small system-level scheduling pressure.

Timed operations do not use `tracemalloc`. The external sampler provides a
common RSS measurement method; it does not make short-process timings immune to
OS scheduling or background load.

Schema-5 runs also record external process-tree CPU seconds and read/write
bytes when the platform exposes those counters. On Windows the sampler uses
`psutil`; on Linux it can read `/proc`. These totals cover worker setup and
correctness validation as well as timed operations, so they are not per-
operation resource measurements. Serial commit-operation throughput is the
number of commits divided by the sum of their measured intervals; it is not
concurrent throughput. Missing I/O counters mean unavailable, not zero.

Diff timing includes materializing sorted changed keys plus old/new SHA-256
value hashes into canonical JSON for every system. Checkout timing includes
materializing the complete sorted key/value state into canonical UTF-8 JSON
for every system. Dolt's CLI output is parsed and normalized inside its timed
region. The comparison remains an in-process Revon API versus a Dolt CLI
workflow comparison; the common output contract does not remove process-startup
or SQL-layer costs.

Dolt commit timing includes SQL mutation, `dolt add`, and commit. It no longer
creates per-version tags in the timed path; commit hashes returned by commit
are retained for historical checkout.

## Interpretation rules

Do not claim that Revon is “faster than Dolt” from one workload or from the
smoke profile. Report the dataset size, mutation density, history distance,
locality, payload size, machine, versions, warmups, trial count, distribution,
paired ratio interval, and Dolt version. Discuss where Revon-H wins, ties, or
loses. A ratio interval from repeated trials on one fixed workload does not
capture variation across datasets or machines. Dolt is a mature
SQL database; Revon is a Python research prototype testing whether adaptive
log/Merkle differencing and fixed-depth copy-on-write indexing are useful.

## Paired ratio uncertainty and robustness

For the issues 13–17 primary bundle, calculate same-trial ratio intervals with:

```powershell
python -m experiments.paired_uncertainty evidence/paper-corrected-issues13-17-counterbalanced-final-20260923
```

The separate seed/payload/history/locality sensitivity runner is:

```powershell
python -m experiments.robustness_study --output-dir evidence/paper-issues18-20-robustness-20260923 --warmups 2 --trials 7
python -m experiments.robustness_study --output-dir evidence/paper-issues18-20-robustness-20260923 --audit
python -m experiments.robustness_summary evidence/paper-issues18-20-robustness-20260923
```

The Windows run has three seeds and five 10,000-row variants. The Linux
replication recorded in `evidence/paper-issues18-20-linux-wsl-20260923/` ran
under WSL2 on the same physical host, with one warm-up and three measured
trials per model and variant. Neither bundle includes public multi-table data
or one-million-row workloads. Neither is evidence about concurrent operations
or ordered range scans.

## Audit a completed evidence bundle

The internal evidence-integrity audit regenerates workloads from the manifest, verifies the exact trial
matrix, recomputes every summary statistic, checks Revon-H strategy
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
not be mixed into the primary Snapshot/Log-only/Revon-H/Dolt result table.
