# Revon final research paper

Date: 2026-09-23

## Deliverables

- `paper/Revon_Final_Research_Paper.docx`
- `paper/Revon_Final_Research_Paper.pdf`
- Canonical repository: <https://github.com/atharvasheersh/Revon>

Only the final paper artifacts are versioned in the repository. Earlier working
drafts remain local preparation material and are excluded from Git. The final
files contain no draft-status banners or preliminary smoke tables.

## Publication format

- Authors: Atharva Sheersh Pandey, Adhyan Jain, and Poornima Nedunchezhian,
  School of Computer Science and Engineering, VIT Vellore
- School of Computer Science and Engineering
- VIT Vellore
- [poornima.n@vit.ac.in](mailto:poornima.n@vit.ac.in)
- A4 paper matching the supplied BERT manuscript's visual format
- Compact two-column body with a full-width title and author block
- Times New Roman typography: 11-point body, 12-point headings, and a
  14.5-point title
- Exactly 13.6-point body leading with a 0.15-inch first-line indent
- One-inch margins and a 0.24-inch gap between equal-width columns
- Abstract begins at the top of the first text column
- Arabic-numbered sections and decimal subsections
- Blue clickable numbered citations and a black numbered bibliography
- Eleven rendered pages
- Six figures and three tables
- Colored charts and architecture/workflow diagrams with a consistent,
  print-readable palette
- Fifteen bibliography entries

Only the publication layout was reproduced. The reference paper's content,
branding, and arXiv margin stamp were not copied.

The final structure is:

1. Introduction
2. Literature Review and Related Work
3. Revon Design
4. Experimental Methodology
5. Results
6. Discussion
7. Limitations and Threats to Validity
8. Future Work
9. Conclusion
10. References
11. Reproducibility and Data Availability

## Evidence sources

Current comparative numbers come from the audited paper-profile run for review
issues 13–17:

- `evidence/paper-corrected-issues13-17-counterbalanced-final-20260923/summary.csv`
- `evidence/paper-corrected-issues13-17-counterbalanced-final-20260923/raw_results.csv`
- `evidence/paper-corrected-issues13-17-counterbalanced-final-20260923/manifest.json`
- `evidence/paper-corrected-issues13-17-counterbalanced-final-20260923/evidence_audit.json`

Trie-sensitivity results come from:

- `evidence/trie-sensitivity-issues8-20260923/summary.csv`
- `evidence/trie-sensitivity-issues8-20260923/raw_results.csv`
- `evidence/trie-sensitivity-issues8-20260923/manifest.json`

The current run records Dolt 2.3.1 and has run ID
`b7a4ec7b610742d9b827f43fd5092fe2`. The audit passed with 540 successful rows,
60 summary groups, 120 warm-ups, and 420 measured trials. The primary five-system
evaluation has 280 measured trials, plus 56 SQL-Dolt and 56 Dolt bulk-import
trials. The August bundle remains available for provenance, with its Dolt diff
validation limitation documented in
`evidence/paper-final-20260824/ERRATA.md`.

## Figures

1. Revon architecture and research-contribution boundary
2. Incremental commit and adaptive diff workflow
3. Independent Revon-H threshold calibration
4. Final diff latency across eight workloads, including four distinct locality patterns
5. Revon-H versus Dolt commit and checkout latency
6. Fixed-trie branching-factor/depth sensitivity

## Claim boundaries

- The paper reports the observed system-level CLI-facing results, not an
  isolated claim that fixed tries are intrinsically faster than Prolly Trees.
- Diff results use one sorted key and old/new SHA-256 value-hash JSON contract;
  checkout results use one sorted canonical JSON state contract. Both are
  fully materialized during timing.
- Dolt commit timing excludes per-version tag creation and uses commit hashes
  for historical checkout. Dolt SQL/CLI and Revon API boundaries remain
  different, so the comparison is explicitly a workflow comparison.
- Revon-H's latency results are presented with its higher storage cost,
  measured import costs, narrower feature set, and runtime/interface asymmetry.
- Revon-M remains an ablation; the primary comparison is Snapshot, Log-only,
  Revon-H, and Dolt.
- Dolt's batched SQL initial import and CSV `dolt table import -r` initial
  import are reported as separate workflows. CSV serialization is timed as part
  of the bulk-import workflow; subsequent Dolt operations use the same adapter.
- Repository bytes are described as workflow footprint. Results also include
  bytes per UTF-8 logical payload byte, a residual that is not pure metadata,
  and representative post-compaction samples after Dolt `dolt gc` or SQLite
  `VACUUM`.
