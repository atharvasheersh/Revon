# Final IEEE-style research paper

Date: 2026-08-24

## Summary

Replaced the preliminary working-paper evidence with the audited paper-profile
benchmark and completed the camera-ready research narrative.

## Changes

- Added a portable final-paper generator at
  `tools/build_final_research_paper.py`.
- Created separate final DOCX and PDF deliverables while preserving the earlier
  working draft.
- Applied a US Letter, IEEE-style two-column layout with black-only 12-point
  Times New Roman text and 1.5 line spacing throughout.
- Revised the abstract, results, Dolt comparison, discussion, limitations, and
  conclusion using only the final CSV evidence.
- Completed the literature review and compact comparison matrix with ten
  primary or official references.
- Added a dedicated Future Work section covering adaptive trie geometry,
  learned diff selection, compact encoding, chunking, garbage collection,
  branches, merges, concurrency, real datasets, one-million-row workloads, and
  unified telemetry.
- Added six captioned figures, including four evidence-backed charts with
  medians and interquartile ranges.
- Added the final five-configuration trie-sensitivity findings and avoided any
  claim that `b=8, d=4` is universally optimal.
- Explicitly documented Dolt feature/interface asymmetry, storage losses,
  outlier retention, and memory-measurement limitations.

## Verification

- `python -m unittest discover -v` - 44 tests passed
- `python -m experiments.evidence_audit output/benchmarks/paper-final-20260824`
  - passed with no issues
- 333 paper rows successful and correct
- 45 sensitivity rows successful and correct
- DOCX accessibility audit - zero findings
- Exact table-geometry audit - passed
- Microsoft Word PDF export - nine tagged US Letter pages
- PDF typography audit - visible text black, 12-point Times New Roman
- Poppler render - all pages visually inspected and clean

The typography follows the requested institutional formatting while retaining
IEEE-style structure; 12-point, 1.5-spaced text is not strict IEEE conference
template typography.

## Suggested commit title

```text
paper: finalize IEEE manuscript with audited benchmark results
```
