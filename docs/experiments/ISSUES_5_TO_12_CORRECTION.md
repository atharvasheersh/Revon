# Corrections to Computing review issues 5 to 12

This record covers only review items 5–12. The review PDF is diagnostic input;
its recommendations do not expand the user-requested scope.

## 5. Storage multiplier wording

The manuscript reports Revon-H/Dolt repository-footprint ratios of 1.98x to
6.46x (about 98% to 546% more footprint). It no longer says “times more,”
which confuses a ratio with a percentage increase.

## 6. Memory metric

The new paper run samples process-tree RSS with the same external 10 ms `psutil` sampler
for every model, including Dolt's child processes. Each system/trial runs in a
fresh worker to avoid carrying another model's memory high-water mark into its
measurement. The value includes the common workload/oracle state and is not
product-only memory. The paper labels this as sampled workflow-level
process-tree RSS; peaks shorter than 10 ms may be missed. Historical `peak_memory_bytes`
values from prior bundles remain non-comparable and must not be pooled with it.

## 7. Audit scope

The manuscript calls the audit an internal evidence-integrity audit. It checks
workload digests, row and summary consistency, correctness flags, and derived
statistics. It does not independently reproduce timings or substitute for a
clean-clone rerun by another researcher.

## 8. Sensitivity chart scale

Figure 6 now uses the corrected sensitivity rerun and derives its vertical
maximum from the largest measured p75 value, with headroom and a 75 ms minimum
range. All corrected medians and p75 values fit. The review's 69.545 ms
`b8-d5` median came from the superseded output contract; the corrected run's
median is 33.681 ms. The plot shows medians only; it does not display an
interquartile range. The axis label is now fully visible.

## 9. API versus CLI boundary

The cross-system comparison remains an in-process Revon API versus Dolt CLI
workflow. The paper labels it that way and makes no tree-algorithm superiority
claim. Normalized outputs improve operation-contract parity, but they do not
remove Dolt process startup, SQL, or CLI costs.

## 10. Diff output contract

Every adapter now returns the same canonical JSON contract: sorted changed
keys with SHA-256 hashes for old and new values. Dolt's structured result is
parsed and normalized inside its timed diff; the Python adapters fully
materialize the same representation before the timer stops. The harness checks
the hash pairs against the workload oracle.

## 11. Commit timing

Dolt's timed commit path no longer creates a tag for each version. It times SQL
mutation, `dolt add`, and commit, retains the commit hash returned by Dolt, and
uses that hash for later history and checkout operations.

## 12. Checkout output contract

Every adapter returns the full target state as sorted canonical UTF-8 JSON.
Dolt query output is requested as JSON, parsed, sorted, and serialized to the
same representation inside the timed checkout. Correctness compares decoded
canonical states with the workload oracle.

## Validation

The full corrected paper-profile run is
`evidence/paper-corrected-issues5-12-externalrss-10ms-20260923`, run ID
`7090860464db41bbb96f5e3ef384c270`. It has 333 successful rows, 37 summary
groups, all correctness flags true, and no audit issues. Accounting is 74
warm-ups, 259 measured runs, 175 primary evaluation runs, and 35 measured Dolt
runs. The external RSS sampler uses 10 ms intervals. The corrected DOCX and
PDF were regenerated; all 10 PDF pages were rendered at 100 dpi and visually
checked. The PDF export used Microsoft Word because LibreOffice is unavailable.

The corrected fixed-trie sensitivity run is
`evidence/trie-sensitivity-issues8-20260923`; it has 45 successful executions,
10 warm-ups, 35 measured trials, and all five configuration groups marked
correct. It uses the canonical diff output contract. All 49 unit tests pass,
Python compilation passes, and `git diff --check` reports only line-ending
warnings. Issues 13–21 remain outside this correction.
