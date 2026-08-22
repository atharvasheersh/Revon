# Commit note: reproducible final experiment harness

- Date: 2026-08-22
- Commit: `PENDING`
- Author: atharvasheersh
- Scope: evaluation

## Objective

Produce a paper-ready measurement pipeline for the primary Snapshot,
Log-only, Chronos-H, and Dolt comparison while retaining forced Merkle as a
clearly labelled Chronos ablation.

## Changes

- Added deterministic seeded workloads with identical mixed mutation batches
  and a SHA-256 workload identity shared across every model.
- Added durable Snapshot, Log-only, SQLite Chronos-M, SQLite Chronos-H, and
  native Dolt CLI adapters.
- Added isolated threshold calibration, warmups, repeated trials, raw CSV,
  median/IQR summaries, an environment manifest, correctness oracles, and
  explicit unavailable/error rows.
- Added import, commit, diff, checkout, storage, peak-memory, and natural-work
  metrics with their methods recorded alongside each result.
- Added regression tests and a research interpretation protocol.

## Verification

```text
python -m unittest -v
Ran 35 tests in 6.414s; OK

python -m experiments.final_benchmark --profile smoke --warmups 1 --trials 3
40 successful rows, 4 Dolt-unavailable rows, 0 error rows;
all measured Python variants passed correctness; threshold = 128 operations
```

## Design decisions

Calibration workloads are disjoint from evaluation workloads, and the final
evaluation always uses fresh repositories. Missing Dolt installations produce
blank `unavailable` records rather than synthetic timings. Chronos-M is an
ablation label; Chronos-H is the proposed system.

## Known limitations

- Dolt integration cannot execute on this machine until the `dolt` executable
  is installed on `PATH`.
- Dolt process-tree RSS requires optional `psutil`; current Python allocation
  and Dolt RSS measurements must not be charted as directly comparable memory
  results.
- The CLI adapter includes Dolt process startup and measures an application
  workflow, not an isolated storage-engine microbenchmark.

## Next action

Install Dolt, run the smoke matrix once, then collect the final paper profile
on one controlled machine without changing code or workload seeds.
