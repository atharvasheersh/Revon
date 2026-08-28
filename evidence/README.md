# Audited research evidence

This directory contains the reviewed evidence used by the final Chronos paper.
It is versioned so a reader can audit the published tables and figures from a
fresh clone.

## Bundles

- `paper-final-20260824/` contains the 333-row Snapshot, Log-only, Chronos-M,
  Chronos-H, and Dolt evaluation, its manifest, recomputed summaries, and
  non-destructive outlier review.
- `trie-sensitivity-20260824/` contains the 45-row branching-factor/depth
  sensitivity study and its manifest and summaries.

Re-run the independent paper-evidence audit from the repository root:

```powershell
python -m experiments.evidence_audit evidence/paper-final-20260824
```

Timestamped smoke tests and new experimental runs continue to write under the
ignored `output/` directory. Only a reviewed, anonymized bundle should be moved
into this directory.
