# Reviewer revision protocol

## Scope and authorisation

The experimental revision request authorised this Windows computer only, without cloud resources, journal submission, emails or Git publication. Git publication was separately authorised on 16 October 2026; this does not authorise journal submission. New results are author-run local experiments, not Linux results or independent-party reproduction. Existing Linux and historical evidence remains byte-identical and is never pooled into the new campaign.

## Frozen design

Executable plan: `evidence/review-revision-20261016/campaign/protocol.json`. The manifest records platform, runtime, SQLite, Dolt, memory availability, CPU topology, background process names, source hashes and the protocol hash. Python workers use the same `PYTHONHASHSEED=20261016`. The source copy is under `campaign/source/`.

| Component | Cases | Design | Query repetitions |
|---|---:|---|---|
| Calibration | 12 | 2 seeds × 2 localities × 3 mutation counts | 2 warm-ups + 7 measured blocks; 6 configurations/block |
| Held-out validation | 18 | 3 different seeds × same 2 localities × 3 mutation counts | Same |
| Sensitivity | 21 | 3 held-out seeds × 7 prespecified changes/controls | Same |
| Monitor diagnostic | 6 | 3 fresh-worker repeats × sampler off/on | Same |
| Additional public data | 18 | 2 source families × 3 repositories/histories × M/H/Dolt | 2 warm-ups + 7 measured queries/repository |
| Repeated scale | 18 | 100k/1M rows × 3 seeds × M/H/Dolt | Same |

Total plan: 93 fresh-worker cases and 3,402 queries (756 warm-ups and 2,646 measured queries). Each selector case builds one durable repository and queries it repeatedly; queries are not independent repository trials. The public CO2 replicates reuse one observed sequence. Wine and scale use three different generated histories.

Primary selector cases hold N=12,000, H=8, payload=32 bytes and geometry b=8,d=4 fixed. Changes/commit are 64, 512 or 4,096 (512, 4,096 or 32,768 total operations). Localities are spread and repeated-key. Candidates are T=512/4,096/16,384/65,536; forced log and forced Merkle are controls over the identical durable representation. Calibration minimises equally weighted case median latency divided by the lower forced-path median, with a lower-threshold tie-break. Selection is written before the first held-out worker starts. All candidates may be reported as prespecified diagnostics; validation results must not select a replacement winner.

Sensitivity changes N to 24,000, H to 16 with 256 changes/commit (same total operations), payload to 256 bytes, or geometry to b4-d6/b16-d3. Route-local updates use C=8 because a nine-bit hash-prefix bucket cannot support C=512 in this dataset; a separate spread C=8 control matches that count. The design is staged, not a full factorial. At fixed total operations, interval length and changes/commit trade off and cannot both be independently held fixed. The two alternative geometries have the same 4,096-leaf capacity as b8-d4.

## Public acquisition and premeasurement exclusions

The acquisition manifest retains URLs, versions, checksums, licence information and transformations. UCI Wine Quality (Cortez et al., DOI 10.24432/C56S3T, CC BY 4.0) contributes 6,497 red/white records. Keys are colour plus source row ordinal; eight seeded batches of 64 generated quality-field changes are artificial histories, not observed revisions. Numeric fields are retained as source strings inside canonical JSON; no inference about wine quality is made.

The DataHub CO2 package (ODC-PDDL-1.0, NOAA-derived Mauna Loa series) supplies the 11 most recent file-changing revisions returned by the API before timing. All raw files are retained. One revision contains only a CSV header. It was excluded before protocol freeze as a publication failure; the primary sequence links the adjacent nonempty snapshots. The resulting ten populated snapshots produce nine observed transitions from an initial 812 records. This is an observed repository publication history, not NOAA transaction logs or evidence that atmospheric observations were deleted.

Source CSV rows contain more fields than their headers. The adapter preserves trailing fields under `_extra_0`, etc., rather than silently dropping them or assigning scientific meanings. Dates identify records, row order/CSV formatting are ignored, and edits between sampled publications are not reconstructed. This upstream quality limitation restricts domain interpretation but does not prevent exact canonical-record diff checks.

Software Heritage was considered using its official graph documentation. A bounded published CSV revision sequence was chosen to obtain actual record changes without bulk graph acquisition on this memory-limited host. Repository fork-event counts would not establish record-level mutation history and were not used.

## Timing boundaries and fair comparison

