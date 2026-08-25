# Research paper working draft

Date: 2026-08-23

## Summary

Created the first paper-ready Chronos draft in editable DOCX and matching PDF
formats. The draft completes the architecture, methodology, and initial
literature-review matrix while keeping final empirical claims gated on the
paper-profile experiment.

## Content added

- Defined the research questions, contribution boundary, fixed-depth Merkle
  trie, incremental copy-on-write update path, adaptive diff policy, SQLite
  persistence contract, and current system limits.
- Added a primary-source literature review covering Merkle trees, Git, Dolt,
  DataHub, Decibel, OrpheusDB, dataset-version storage trade-offs, Noms, and
  ForkBase.
- Specified the Snapshot, Log-only, Chronos-M, Chronos-H, and Dolt variants,
  deterministic workloads, calibration/evaluation split, metric contracts,
  repetition protocol, fairness controls, and analysis plan.
- Generated the preliminary result table and chart programmatically from
  `output/benchmarks/check-again/summary.csv`.
- Marked the smoke results as pipeline validation only because Dolt was absent
  and the run used three measured trials at one dataset size.
- Added a concrete evidence gate for the Dolt run, extended threshold
  calibration, paper-profile trials, trie sensitivity sweep, and final paper
  revisions.

## Generated artifacts

- `output/docs/Chronos_Research_Paper_Working_Draft.docx`
- `output/pdf/Chronos_Research_Paper_Working_Draft.pdf`

The reproducible generator is `tools/build_research_paper.py`.

## Verification

- All 12 Word tables passed exact-width OOXML geometry checks.
- The DOCX accessibility audit reported zero findings after adding image alt
  text and table-header metadata.
- Microsoft Word exported a tagged 14-page PDF.
- Every PDF page was rendered and visually inspected; no clipped, blank, or
  overlapping content was found.
- PDF text extraction confirmed all 14 pages contain text and that the
  preliminary-results warning, final benchmark command, and references are
  present.

## Known limitations

- Dolt results are intentionally absent until Dolt is installed and the final
  paper profile is run.
- The literature-review matrix is ready for supervisor feedback but may need
  formatting changes to match the institution's final citation template.
- Final results, discussion, abstract, and conclusion must be refreshed from
  the reviewed paper-profile CSV bundle before submission.
