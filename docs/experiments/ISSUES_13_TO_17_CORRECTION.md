# Corrections for review issues 13–17

This note records the benchmark and manuscript changes for review issues 13–17. The complete paper-profile run is stored under `evidence/paper-corrected-issues13-17-counterbalanced-final-20260923/` after a successful evidence audit.

## 13. Dolt initial-import workflow

The benchmark now retains two explicitly named Dolt paths. `Dolt` uses the existing batched SQL `INSERT` workflow. `Dolt (bulk import)` writes the same initial logical state to CSV and times `dolt table import -r` plus the Dolt commit. CSV serialization and the import command are both included in the initial-import workflow time. The two medians are summarized separately; the bulk-import option is not substituted for the SQL baseline in the main cross-system comparison.

The harness was checked against the installed Dolt 2.3.1 CLI with a 100-row fixture. The bulk-imported table contained all expected rows after checkout.

## 14. Symmetric latency and memory instrumentation

Timed operations run without `tracemalloc`. An external parent process samples process-tree RSS every 10 ms for each isolated worker, including Dolt child processes. Sampling is outside timed operations. This uses one measurement method across systems; it does not eliminate operating-system scheduling noise, and peaks shorter than 10 ms can be missed.

## 15. Trial order

Within each scenario and trial kind, the model list is seeded and shuffled once, then rotated by trial number. For six evaluation variants, the first six measured trials place each variant in each execution position exactly once; trial seven begins a new cycle. `execution_order` is recorded in each raw row and validated as a contiguous block by the audit. This controls position effects better than independent random shuffles but does not eliminate all time drift.

## 16. Storage interpretation

The benchmark labels directory size as total repository/workflow footprint. It also reports bytes per UTF-8 logical key/value payload byte and the repository-minus-payload residual. That residual contains encoding, indexing, metadata, and compression effects; it is not pure metadata overhead. A representative measured trial per scenario and compactable system is also sampled after offline `dolt gc` or SQLite `VACUUM`. Compaction time is excluded from operation latency and RSS sampling. This is a bounded post-compaction observation, not a universal steady-state storage claim.

## 17. Locality coverage

The previous `large-hot` workload was lexically adjacent application keys, so it favored that key ordering and did not represent general locality. It is now named `large-application-key-local`. Separate workloads exercise contiguous ranges of sorted keys, repeated updates to a small key set, and keys sharing the same nine-bit SHA-256 routing prefix used by Revon's trie. The paper reports these as distinct synthetic update patterns. Hash-route locality is specific to Revon's routing scheme, and none of these update workloads demonstrates range-query performance.

## Validation

The targeted experiment tests cover the locality generators, the Dolt bulk-import oracle check, and balanced randomized order. Final run counts, correctness, summary recomputation, normalized storage fields, compaction fields, and order blocks are checked by `experiments.evidence_audit`. The audit validates evidence consistency; it does not independently reproduce wall-clock measurements.

The final run (`b7a4ec7b610742d9b827f43fd5092fe2`) passed with 540 successful rows, 60 summary groups, 120 warm-ups, and 420 measured trials. There are 280 primary five-system evaluation trials, 56 SQL-path Dolt trials, and 56 bulk-import Dolt trials. All 51 unit tests passed.

Across eight scenario medians, batched SQL initial import measured 1,814.83 ms and the CSV bulk-import workflow measured 1,701.25 ms (SQL/bulk ratio 1.07). That is a modest bulk-import difference in this tested environment, not evidence that bulk import is universally faster. Revon-H/Dolt total repository-footprint ratios ranged from 1.99 to 6.90; normalized payload-byte and residual ratios are reported in the manuscript. Post-compaction values are one sample per scenario/system and should be treated as descriptive.
