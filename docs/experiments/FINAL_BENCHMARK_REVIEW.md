# Final benchmark evidence review

Date: 2026-08-24

Evidence bundle: `evidence/paper-final-20260824/`

## Verdict

The paper-profile bundle passes the independent evidence audit. All 333 raw
rows are present, successful, and correct. The 37 summary groups reproduce the
raw measured trials exactly. Dolt 2.3.1 is recorded consistently, and no row
was failed, unavailable, removed, or edited.

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
| All variants report correctness | Pass | `333/333` raw rows have `correctness=True`. |
| Dolt version is recorded | Pass | Every Dolt row records `dolt version 2.3.1`. |
| No unavailable or failed trials | Pass | Status distribution is exactly `ok: 333`. |
| Raw CSV, summary CSV, and manifest agree | Pass | Trial matrix, run ID, platform, workload metadata, digests, summary medians, p25, and p75 were independently recomputed. |
| Chronos-H selection behaves correctly | Pass | The selector follows the inclusive 4,096-operation threshold in every raw row. |
| Outliers investigated, not deleted | Pass | All candidates remain in `raw_results.csv` and therefore in the seven-trial medians and quartiles. |

## Bundle reconciliation

- Profile: `paper`
- Run ID: `7048cc1674dc4038a8e42c87818b9088`
- Warmups: 2 per configuration
- Measured trials: 7 per configuration
- Raw rows: 333
- Summary rows: 37
- Models: Snapshot, Log-only, Chronos-M, Chronos-H, and Dolt
- Calibration models: Chronos log and forced Merkle
- Workload integrity: every scenario was regenerated from its manifest seed;
  all workload SHA-256 values and expected changed-key counts matched.
- Environment integrity: raw Python version and platform fields agree with the
  manifest.

Expected raw-row count:

```text
calibration: 6 scenarios x 2 models x (2 warmups + 7 measured) = 108
evaluation:  5 scenarios x 5 models x (2 warmups + 7 measured) = 225
total:                                                        = 333
```

## Chronos-H strategy review

The calibrated threshold is 4,096 operations. Chronos-H uses the log when the
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
| small-sparse / Chronos-M / 7 | checkout | 4.417 ms | 3.20x | Diff was also elevated (1.98x), while correctness and node work were unchanged. |
| small-sparse / Dolt / 2 | diff | 493.972 ms | 2.62x | Import, commit, and checkout were also elevated, indicating a whole-trial CLI/runtime slowdown. |
| small-sparse / Log-only / 6 | checkout | 5.358 ms | 2.44x | Diff was simultaneously elevated; correctness and operation count were unchanged. |
| small-sparse / Log-only / 6 | diff | 2.472 ms | 2.09x | Same transient late-operation slowdown as the checkout value. |

These candidates affect the smallest and shortest operations, where scheduler,
filesystem, process-startup, and cache noise have the largest relative effect.
They do not coincide with incorrect output, altered workload hashes, changed
work counts, missing data, or failed trials. They were retained. The paper must
report medians and interquartile ranges rather than selecting faster trials.

## Interpretation boundary

This audit establishes evidence integrity, not that Chronos wins every metric.
The paper should report where Chronos-H wins, loses, or trades latency for
storage. Dolt's broader SQL and production feature set also remains part of
the comparison context. Dolt peak memory is blank in this bundle because a
directly comparable memory method was not available; it must not be fabricated
or combined with Python `tracemalloc` values in one comparative chart.
