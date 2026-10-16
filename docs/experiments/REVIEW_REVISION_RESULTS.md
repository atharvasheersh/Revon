# Review revision experiment completion report

## Execution and evidence boundaries

All work used the authorised local Windows computer. No cloud was provisioned
or restarted. Main collection: `evidence/review-revision-20261016/`. Separate
post-campaign decision-prefix diagnostic: `evidence/selector-cost-20261016/`.

| Evidence family | Status / unit | Use in this revision |
|---|---|---|
| Legacy `paper-final-20260824` | Erratum: Dolt fields did not establish observed semantic output | Historical only; no recovered correctness or pooling claim |
| Repaired 2026-09-23 Windows campaigns | Separately retained workflow evidence | Preserved, not replaced or pooled with new rows |
| Linux primary 20261008 | 516 executions, fixed-history repeated timings | Original figures/tables and adverse threshold result preserved |
| Linux final supplement 20261008 | 27 zero-preserving telemetry + 45 geometry executions | Separate 72-execution supplement preserved |
| Local review 20261016 | 93 fresh workers, 3,402 checked queries | New frozen controlled/public/scale campaign |
| Selector-cost 20261016 | 18 reconstructed histories, 324,000 warm-prefix calls, of which 252,000 measured | Separate warm microbenchmark, no extra full-workflow trials or policy tuning |

The new main protocol was frozen at **2026-10-15 18:47:31 UTC**. The parameter
choice was frozen at **18:49:58 UTC**, before any held-out worker started. Dates
refer to the same run across UTC and the local India date, 16 October. Local
manifest: Windows 11, Python 3.14.3, SQLite 3.50.4, Dolt 2.3.1, psutil 7.1.0,
12 logical / 10 physical CPUs and about 15.6 GiB RAM. Preparation recorded
about 1.90 GiB available RAM and active background processes. The study does
not claim idle-host, cold-cache or OS-causal conditions.

## Completed matrix

| Component | Cases | Warm-up queries | Measured queries | Independent unit |
|---|---:|---:|---:|---|
| Calibration | 12 | 144 | 504 | Two seeds × six profiles |
| Held-out | 18 | 216 | 756 | Three different seeds × six profiles |
| Sensitivity | 21 | 252 | 882 | Three seeds × seven staged variations/controls |
| Sampler diagnostic | 6 | 72 | 252 | Three off/on pairs of one history |
| Public data | 18 | 36 | 126 | Wine: three seeds; CO2: three repositories of one observed sequence |
| Scale | 18 | 36 | 126 | Two sizes × three seeds × three systems |
| **Total** | **93** | **756** | **2,646** | Cached queries within each repository are not independent histories |

Every case passed output-oracle and historical-state checks. Revon identity,
reverse, object-integrity and reopen checks ran outside timing. The portable
audit reimports the frozen source on a disposable copy and rederives histories,
semantic proofs, configuration/order accounting and summaries. It validates
internal consistency, not fresh elapsed times. The collection manifest seals
594 files; auxiliary analysis/package-init files are explicitly identified as
added after timing, not executed implementation changes.

## Calibration and held-out findings

The objective is the equal-weight mean across calibration cases of hybrid median
latency divided by the lower forced-path median. Scores were 1.337194 (T512),
1.048821 (T4096), 1.109850 (T16384) and **1.013502 (T65536)**. Selection used
only calibration. The 18 validation cases never select another policy.

| Held-out descriptive metric | T4096 | Calibration-frozen T65536 |
|---|---:|---:|
| Agreement with lower forced-path median | 12/18 | 18/18 |
| Mean latency / lower forced-path median | 1.100590 | 1.011537 |
| Largest such ratio for calibrated policy | — | 1.090457 |

All primary histories have at most 32,768 operations. T65536 therefore selects
log throughout: the result avoids early switching but does not establish a
useful adaptive crossover. No production threshold was changed. Ratios below
one can arise from independent noisy timings of equivalent selected paths.
The old Linux adverse selection and S3 dense-case inconclusiveness remain.

### Decision measurement correction

The retained `decision_probe_ms` uses the detached public changeset view, which
copies operations. Across all case/configuration medians it ranges from 0.2164
to 296.0638 ms; those are probe costs, **not pure selector overhead**. None was
subtracted from full diff latency or relabelled in the raw evidence.

The separate diagnostic extracts the actual production function AST up to the
selected-path dispatch, including validation, ancestry and internal count. Two
thresholds on the 18 already evaluated held-out histories use two warm-up and
seven measured batches of 1,000 calls. The median of 36 case/threshold medians
is **2.6735 µs**, range **1.6115–3.6778 µs**. Prefix decisions agree with actual
production dispatch; regression tests cover forward/reverse/identity and invalid
inputs. This post-campaign warm-prefix measurement excludes actual diff work and
detached-view copying; it is neither a cold-cache estimate nor causal overhead
to subtract. It does not retune the selector.

## Controlled sensitivity

Primary comparisons hold N=12,000, H=8, payload=32 and b8-d4 fixed while crossing
spread/repeated locality and C64/512/4096. The following are medians of three
forced-Merkle history medians, not confidence intervals or selected winners:

| Staged sensitivity | Median ms | Interpretation |
|---|---:|---|
| N24,000 | 47.8570 | Other base parameters fixed |
| H16/C256 | 40.1223 | Same 4,096 operations; interval and density trade off |
| Payload256 | 39.9497 | Other base parameters fixed |
| Geometry4x6 | 43.0035 | Same 4,096 leaves and history hashes |
| Geometry16x3 | 38.4996 | Same 4,096 leaves and history hashes |
| Hash-route C8 | 0.1736 | Matched low-density route-local case |
| Spread C8 control | 0.9028 | Same N/H/C/payload/geometry, different locality |

