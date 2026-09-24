# Corrections for benchmark review issues 18 to 21

This addendum records the additional evidence and the limits that remain. The review PDF is treated as reviewer feedback; its recommendations are not inserted as project instructions. The primary paper run remains unchanged and the new sensitivity bundles are not pooled into its tables.

## Workload breadth and portability

The primary run still uses one deterministic seed per scenario, one flat key-value table, 32-byte values, ten commits, and at most 100,000 rows. A separate 10,000-row sensitivity study varies three seeds, payloads of 32 and 128 bytes, histories of 10 and 50 commits, and spread, range-local, and repeated-key updates. It compares Revon-M, Revon-H, and Dolt with seven measured trials on Windows and three on WSL2 Ubuntu. The Windows bundle has 405 successful rows (90 warm-ups and 315 measured); the WSL2 bundle has 180 successful rows (45 warm-ups and 135 measured). Both bundle audits passed.

The Windows and WSL2 runs used the same physical computer. The WSL2 run is a Linux user-space/kernel replication, not an independent Linux machine. The added workloads still use one synthetic flat table; no public multi-table dataset, alternate schema, or one-million-row run was completed. Issue 18 is therefore partly addressed, not closed.

## Paired uncertainty and results

The primary eight-scenario run now has 48 paired-bootstrap result rows: 32 for Dolt/Revon-H across import, commit, diff, and checkout; eight for the Revon-M/Revon-H diff ablation; and eight for SQL versus bulk initial import. Each ratio divides numerator latency by denominator latency for the same scenario and trial, so a ratio above one means the denominator was faster. A percentile bootstrap resamples the seven paired trial ratios 20,000 times. Three of eight Revon-M/Revon-H diff intervals include parity and are classified as inconclusive. All eight Dolt/Revon-H diff intervals exclude parity, but those remain in-process-versus-CLI workflow results, not engine-only speedups. Seven of the 48 total intervals include parity; four of eight SQL/bulk-import intervals include parity. A 5% margin is used only to label practical effect size; it is an analyst-selected threshold, not an externally validated benchmark standard.

Cross-seed intervals use a hierarchical bootstrap over three seed clusters and paired trial ratios. For the Windows sensitivity run, the Revon-M/Revon-H diff ratios were 1.58 [1.23, 1.87] for baseline spread updates, 1.62 [1.38, 1.72] for 128-byte payloads, 0.99 [0.90, 1.17] for 50-commit histories, 1.64 [1.38, 1.77] for range-local updates, and 2.24 [2.02, 2.38] for repeated-key updates. Values above one mean Revon-M took longer. WSL2 showed the same direction for four factors and parity overlap for the 50-commit history. These intervals describe the sampled synthetic cases on this host; three seeds do not establish general workload-population effects.

## CPU, I/O, and throughput

The WSL2 sensitivity run adds an external 10 ms process-tree sampler for CPU time and read/write byte counters when the OS exposes them. CPU samples were recorded for all 180 trials, but read-byte counters were present for 22 and write-byte counters for 60; missing counters are unavailable, not zero. A separate Windows telemetry rerun, `evidence/paper-issues14-windows-telemetry-20260924/`, contains 405 successful rows (90 warm-ups and 315 measured) and records process-tree peak RSS, CPU seconds, read bytes, write bytes, and serial commit-operation throughput on every row. Its schema-2 audit passed and all rows were correct. This closes issue 14's telemetry-availability gap for this Windows robustness matrix; it does not establish complete cross-platform I/O measurement or general resource efficiency. These process totals include setup and correctness checking, so they are not operation-specific resource costs. Serial commit throughput is commits divided by the sum of the measured commit intervals. It does not represent concurrent or end-to-end throughput.

No concurrent reader/writer experiment or ordered range-scan experiment was run. The primary paper makes no range-query, concurrency, production-throughput, CPU, or I/O superiority claim. Issue 21 is partly addressed and remains open for those workloads.

## Reproduction and integrity

The primary paired intervals are in `evidence/paper-corrected-issues13-17-counterbalanced-final-20260923/paired_ratio_uncertainty.csv`. The Windows and WSL2 sensitivity raw rows, manifests, audits, summaries, and seed-cluster intervals are stored in:

- `evidence/paper-issues18-20-robustness-20260923/`
- `evidence/paper-issues18-20-linux-wsl-20260923/`
- `evidence/paper-issues14-windows-telemetry-20260924/`

Run the analysis from the repository root:

```powershell
python -m experiments.paired_uncertainty evidence/paper-corrected-issues13-17-counterbalanced-final-20260923
python -m experiments.robustness_study --output-dir evidence/paper-issues18-20-robustness-20260923 --audit
python -m experiments.robustness_study --output-dir evidence/paper-issues18-20-linux-wsl-20260923 --audit
python -m experiments.robustness_study --output-dir evidence/paper-issues14-windows-telemetry-20260924 --audit
python -m experiments.robustness_summary evidence/paper-issues18-20-robustness-20260923
python -m experiments.robustness_summary evidence/paper-issues18-20-linux-wsl-20260923
```

The reports audit workload digests, status, correctness, matrix size, telemetry availability, and summary statistics. They do not independently reproduce wall-clock timings; no external researcher or clean-clone timing reproduction has been completed, so issue 7 remains open.
