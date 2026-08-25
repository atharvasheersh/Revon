# Final BERT-format research paper

Date: 2026-08-24

## Summary

Replaced the preliminary working-paper evidence with the audited paper-profile
benchmark and completed the camera-ready research narrative.

## Changes

- Added a portable final-paper generator at
  `tools/build_final_research_paper.py`.
- Created separate final DOCX and PDF deliverables while preserving the earlier
  working draft.
- Restyled the paper to match the supplied BERT manuscript: A4 pages, compact
  Times New Roman typography, a full-width title/author block, and two-column
  body text.
- Applied the supplied Word recreation values exactly: one-inch margins,
  0.24-inch column spacing, 11-point body text, 13.6-point leading, and a
  0.15-inch first-line indent.
- Narrowed the abstract by 17 points on each side and enabled automatic
  hyphenation for the compact ACL-style column texture.
- Converted section numbering and citations to Arabic section,
  decimal-subsection, and numbered-reference conventions.
- Added blue clickable internal links from numbered citations to their
  reference entries.
- Reworked tables to use compact horizontal rules instead of boxed grids and
  placed all figure and table captions beneath their objects.
- Revised the abstract, results, Dolt comparison, discussion, limitations, and
  conclusion using only the final CSV evidence.
- Completed the literature review and compact comparison matrix with fifteen
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
- Microsoft Word PDF export - seven A4 pages
- PDF typography audit - 11-point Times New Roman body, 9-point tables,
  11/12-point headings, and a 14.5-point title
- Poppler render - all pages visually inspected and clean

The source paper was used only as a visual-format reference; its content,
branding, and arXiv margin stamp were not copied.

## Suggested commit title

```text
paper: match final manuscript to BERT publication format
```
