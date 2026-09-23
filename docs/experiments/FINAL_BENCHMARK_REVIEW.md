# Final benchmark evidence review

> Historical review of the August 2026 bundle. The current audited paper-profile
> results are in `evidence/paper-corrected-issues13-17-counterbalanced-final-20260923/`;
> use `docs/experiments/ISSUES_13_TO_17_CORRECTION.md` for the current metric
> definitions and `docs/paper/FINAL_RESEARCH_PAPER.md` for the current claims.

Date: 2026-08-24

Evidence bundle: `evidence/paper-final-20260824/`

## Historical verdict and correction

The original paper-profile bundle passes an internal arithmetic and trial-matrix
audit. All 333 executions succeeded, but 74 were warm-ups. Of the 259 measured
executions, 175 were in the primary five-system evaluation, including 35 Dolt
executions. The 37 summary groups reproduce measured trial values. This audit
does **not** establish semantic correctness of Dolt's diff: the adapter did not
parse its output, and the Dolt `changed_keys` field was copied from the oracle.
Those original CSV fields are retained as historical records and must not be
cited as observed Dolt results. A schema-version-2 rerun supersedes this bundle
for manuscript claims.

The machine-readable audit outputs are:

- `evidence_audit.json`
- `outlier_review.csv`

Run the audit again with:

```powershell
python -m experiments.evidence_audit evidence/paper-final-20260824
```

## Checklist

| Check | Result | Evidence |
| --- | --- | --- |
| Historical state checks | Limited | `333/333` raw rows recorded `correctness=True`, but the 45 Dolt flags cover successful diff commands and historical checkout states, not diff contents. |
| Dolt version is recorded | Pass | Every Dolt row records `dolt version 2.3.1`. |
| No unavailable or failed trials | Pass | Status distribution is exactly `ok: 333`. |
| Raw CSV, summary CSV, and manifest agree | Pass | The internal audit recomputes the trial matrix, metadata, and summary medians and quartiles. It does not reproduce timings or inspect Dolt diff output. |
| Revon-H selection behaves correctly | Pass | The selector follows the inclusive 4,096-operation threshold in every raw row. |
| Outliers investigated, not deleted | Pass | All candidates remain in `raw_results.csv` and therefore in the seven-trial medians and quartiles. |

## Bundle reconciliation

- Profile: `paper`
- Run ID: `7048cc1674dc4038a8e42c87818b9088`
- Warmups: 2 per configuration
- Measured trials: 7 per configuration
- Raw executions: 333 = 74 warm-ups + 259 measured
- Primary evaluation: 175 measured = 5 scenarios x 5 systems x 7 trials
- Dolt primary evaluation: 35 measured = 5 scenarios x 7 trials
- Summary rows: 37
- Models: Snapshot, Log-only, Revon-M, Revon-H, and Dolt
- Calibration models: Revon log and forced Merkle
- Workload integrity: every scenario was regenerated from its manifest seed;
  workload SHA-256 values matched. The original Dolt changed-key counts were
  oracle values, not observations.
- Environment integrity: raw Python version and platform fields agree with the
  manifest.

Expected raw-row count:

```text
calibration: 6 scenarios x 2 models x (2 warmups + 7 measured) = 108
evaluation:  5 scenarios x 5 models x (2 warmups + 7 measured) = 225
total:                                                        = 333
```

## Revon-H strategy review

The calibrated threshold is 4,096 operations. Revon-H uses the log when the
number of operations on the ancestor path is at or below the threshold and
uses Merkle comparison above it.

| Evaluation scenario | Operations | Expected | Recorded |
| --- | ---: | --- | --- |
| small-sparse | 100 | log | log |
| medium-sparse | 100 | log | log |
| medium-dense | 10,000 | Merkle | Merkle |
| large-sparse | 1,000 | log | log |
| large-hot | 1,000 | log | log |

The selector is therefore implemented correctly for the evaluated scenarios.
However, 4,096 is the largest sampled calibration point. It is a valid frozen
policy boundary for this run, not proof that the true hardware-dependent
crossover occurs at exactly 4,096 operations.

## Outlier investigation

Candidate outliers were identified within each measured
scenario/model/metric group using Tukey 1.5 x IQR fences. With only seven
values per group and many very stable measurements, this rule is intentionally
sensitive. It flagged 83 individual metric values:

- 71 timing candidates;
- 12 storage-size candidates;
- no peak-memory or examined-work candidates.

The storage candidates were minor. Every value remained within 2.8% of its
group median, consistent with page allocation and repository-file variation.

Four timing values were at least twice their group median:

| Scenario / model / trial | Metric | Value | Median multiple | Investigation |
| --- | --- | ---: | ---: | --- |
| small-sparse / Revon-M / 7 | checkout | 4.417 ms | 3.20x | Diff was also elevated (1.98x), while correctness and node work were unchanged. |
| small-sparse / Dolt / 2 | diff | 493.972 ms | 2.62x | Import, commit, and checkout were also elevated, indicating a whole-trial CLI/runtime slowdown. |
| small-sparse / Log-only / 6 | checkout | 5.358 ms | 2.44x | Diff was simultaneously elevated; correctness and operation count were unchanged. |
| small-sparse / Log-only / 6 | diff | 2.472 ms | 2.09x | Same transient late-operation slowdown as the checkout value. |

These candidates affect the smallest and shortest operations, where scheduler,
filesystem, process-startup, and cache noise have the largest relative effect.
They do not coincide with altered workload hashes, changed work counts,
missing data, or failed trials. Dolt diff contents were not checked in this
bundle. The candidates were retained. The paper must
report medians and interquartile ranges rather than selecting faster trials.

## Interpretation boundary

This audit establishes evidence integrity, not that Revon wins every metric.
The paper should report where Revon-H wins, loses, or trades latency for
storage. Dolt's broader SQL and production feature set also remains part of
the comparison context. Dolt peak memory is blank in this August bundle because
a directly comparable memory method was not available. That historical value
must not be fabricated or combined with Python `tracemalloc` values. The
separate schema-3 bundle for review issues 5–12 uses an external parent
process-tree RSS sampler at 10 ms for isolated workers; it does not reuse these
historical allocations.