- Execution order is randomized and rotated within scenario/trial blocks;
  recorded positions are checked in raw results and by the audit.
- The former lexical `large-hot` case is now application-key-local. Separate
  range-local, repeated-key, and hash-route-local update workloads are reported;
  they do not establish range-query performance.
- Peak process-tree RSS is externally sampled at 10 ms for isolated workers,
  including Dolt child processes and common benchmark-oracle memory. It is not
  product-only memory. Peaks shorter than 10 ms may be missed; this remains a
  workflow-level estimate rather than an allocation metric.
- The 4,096-operation threshold is described as a frozen sampled boundary, not
  a universal crossover.
- `b=8, d=4` is described as a storage-conscious balanced default; `b=16, d=3`
  had the lowest median diff in the corrected sensitivity run, at higher storage.

## Artifact maintenance

The previous full builder is disabled because it restores the superseded
August claims. The current manuscript was patched in place to preserve later
layout edits. After auditing the corrected bundle, use:

```powershell
python -m experiments.evidence_audit evidence/paper-corrected-issues13-17-counterbalanced-final-20260923
python tools/revise_paper_issues13_to17.py
```

The maintenance utility depends only on `python-docx` and Pillow beyond the
Python standard library. It validates the final manifests, audit result, row
counts, correctness flags, Dolt version, and sensitivity summaries while
maintaining the editable DOCX. Export the author-approved DOCX to PDF using
Microsoft Word or LibreOffice.

## Verification completed for benchmark-review issues 1–21

- Current paper-profile evidence bundle:
  `evidence/paper-corrected-issues13-17-counterbalanced-final-20260923`, run ID
  `b7a4ec7b610742d9b827f43fd5092fe2`. Its schema-4 audit passed with 540
  successful rows, 60 summary groups, all correctness flags true, and no audit
  issues. It records 120 warm-ups, 420 measured rows, eight scenarios, and
  randomized counterbalanced execution order.
- All corrected Dolt JSON diffs were parsed and compared against the same
  workload oracle. The reported changed-key count is derived from Dolt output.
- Paired ratio intervals are stored beside the primary raw run. They resample
  seven same-scenario trial ratios and condition on each fixed workload and one
  host; they do not represent dataset-population or machine-to-machine error.
- The separate robustness study contains 405 Windows rows across three seeds
  and 180 WSL2 rows. It varies payload, history length, and update pattern at
  10,000 rows; WSL2 ran on the same physical computer.
- The WSL2 run records process-tree CPU time and serial commit throughput.
  Process I/O counters were incomplete. Concurrent workloads and ordered
  range queries remain unmeasured, and no production-system superiority claim
  is made.
- Corrected trie sensitivity bundle:
  `evidence/trie-sensitivity-issues8-20260923`; 45 executions, 10 warm-ups, 35
  measured runs, and all five configuration groups correct. Figure 6 is based
  on this run; it shows medians without error bars.
- Unit tests: all 56 passed. This included the corrected sensitivity-harness
  check, which decodes canonical state and verifies old/new hashes against the
  oracle.
- The DOCX and PDF were regenerated from the audited bundle. Microsoft Word
  exported the PDF, and all 11 pages were rendered at 100 dpi and visually
  checked. LibreOffice was unavailable.
- Dolt SQL and bulk import timings are separate. Storage reports total
  repository footprint, normalized bytes per final logical payload, the
  explicitly non-metadata-only residual, and sampled post-compaction size.
- Application-key, range, repeated-key, and hash-route locality are separate
  update workloads; the paper does not claim range-query results.
- Issue 18 remains partly open: the evidence still lacks alternate schemas,
  public multi-table datasets, one-million-row data, and independent Linux
  hardware. Issue 21 remains partly open: no concurrent reader/writer or
  ordered range-scan results are available.
- Literature review: four explicit subsections plus an eleven-row comparison
  matrix covering content addressing, persistent structures, dataset
  versioning, the system-design gap, and the implications for Revon-H's
  hypotheses and evaluation design
- Bibliographic validation: corrected the Merkle Search Tree DOI, author names
  for the dataset-versioning and OrpheusDB papers, upgraded DataHub to its CIDR
  publication, and added verified DOIs for dataset versioning, OrpheusDB, and
  LBFS
- Citation audit: 15 numbered bibliography entries and internal links from
  bracketed in-text citations to bookmarked reference entries

The resulting manuscript follows the supplied BERT paper's publication format
rather than the earlier IEEE-style institutional formatting.
