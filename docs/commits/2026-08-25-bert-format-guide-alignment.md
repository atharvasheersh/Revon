# Align final paper with the BERT formatting guide

Date: 2026-08-25

## Summary

Updated the final Revon manuscript using the explicit values in
`BERT_Paper_Formatting_Details.pdf` rather than relying only on visual
estimation from the source paper.

## Changes

- Set A4 pages with one-inch margins on every side.
- Set two equal columns with a 0.24-inch gap.
- Set the main body to 11-point Times New Roman with exactly 13.6-point
  leading, full justification, 0-point paragraph spacing, and a 0.15-inch
  first-line indent.
- Kept the 14.5-point bold title, 12-point main headings, 11-point
  subsections, 10-point abstract/captions/references, and 9-point tables.
- Added 17-point left and right indents to the abstract body.
- Enabled automatic hyphenation and removed first-line indents from the first
  prose paragraph following a heading.
- Added blue clickable numbered citations linked to bookmarked reference
  entries.
- Expanded the bibliography to 15 numbered entries and strengthened the
  literature review with three explicit subsections and a comparison matrix.
- Applied a restrained, consistent color palette to all graphs and the two
  system diagrams while keeping titles and bibliography text black.
- Preserved horizontal-rule tables, captions below figures and tables, and no
  visible page numbers.

## Verification

- Microsoft Word export: seven A4 pages.
- Every rendered PDF page visually inspected with no clipping, overlap,
  missing figures, broken tables, or orphaned trailing page.
- DOCX table geometry, accessibility, and image audits passed.
- Structural audit confirmed margins, column spacing, typography, abstract
  indents, automatic hyphenation, citation hyperlinks, and reference
  bookmarks.
- PDF audit confirmed the expected 9, 10, 11, 12, and 14.5-point type scale
  and blue citation text.

## Suggested commit title

```text
paper: align final manuscript with BERT formatting guide
```
