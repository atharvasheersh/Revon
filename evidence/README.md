# Audited research evidence

This directory contains the reviewed evidence used by the final Revon paper.
It is versioned so a reader can audit the published tables and figures from a
fresh clone.

## Bundles

- `paper-final-20260824/` is the original 333-execution run (74 warm-ups,
  259 measured runs, of which 175 are primary evaluation runs). It is retained
  for provenance. Its Dolt `changed_keys` values came from the expected
  workload, and its Dolt `correctness=True` flags did not validate diff
  contents. Do not use those fields as Dolt observations.
- `paper-corrected-20260923/` reruns the first four review corrections with
  observed JSON Dolt diffs checked against the key/value oracle.
- `paper-corrected-issues5-12-externalrss-10ms-20260923/` refreshes all five
  systems under schema 3. It uses canonical diff and checkout outputs, stores
  Dolt commit hashes instead of creating timed tags, and externally samples
  isolated process-tree RSS at 10 ms. It is retained as the prior correction
  stage and is superseded for current paper claims by issues 13–17.
- `paper-corrected-issues13-17-counterbalanced-final-20260923/` is the current
  schema-4, 540-execution primary paper run. It separates SQL and Dolt bulk initial
  import, uses balanced randomized order across trials, adds three locality
  workloads, and reports normalized and post-compaction workflow storage. Its
  internal evidence-integrity audit passed with all 540 rows successful.
  Its `paired_ratio_uncertainty.csv` sidecar reports within-trial paired
  bootstrap intervals for initial import, incremental commit, diff, checkout,
  and SQL versus bulk import; intervals condition on each fixed scenario and
  one Windows host.
- `paper-issues18-20-robustness-20260923/` contains the separate Windows
  sensitivity run (405 rows, three seeds, seven measured repetitions) across
  payload, history, and update-pattern variants. Its seed-cluster bootstrap
  found the 50-commit comparison inconclusive.
- `paper-issues18-20-linux-wsl-20260923/` contains a smaller WSL2 Ubuntu
  replication (180 rows, three measured repetitions) of the same 10,000-row
  variants, plus process-tree CPU/I/O counters and serial commit throughput
  where supported. WSL2 ran on the same physical computer as Windows. It is not
  an independent-machine replication, and its I/O counters are incomplete.
- The interrupted scratch attempts `paper-corrected-issues13-17-randomized-bulk-locality-20260923/`
  and `paper-corrected-issues13-17-counterbalanced-20260923/` have no complete
  audited result bundle and must not be cited. Use only the
  `...-counterbalanced-final-20260923/` bundle above.
- `trie-sensitivity-issues8-20260923/` is the corrected 45-execution
  branching-factor/depth sensitivity run. It uses the canonical diff output
  contract and backs Figure 6.
- `trie-sensitivity-20260824/` is retained as historical evidence. Its results
  use the prior output contract and are superseded by the corrected sensitivity
  run for current claims.

Re-run the internal evidence-integrity audit from the repository root:

```powershell
python -m experiments.evidence_audit evidence/paper-corrected-issues13-17-counterbalanced-final-20260923
python -m experiments.robustness_study --output-dir evidence/paper-issues18-20-robustness-20260923 --audit
python -m experiments.robustness_study --output-dir evidence/paper-issues18-20-linux-wsl-20260923 --audit
```

Unspecified new runs default to the ignored `output/` directory. The current
paper-profile run was written to its named bundle above and retained only after
its audit passed. The interrupted scratch-only attempt is listed separately and
must not be cited.