The same generated initial distribution is shared across seeds; mutation
histories differ. C8 is necessary for the nine-bit route bucket and has its own
matched control. This staged design does not estimate all factor interactions,
isolate H and C simultaneously at fixed operations, or identify a global geometry
optimum. Full per-seed results, forced log and all candidate hybrids are retained
in `selector.csv` rather than only the favourable cases.

## Public sources and workflow phases

Wine Quality: 6,497 rows, keys colour + physical row ordinal, canonical JSON with
source numeric strings, eight generated C64 correction batches per seed. Three
distinct generated histories. CO2: initial 812 rows; ten selected populated
snapshots, nine observed transitions; change counts 38,51,41,37,41,38,42,43,52.
Three repositories repeat this same observed sequence. Dataset licence,
acquisition-version URLs, hashes, exclusions and information lost are retained.

| Source / system | Median diff ms | Range of repository medians ms | Median persistent MiB |
|---|---:|---:|---:|
| CO2 / M | 0.6119 | 0.5625–0.6613 | 1.1914 |
| CO2 / H4096 | 0.3092 | 0.3022–0.3176 | 1.1836 |
| CO2 / Dolt CLI | 256.9769 | 251.8654–262.8907 | 0.1784 |
| Wine / M | 4.2811 | 4.2599–4.9640 | 10.8320 |
| Wine / H4096 | 2.2471 | 1.9558–2.3663 | 10.8125 |
| Wine / Dolt CLI | 296.7642 | 246.7498–302.8080 | 1.3598 |

Dolt phase medians: CO2 command256.0631/parse0.5014/canonical0.5035 ms;
wine288.4645/4.4452/3.2579 ms. Ratios of phase medians to total medians are
99.6% and 97.2%; separate phase medians need not sum exactly to total medians.
The command combines process launch, native work and JSON output. No pure
engine ranking or generic startup subtraction is justified. Dolt uses less
persistent space on these sources despite higher CLI diff latency.

## Repeated local scale

H=4/C64/payload32, three generated seeds per size/system. Diff values are medians
of seven cached queries per repository, then median/range across repositories.
Import/commit/checkout and worker telemetry are collected separately.

| Rows / system | Import median s | Diff median ms | Diff range ms | Worker RSS median GiB |
|---|---:|---:|---:|---:|
| 100k / M | 1.1163 | 5.6493 | 5.1488–7.6039 | 0.2485 |
| 100k / H4096 | 1.1085 | 1.0035 | 0.9124–1.0910 | 0.2418 |
| 100k / Dolt CLI | 1.6619 | 283.6535 | 243.3587–331.1855 | 0.2225 |
| 1M / M | 10.6141 | 33.6939 | 30.6280–56.8855 | 1.9389 |
| 1M / H4096 | 10.7379 | 1.0130 | 0.9521–1.0225 | 1.9253 |
| 1M / Dolt CLI | 11.2808 | 320.3003 | 306.3636–336.6454 | 0.9762 |

All million-row cases completed without OOM. This is a conditional observation
on this host, not an independent-machine test, population ranking or scaling law.
The old Linux n=1 table remains diagnostic and is never upgraded by these rows.
Whole-worker RSS includes oracle/history state and verification, so the lower
Dolt worker RSS is not a product-only memory comparison.

## Telemetry, failures and exclusions

- H4096 sampler on/off median ratios: 1.205767, 1.069649, 0.950414. Off always
  precedes on, so no causal sampling correction or negligible-overhead claim.
- Supported zero counters remain zero; missing means unavailable/unobserved.
  Windows OS process I/O is neither physical-disk traffic nor database logical
  reads. Sampling every 10 ms can miss short-lived descendants and peaks.
- **Premeasurement:** unexpected trailing CO2 columns caused an acquisition
  validation failure. The adapter was repaired to retain extra fields, and a
  regression test was added before protocol freeze.
- **Premeasurement:** the header-only CO2 revision was retained but excluded
  before timing; adjacent nonempty publications are linked explicitly. This is
  an exclusion of a publication outage, not evidence of real-world deletion.
- **Premeasurement:** native Dolt output equivalence passed, but Windows briefly
  locked a scratch directory on cleanup. A bounded retry fixed cleanup before
  the successful 77-test preflight gate.
- **Timed main campaign:** zero failures, zero timeouts, zero replacement runs,
  zero latency-based exclusions. **Prefix diagnostic:** all 18 histories and
  324 batches completed with correct decisions.
- **Document tooling:** the preferred LibreOffice renderer was unavailable on
  PATH. Word COM export succeeded; Windows backslash paths were required. A
  couple of orphan headings were repaired and the final pages re-rendered.
- The measurement and verification phase used no cloud, independent party,
  email or journal submission. Subsequent authorised Git publication and CI
  results are recorded separately in `docs/paper/REVISION_VERIFICATION_REPORT.md`.

## Reproduction and remaining gaps

See `REVIEW_REVISION_PROTOCOL.md`, the collection README, `paper/README.md` and
the package manifests. Internal audits are read-only on original evidence;
fresh timing reproduction always uses new output directories. The separate
claim register and skeptical reviewer audit describe the remaining novelty,
domain, machine, interface and inference limits. No substantive planned case
in the declared bounded revision is left pending. Broader independent research
validation remains open rather than silently described as complete.
