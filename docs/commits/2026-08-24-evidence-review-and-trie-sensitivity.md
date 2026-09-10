# Final evidence review and trie sensitivity

Date: 2026-08-24

Commit: `PENDING`

## Objective

Validate the final paper-profile evidence without deleting unfavorable trials,
then test whether Revon's default fixed-depth trie geometry is a reasonable
design point rather than assuming it is universally optimal.

## Changes

- Added `experiments.evidence_audit`, which reconciles the manifest, raw CSV,
  and summary CSV; regenerates deterministic workload identities; validates
  correctness, Dolt metadata, trial completeness, and Revon-H selection; and
  emits an outlier review without modifying raw evidence.
- Audited `output/benchmarks/paper-final-20260824`: all 333 raw rows passed,
  Dolt 2.3.1 was recorded, and every one of the 37 summary groups reproduced
  the raw trial statistics.
- Investigated all Tukey outlier candidates. Severe timing candidates were
  retained because correctness, workload hashes, and structural work remained
  stable and the paper reports robust medians/IQRs.
- Added `experiments.trie_sensitivity` with five controlled branching-factor /
  depth configurations, construction work counters, and raw/summary/manifest
  outputs.
- Completed 45 sensitivity trials with one shared workload digest and no
  errors or incorrect results.
- Added paper-ready evidence and sensitivity reports under `docs/experiments/`.

## Verification

- `python -m unittest discover -s tests -v`
- `python -m experiments.evidence_audit output/benchmarks/paper-final-20260824`
- Full sensitivity run: 2 warmups and 7 measured trials for five geometries
- `python -m unittest discover -s tests -v` — 44 tests passed

## Result

The final benchmark evidence is internally consistent and suitable for paper
analysis. The sensitivity study shows that `b8-d4` is a storage-conscious
balanced default, while `b8-d3` is faster on the controlled workload at the
cost of 61.9% more storage and three times as many examined leaf entries.
