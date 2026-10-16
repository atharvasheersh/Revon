# Claim-to-evidence register

Current title: **Revon: Log and Merkle Differencing for Durable Structured Data Versioning**.
The index geometry is fixed. “Adaptive” describes a diff-path decision, not an
adaptive trie, novel persistence mechanism or proven optimal strategy.

| ID / claim | Status | Evidence and location | Interpretation limit |
|---|---|---|---|
| C01: Revon exposes log and hash-pruned Merkle diff over the same durable representation | Established implementation property | `versioned_db.py`, `sqlite_store.py`, `experiments/adapters.py`; core correctness tests; paper §§3, 4.2 | Established building blocks are reused; integration is incremental engineering, not invention of Merkle tries or content addressing |
| C02: the evaluated Revon paths produce equivalent encoded-value diffs | Established for retained tests and histories | `tests/test_review_revision.py`; `campaign/cases/*/result.json` observed/oracle hashes; paper §4.4 | Tests and internal audits are not a proof over every input or independent reproduction |
| C03: eight of nine Linux paired M/H intervals favour H; dense S3 is inconclusive | Conditional historical result | `evidence/linux-validation-20261008/paired_uncertainty.csv`; unchanged Fig. 3 / Table 6 | Seven timings on fixed histories and one VM; no population generalisation; not all cases favour H |
| C04: the frozen Linux T=16,384 policy can choose a slower path | Established adverse observation | Same bundle, threshold rows; unchanged Fig. 4 / Table 7; publication gate checks all seven pairs | Preserved counterexample; a count alone does not establish the fastest path |
| C05: new calibration transfers to the specified held-out histories | Conditional descriptive result | `review-revision-20261016/campaign/frozen_selection.json`, `selector.csv`, `analysis.json`; §6.1, Table 13, Fig. 8 | 18 held-out cases = three different seeds × six profiles, not 18 independent populations; observed timing medians are noisy |
| C06: a useful general adaptive crossover or optimal selector has been established | **Unsupported** | Largest candidate T=65,536 exceeds every primary interval (max 32,768 operations) | The winner selects log throughout; 18/18 path agreement does not demonstrate switching benefit; production defaults unchanged |
| C07: selection improved the held-out descriptive latency reference | Conditional descriptive result | Mean normalised latency 1.011537 calibrated versus 1.100590 T4096; §6.1 | Normaliser is the lower forced-path median, not a deployable oracle; some ratios below one reflect noise; no tuning on held-out results |
| C08: workload structure/geometry affects costs on controlled cases | Conditional sensitivity result | 21 new sensitivity cases, `selector.csv`, `summary.csv`; §6.2; retained Linux geometry supplement | Three seeds; staged controls, no full factorial or universal geometry optimum; H and C trade off at fixed operation count |
| C09: public coverage extends beyond TLC | Established dataset coverage | UCI Wine Quality and DataHub CO2 acquisition manifest; 18 cases; §4.7, §6.3, Table 14, Fig. 9 | Wine edits are generated. CO2 repeats one filtered observed publication sequence, not three independent histories or NOAA transaction logs |
| C10: repeated million-row observations exist | Established local feasibility and conditional workflow comparison | 18 scale cases at 100k/1M rows × three seeds × M/H/Dolt; Table 15, Fig. 10 | New Windows campaign only; old Linux n=1 remains diagnostic. Shared starting distribution, cached queries, two sizes, no general scaling law |
| C11: Revon outperforms Dolt's storage engine or SQL system generally | **Unsupported** | Dolt command/parse/canonical phases in raw rows; paper Table 5 and §6.3 | API/CLI boundaries differ; native command interval includes launch and execution. No generic overhead subtraction, query/concurrency parity or general ranking |
| C12: resource measurements isolate tree-operation memory, CPU or disk activity | **Unsupported** | `campaign/cases/*/telemetry.json`, manifest; §6.2 and limitations | Whole-worker setup/oracle/verification included. 10 ms sampling can miss processes/peaks. Windows OS process I/O is neither physical-disk nor DB logical reads |
| C13: zero and unavailable counters are distinct in new evidence | Established counter contract | `aggregate_io`, regression tests, retained telemetry; old supplement preserves zero | Does not repair ambiguity in original Linux counters or establish no physical I/O |
| C14: sampler overhead is causally identified | **Inconclusive** | Three off/on pairs; H4096 ratios 0.950–1.206; `monitor.csv` | Off precedes on; order/cache/background confounded. No subtraction or assertion of negligible overhead |
| C15: persistent bytes and worker RSS show a single universally best system | **Unsupported** | Tables 9, 14, 15 and raw resource records | Different representations/metadata, measurement conditioning and worker scope; latency, footprint and RSS trade off |
| C16: the new run is Linux or independent-party reproduction | **Unsupported** | Windows environment manifest, author-run execution | Additional author-run evidence only; old Linux and new Windows are never pooled or treated as an OS-causal experiment |
| C17: archived records are internally consistent and replayable without rewriting originals | Established after the recorded gates pass | `tools/check_review_campaign.py`, collection/package manifests and final verification report | Regenerates histories, oracles and summaries; does not independently reproduce elapsed timings |
| C18: related systems have the documented capabilities in Table 2 | Primary-source supported scope comparison | `REVIEW_REFERENCE_CHECK.md`; §§2.3–2.5 | Noms/ForkBase/Git4Data not benchmarked here. “Not evaluated” is not “not supported”; preprint claims retain their status |

## Research questions and testable expectations

| RQ | Hypothesis / expectation | Experiment and metric | Result and limit |
|---|---|---|---|
| RQ1: complete workflow trade-offs and API/CLI limits | Latency, footprint and whole-worker resources can favour different configurations | Linux workflow/control campaigns; new public/scale runs; import/commit/diff/checkout, bytes, RSS, Dolt phase timers | Trade-offs are measured; engine-only superiority is not identified |
| RQ2: unseen-history selector transfer | A calibration-frozen scalar rule may avoid premature switching on held-out profiles | Two calibration seeds, three disjoint validation seeds; forced-path agreement, normalised latency; separately timed detached-view probe and warm production-prefix diagnostic | T65536 matches faster forced medians 18/18 but always selects log in tested range; adaptive switching remains unestablished |
| RQ3: workload and fixed geometry sensitivity | Changed locality, density, payload, interval or geometry can change work even at similar operation counts | Primary fixed N/H/payload/geometry matrix plus seven matched sensitivity variants × three seeds | Conditional sensitivity, not independent identification of every interaction or an optimal layout |

“Established” means supported within the stated implementation or collected
sample. It does not mean mathematical novelty, universal correctness, journal
acceptance, detector certification or third-party validation.
