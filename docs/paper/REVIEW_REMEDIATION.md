# Verification and packaging repairs after the second review

Scope: local repairs, 16 October 2026, followed by separately authorised Git
publication. No new benchmark timing campaign, cloud or journal submission.
Canonical manuscripts, raw measurements, executed
sources and sealed collection manifests retain their original bytes.

## Chronological work and acceptance

1. Record protected hashes and reproduce the three failures on disposable
   copies. The old audit accepted zero calibration scores, prefix accounting
   accepted unrelated code with refreshed hashes, and package validation
   required ignored local output assets.
2. Copy six exact PNG/PDF assets to `paper/review-assets/figures/` and update
   builders. Explicit required membership prevents silent omission. Exclude
   the ignored local review document `ALL_21_ISSUES_RECHECK.md` as well as output.
3. Recalculate calibration scores independently from raw measured records.
   Check configurations, finite positive timings, minimizing threshold, exact
   smaller-threshold tie-break, disjoint seeds and timezone-aware protocol/
   start/completion/freeze/validation ordering. Validation timings never enter
   the objective. Relative tolerance is 1e-12, absolute tolerance zero, solely
   for floating summation differences across supported Python versions.
   Winner/tie selection uses recalculated scores without approximate ties.
4. Verify five retained source files for the prefix diagnostic. Its original
   benchmark script is copied byte-for-byte into publication assets; its hash
   was already recorded in the unchanged diagnostic protocol. Independently
   derive the expected prefix from archived `VersionedDatabase.diff_versions`,
   stopping at the first log-path dispatch. AST comparison ignores locations,
   comments, whitespace and quote style, but requires the same signature,
   statements and expressions. No extracted code is executed by this check.
5. Add 25 isolated regression tests: resigned zero scores, wrong winner/tie,
   invalid timings/configurations/chronology, ignored validation timings,
   missing figures, changed prefix/source/history, retained batch accounting,
   strict local baseline preservation and explicitly portable baseline checks.
6. Run implementation/publication tests, semantic replay, historical evidence,
   manuscript agreement, package correspondence and protected-byte checks.
7. Rebuild the package after code/docs settle. Record its final hash in the
   verification report outside the ZIP to avoid a circular dependency.
8. Construct an explicitly selected clean snapshot from versioned files plus
   intended new revision files. Exclude ignored/private/unrelated inputs and
   Git metadata. Install pinned verification dependencies in an isolated
   environment; repeat tests and the complete publication gate.
9. Inspect final changes; distinguish local completion from pending repository
   publication, remote CI and author approval before submission.

## Verification entry points

```bash
python -m unittest discover -s tests -v
python -m unittest discover -s tools/tests -v
python tools/check_final_paper.py
python tools/check_review_baseline.py
python tools/check_review_package.py
```

`check_review_baseline.py` defaults to a strict local check of all original
1,329 inventoried files, including 35 incidental scratch/bytecode files. These
are preserved locally, not distributed. In a clean snapshot use
`python tools/check_review_baseline.py --portable`: it excludes only inventory
paths under `.work` or `__pycache__`, requires the remaining 1,294 files and
original manuscript backups, and does not weaken any sealed collection check.
The first clean-snapshot attempt exposed this distinction; regression tests
confirm that portable mode still rejects changed scientific evidence.

Install `requirements-test.txt` and `requirements-publication.txt` first. Dolt
2.3.1 on PATH enables native equivalence tests; disclose skips if unavailable.
Artifact checks need no Word, font installation, plotting, raw TLC download or
ignored output. The historical absolute data path is mapped to supplied public
sources only inside a disposable replay copy. Word rendering is separate QA.

Actual commands/runtimes, outcomes, clean-snapshot selection, final hashes and
remaining limits are recorded in
[REVISION_VERIFICATION_REPORT.md](REVISION_VERIFICATION_REPORT.md), outside
the ZIP. Local log/manifest locations are identified there. The package contains
the maintained tools and tests needed to repeat these verification checks.

## Research interpretation

These repairs add no timing evidence or algorithmic novelty. Actual calibration
scores still select T=65,536, behaving as always-log over the primary matrix.
Adaptive benefit, API/CLI confounding, worker telemetry, hardware/history
coverage and independent reproduction retain their documented limits.