Revon timings wrap `diff_versions` plus common canonical output construction. An ancestry/operation-count probe runs outside the timer and is reported as a probe, not subtracted as causal overhead. All Revon strategies share representation, persistence, histories and output contracts.

Dolt uses its native JSON diff CLI. Separate timers wrap command execution, JSON interpretation and common canonical output construction. The command interval combines process launch, native execution and native JSON output; it does not isolate tree traversal or SQL engine cost. No generic startup subtraction, server-interface substitution or engine-level ranking is permitted.

The sampler observes worker plus descendants every 10 ms, including construction, timing, verification and cleanup. Zero counters remain zero; unsupported/unobserved counters are missing. Windows process I/O counters are OS-reported bytes, not direct physical-disk traffic or database logical reads. PID lifetimes shorter than the sample interval can be missed. Worker RSS includes oracle/history objects.

The monitor off/on experiment is a diagnostic over the same history in separate fresh workers. Off precedes on within each pair; order, background load and cache effects prevent a precise causal overhead correction. Do not subtract its difference from other measurements.

## Correctness and inference

Observed outputs are decoded and compared with a separately constructed key/old-hash/new-hash oracle. Every historical state has observed and expected hashes. Identity, reverse, stored-object integrity and close/reopen checks apply to Revon outside timing. Dolt's observed JSON parsing is compared with the native adapter in preflight. Failures are retained and halt execution; no latency-driven exclusions are allowed.

Report per-repository median and IQR for seven timed queries. For three histories/repositories, report the median and range of repository medians, identifying whether histories actually differ. These are descriptive fixed-host estimates, not population confidence intervals. A lower forced-path median is a hindsight descriptive reference, not an executable selector oracle. Ratios below one relative to that reference can arise from timing variation. Many sensitivity comparisons are exploratory and receive no family-wise significance claim.

The existing one-run Linux million-row observations stay feasibility-only. Only the new repeated local scale cases may support a conditional descriptive scale comparison, subject to their own completeness, resource conditions and correctness audits.

## Separate post-campaign selector-cost diagnostic

The original `decision_probe_ms` reads the detached public changeset view. That
view copies operations, so the probe is not pure production selector overhead.
No original row was changed or discarded. A separate diagnostic in
`evidence/selector-cost-20261016/` extracts the actual unchanged production
function AST through validation, ancestry and internal changeset counting,
stopping before diff dispatch. Its own protocol is written before its timings.
It repeats the 18 held-out histories at T4096 and T65536, without selecting any
new policy: two warm-up and seven measured batches of 1,000 calls per condition.
The extracted prefix must agree with actual production dispatch. This warm
microbenchmark is not cold-cache overhead, timed diff traversal, or a causal
amount to subtract from full-workflow measurements. `tools/check_selector_cost.py`
checks its collection, history identities, batch accounting and summary.

## Reproduction

Install the experiment dependencies and Dolt 2.3.1 in an isolated environment. To acquire the exact source files in a new directory:

```python
from pathlib import Path
from experiments.review_revision_data import acquire
acquire(Path('/new/public_sources'), Path('evidence/review-revision-20261016/public_sources/acquisition.json'))
```

Then, from the matching source root:

```bash
python -m experiments.review_revision --prepare --output /new/campaign --public-sources /new/public_sources
python -m experiments.review_revision --output /new/campaign
python -m experiments.review_revision --output /new/campaign --audit
```

Use a new output directory and retain the existing evidence. A changed platform produces a separate timing campaign even when semantic hashes match. The auditor regenerates workloads and semantic oracles; it does not reproduce elapsed times.

## Maintained verification checks added after review

The live wrapper independently recalculates calibration medians, normalised
scores, winner and exact tie-break, using calibration cases only. It checks
finite positive timings, configurations, disjoint seeds and timezone-aware
protocol/calibration/freeze/validation ordering. Score comparison permits only
1e-12 relative floating summation variation, with zero absolute tolerance;
winner/tie choice is exact on recalculated scores. Frozen sources are unchanged.

Prefix verification uses the archived production source and exact retained
diagnostic script, validates five source hashes and compares the independently
derived expected prefix AST. Comments/whitespace/quote style may differ, but
function signatures, statements and expressions must agree. This adds no timing
or new policy selection. Canonical publication figures are versioned under
`paper/review-assets/figures/`; verification needs no ignored output directory.
