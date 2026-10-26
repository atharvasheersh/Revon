# Revon publication files

The current manuscript is **Revon Research Paper Springer Nature**:

Title: **Revon: Log and Merkle Differencing for Durable Structured Data Versioning**.
The unpublished manuscript presents an auditable prototype and a bounded
workflow/selection study; the fixed trie is not a new adaptive index.

- [PDF](Revon%20Research%20Paper%20Springer%20Nature.pdf) — the reference layout for submission.
- [DOCX](Revon%20Research%20Paper%20Springer%20Nature.docx) — the editable companion.
- [Windows reproducibility archive](Revon_Review_Revision_Reproducibility_20261016.zip) — the Windows campaign, exact sources, public acquisition metadata, raw observations, derived figures, response documents and audit tools.
- [Original Linux archive](Revon_Linux_Reproducibility_Supplement.zip) — unchanged source snapshots, protocols, manifests, raw observations, semantic verification and internal audits for the historical Linux campaigns.

The manuscript links to the current [GitHub repository](https://github.com/atharvasheersh/Revon)
and the archive on `main`. It does not identify a fixed repository commit.
The executed source snapshots and collection manifests remain inside each evidence
bundle; updates to the repository do not replace those experiment records.
Both archives accompany the manuscript in this repository on `main`. Neither
archive's presence establishes journal upload or independent timing reproduction.
Git publication is authorised separately from author approval for journal
submission. Current publication and CI records are in the verification report.

The Windows evaluation comprises 93 cases, each run in a fresh worker process,
and 3,402 queries (2,646 measured). The 93 cases include 18 public-source cases
and 18 scale cases. A separate warm decision-prefix diagnostic covers 18
histories and 252,000 measured prefix calls, not additional full-workflow trials.
The PDF has 31 pages, 17 tables, 10 figures and 68 references. The editable Word
document also renders to 31 pages. The hand-edited prose and restored formatting
preserve all numerical table entries and nine figure images. Figure 2 has a
separate connector-layout repair with unchanged labels and physical dimensions.
All 68 references
have clickable source links; hyperlinks are blue and the remaining text is black.
The [reference audit](../docs/paper/REFERENCE_VERIFICATION_20261026.md) confirms
source identities and records access limitations. It does not establish that
each source supports the paper's claims.
Two explanatory table cells have editorial wording changes; the historical-table
gate permits only the exact reviewed source-description replacement. See the [supervisor response](../docs/paper/REVIEW_RESPONSE.md),
[response matrix](../docs/paper/REVIEW_RESPONSE_MATRIX.md),
[claim register](../docs/paper/CLAIM_EVIDENCE_REGISTER.md) and
[skeptical audit](../docs/paper/FINAL_REVIEW_AUDIT.md).

## Earlier versions

The [previous versions](previous%20versions/) directory retains the earlier
Discover Computing, IEEE and Springer DOCX/PDF exports, including the snapshots
before the October prose revisions. They are historical artifacts,
not the current submission. Their original model and evidence checks remain in
the publication gate. Older review sources are retained separately under
[`older versions/`](older%20versions/README.md).

## Validation and editing

From the repository root:

```bash
python -m pip install -r requirements-publication.txt
python -m unittest discover -s tools/tests -v
python tools/check_final_paper.py
```

These checks read the committed artifacts and recorded evidence. They do not
repeat the experiments or certify the paper's scientific conclusions, journal
eligibility, plagiarism status or AI-detector score. Exported manuscript changes
also require visual inspection. The manuscript still requires author review
before submission.

When revising the current paper, update its PDF and DOCX together. The archived
builders target earlier manuscript versions and must not overwrite this pair.

## Earlier manuscript build pipeline

Use `requirements.txt` for document/plot generation. Font conversion is not
needed: licensed ready-to-use fonts and their source assets are retained under
`tools/publication_assets/reference_fonts/`. Builders read the preserved semantic
baseline under `previous versions/review-baseline-20261016/`, insert audited
experimental results, then apply the reviewed first-submission prose from
`tools/publication_assets/first_submission_editorial.json`. Source-text and hash
guards reject changed inputs before applying any editorial override. Never use
a new benchmark run to overwrite collected evidence. The fonttools dependency
is pinned in `requirements.txt` for the retained reference renderer.

```bash
python -c "from pathlib import Path; from experiments.analyze_review_revision import plots; plots(Path('evidence/review-revision-20261016/campaign'), Path('paper/review-assets/figures'))"
python tools/revise_review_manuscript.py
python tools/render_review_manuscript.py
```

These builders reproduce the earlier generated draft, not the author's later
hand-edited prose and 68-reference bibliography. They still use the older
`Revon Research Paper Springer` stem. Do not use their output to replace the
current pair. Edit the current DOCX and export its PDF together. On Windows
with Word installed:

```powershell
& '.\tools\render_docx_with_word.ps1' -InputPath 'C:\Users\admin\Desktop\Revon\paper\Revon Research Paper Springer Nature.docx' -OutputPdf 'C:\Users\admin\Desktop\Revon\output\review_revision\word-render.pdf'
python tools/render_review_qa.py
```

Do not automatically replace the reviewed publication model after arbitrary
changes. `freeze_review_publication.py` records approved artifact expectations;
it is not a scientific validator. The independent historical-table/figure,
raw-evidence and numerical-derivation gates must still pass after a new freeze.

## Verification repairs after the second review

Figures 8–10 have six canonical PNG/PDF assets in `review-assets/figures/`.
The repaired Figure 2 has a canonical SVG source and PNG in the same directory.
The historical figure gate permits only that exact reviewed replacement and
still validates the original Figure 2 inside the unchanged Linux archive.
They are versioned package inputs; temporary renders remain under ignored
`output/`. Existing assets were copied without regeneration, preserving their
bytes. Replot only when deliberately revising a figure, then review the change.
Package construction fails if any required asset is absent. The local-only
`ALL_21_ISSUES_RECHECK.md` is excluded from the archive.

The maintained campaign checker independently recomputes calibration scores,
the minimizing threshold and the exact smaller-threshold tie-break from raw
calibration timings. It also checks split identities and chronological order.
The diagnostic checker compares the retained prefix AST with the prefix
derived from the archived production function and validates recorded source
hashes. Its original benchmark script is retained byte-for-byte at
`../tools/publication_assets/selector_cost_source_20261016.py`.
Frozen executed collections are unchanged. See the current
[verification report](../docs/paper/REVISION_VERIFICATION_REPORT.md) for actual
test outcomes, clean-snapshot construction and publication status.

The optional original-inventory check `python tools/check_review_baseline.py`
is strict and local: its pre-edit inventory includes 35 scratch/bytecode files.
Use `--portable` in a clean snapshot; that mode omits only those incidental
paths and still checks 1,294 protected files and the old manuscript backups.
All sealed collection/source checks remain required in the aggregate gate.
