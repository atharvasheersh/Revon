# Corrections to the first four Computing rejection issues

The review PDF is a diagnosis. This record states what was changed and what
the resulting evidence can support.

## 1. Execution and trial counts

The original 333-row headline called every execution a trial. That was wrong.
Both the original and corrected paper-profile matrices contain 333 executions:

| Phase | Warm-ups | Measured |
| --- | ---: | ---: |
| Selector calibration | 24 | 84 |
| Primary five-system evaluation | 50 | 175 |
| Total | 74 | 259 |

The primary evaluation has seven measured runs for each of five systems in
each of five scenarios. Dolt contributes 35 measured evaluation runs. All
warm-ups remain in the raw CSV but are excluded from summary statistics.

## 2. Dolt diff semantics

The old adapter treated a successful Dolt diff command as sufficient, because
it returned `None` to the harness. That was a correctness bug. The revised
adapter requests Dolt's JSON diff, parses every changed key with its old and
new value, rejects malformed or repeated rows, and compares the complete map
with the workload's initial and final states. A successful command with a
wrong diff now fails the trial. Tests cover real Dolt output and a deliberately
wrong diff.

## 3. Changed-key provenance

In the original bundle, all 45 Dolt `changed_keys` cells were copied from the
expected workload. They were not Dolt measurements. The original CSV remains
unchanged for provenance and is marked with an adjacent erratum. In the
corrected schema-version-2 run, `changed_keys` is the count of parsed Dolt
diff rows. The internal audit checks it against the regenerated oracle, but
does not independently reproduce Dolt's command output.

## 4. Latency ratios

The phrase “x lower latency” has been removed from the current manuscript.
For each scenario and operation, the reported speedup is
`median(Dolt latency) / median(Revon-H latency)`. A ratio above one is stated
as “Revon-H was x times as fast.” These are ratios of separate medians; no
confidence interval is implied. Charts, Table 3, the abstract, results, and
conclusion are regenerated from the corrected run.

## Limits that remain

The new run changes Dolt's timed diff output from tabular text to JSON and
includes parsing in the timed operation. Old and new diff latencies should not
be pooled as identical measurements. Revon still uses an in-process Python
interface while Dolt runs as a CLI workflow. The first four fixes do not solve
that interface mismatch or the other fairness and statistical issues in the
review. The audit is an internal consistency check, not independent
reproduction of timings or Dolt output.

The corrected-run Dolt/Revon-H diff speedups from separate medians were 592.1x
(small sparse), 518.9x (medium sparse), 7.7x (medium dense), 84.8x (large
sparse), and 73.5x (large hot). The new run's 35 measured Dolt evaluation
diffs reported 95, 100, 6,502, 995, and 671 changed keys for those scenarios,
respectively, and every observed key/value diff matched the oracle. These
large ratios are system-workflow results; they do not show that Revon's trie
algorithm is intrinsically faster. There are only seven measured repetitions
per configuration and no confidence intervals for the ratios.

## Recheck status

- Corrected evidence audit: passed, 333 successful rows, 37 summary groups,
  no audit issues.
- Trial accounting: 74 warm-ups, 259 measured, 175 primary evaluation, 35
  measured Dolt evaluation runs.
- Full unit suite: 47 passed, including successful local Dolt integration and
  deliberate wrong-diff rejection.
- The manuscript DOCX and Computing cover-letter DOCX were edited. The PDF
  renderer could not be completed in this environment: LibreOffice is absent
  and Microsoft Word COM remained blocked after launch. The existing manuscript
  PDF is therefore stale relative to the revised DOCX and needs a local Word
  export before submission.
- DOCX structural recheck found and corrected an outdated August evidence-bundle
  pointer in the reproducibility appendix. The current appendix points to the
  corrected bundle; text, table, and embedded-image structure were rechecked.
