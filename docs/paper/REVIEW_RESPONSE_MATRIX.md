# Review response matrix

Baseline: `COMMENTS (1).docx`, including the novelty, datasets and workload-control follow-up sections. Current manuscript: `paper/Revon Research Paper Springer Nature.docx` and PDF. New experiments are authorised on this Windows computer only. Git publication was separately authorised on 16 October 2026; cloud spending and journal submission remain outside scope.

Status terms: not started; in progress; implemented but unverified; verified complete; blocked. A limitation paragraph alone does not complete a request for new evidence.

| ID | Comment location and request | Baseline finding and required work | Deliverable and acceptance check | Status |
|---|---|---|---|---|
| R01 | Opening; novelty row; novelty follow-up: distinguish original contributions from engineering | Fixed trie, addressed log and SQLite are established mechanisms; sharpen contribution at the selection/evaluation level | Contributions and claim register distinguish algorithm, policy, implementation and evidence; primary-source comparison | Verified complete |
| R02 | Scope row; what to avoid: bound title, abstract, highlights and conclusion | Existing text is cautious but RQ1 is broader than controlled evidence | All headline claims map to audited evidence; no generic Dolt/SQL/production superiority | Verified complete |
| R03 | Experimental design; threshold follow-up: separate calibration and validation histories | Existing 42-repository held-out study exists; local pilot confounds rows/history/locality | Audit old split; new disjoint-seed controlled matrix, frozen selection before validation with recorded timestamps | Verified complete |
| R04 | Threshold validity and adverse outcomes | Largest historical candidate wins; Linux T16384 chooses slower path at 32768 | Preserve old result; report held-out regret, path agreement and failures for a newly labelled policy | Verified complete |
| R05 | Comparative evaluation: distinguish engine and workflow costs | Revon API and Dolt CLI have different boundaries | Timing-boundary table plus instrumented subprocess/execution and parsing phases; no causal overhead subtraction | Verified complete |
| R06 | Comparative controls: same representation and contract | Durable Revon forced-log/M/H share one representation; cross-system differences remain | Tests of observed diff equivalence; controls explicitly identified; process reuse only if separately evaluated | Verified complete |
| R07 | Method transparency: readable main methods and detailed appendix | Existing methods are dense; reproduction appendix contains availability, not full protocol | Short workflow narrative and separate methods appendix covering protocol, counters and analysis | Verified complete |
| R08 | Interpretation: algorithm, workflow and system resources | Full-worker telemetry is already qualified but scattered | Distinct results/discussion explanations and metric scope table | Verified complete |
| R09 | Generalisability; dataset follow-up: 1–2 new public sources | Only TLC in Linux public-data comparison, generated edits | Two additional source families with acquisition/licence/hash metadata, independent campaign and retained raw results | Verified complete |
| R10 | Dataset follow-up: naturally occurring revision histories | No observed record-level history in current paper | Bounded observed public revision sequence; documented mapping, additions/deletions/ordering, no invented edits called observed | Verified complete |
| R11 | Dataset suggestions: assess Software Heritage/fork events | Suggestions are exploratory, not established experiments | Explain chosen manageable sources; do not equate repository forks to record mutations | Verified complete |
| R12 | Workload table: control row count, density, locality and interval independently | Existing robustness profiles differ in multiple factors | Frozen staged design holding rows/history fixed for locality, documenting independent seeds and operation counts | Verified complete |
| R13 | Workload table: payload, routing and trie shape | Equal-capacity geometry has prior one-workload evidence | New controlled payload/geometry sensitivity or explicit measured coverage; distinguish lexical and hash-route locality | Verified complete |
| R14 | Scale recommendation: repeated trials before scaling claims | Linux million-row observations are n=1 | Repeated separate local scale runs if feasible; do not retrofit Linux or claim independent histories from repetitions | Verified complete |
| R15 | Repetitions and uncertainty | Fixed-history timing intervals, no population-level inference | Predeclared units, paired summaries, independent-history aggregates and failure policy | Verified complete |
| R16 | Measurement/correctness: actual observations and retained failures | Legacy Dolt flags did not preserve outputs; repaired campaign does | New observed outputs/state hashes checked against oracle; negative controls and complete accounting | Verified complete |
| R17 | Telemetry: zero/missing and sampling scope | Primary Linux read counters conflate zero with missing; later supplement repaired | Preserve old files; verify new zero/missing semantics, worker scope and sampler impact | Verified complete |
| R18 | Environment: additional machine vs independent party | Linux VM was author-run, not third-party reproduction | Environment manifests for new Windows runs; no Linux or independent-reproduction claim | Verified complete |
| R19 | Related work row and novelty follow-up: structured capabilities | Current Table 1 is a compact comparison, requires expansion/qualification | Primary-sourced table covers representation/history/diff/persistence/branches/queries/reproducibility, not-evaluated distinguished | Verified complete |
| R20 | Writing row: takeaways and RQ1–RQ3 | Existing discussion has RQ prose, no concise takeaways | Takeaways answer each revised RQ with established, inconclusive and open findings | Verified complete |
| R21 | Claims/limitations across full manuscript | Historical, repaired and new campaigns must remain separate | Consistent abstract/introduction/results/discussion/conclusion/limitations and claim-to-evidence register | Verified complete |
| R22 | Reproducibility and dissemination | GitHub archive exists; current links intentionally follow main | Versioned revision supplement and valid checksums; current repository links; frozen sources retained; no journal-hosting claim | Verified complete |
| R23 | Presentation and artifacts | Current reference layout and author block must survive | Updated matching DOCX/PDF, preserved correct historical figures, new evidence-derived additions, every rendered page checked | Verified complete |
| R24 | Complete response and final skeptical review | All requests must be individually accounted for | Supervisor response, experiment report, matrix with exact artifact paths, final audit and honest unresolved items | Verified complete |

## Initial cross-area audit

- Read the complete comments and follow-up recommendations before algorithm changes.
- Existing held-out evidence is documented in `docs/experiments/THRESHOLD_VALIDATION.md`; do not misreport calibration as entirely absent.
- Existing pilot limitations are documented in `docs/experiments/THRESHOLD_ROBUSTNESS_PILOT.md`.
- Existing Linux campaign and supplement remain historical author-run evidence; this revision will use the authorised Windows host.
- The previous publication gate, exact archived-format checks and current layout must be preserved or extended, not bypassed.
- The unrelated untracked file `earch manuscripts… &&` is outside this revision.

## Completion evidence and remaining limits

Paths below are relative to the repository root. `campaign/` abbreviates
`evidence/review-revision-20261016/campaign/`. Main campaign evidence was sealed
before final documentation. The separate prefix diagnostic does not alter it.
“Verified complete” means the bounded requested revision and its listed checks
were completed; it does not imply that every broader research limit is resolved.

| ID | Actual manuscript / implementation change | Inspected evidence and verification | Precise remaining limitation |
|---|---|---|---|
| R01 | Title, §§1.2, 2.3–2.5, 7–9; established mechanisms separated from integration/policy/evaluation | `docs/paper/CLAIM_EVIDENCE_REGISTER.md`, `REVIEW_REFERENCE_CHECK.md`; actual core and primary sources reviewed | Incremental prototype contribution; no new index or proven adaptive advantage |
| R02 | Abstract, RQs, contributions and conclusion rewritten consistently | Current DOCX/PDF; `tools/check_review_manuscript.py` freezes reviewed text and historical evidence; claim register C01–C18 | No engine, SQL, concurrency, production or Q1-acceptance claim |
| R03 | §4.6, Appendix B; disjoint 2 calibration / 3 validation seeds, fixed primary N/H/payload/geometry | `campaign/protocol.json`, `manifest.json`, `frozen_selection.json`, per-case `started.json`; frozen-source audit checks ordering | Small seed population, generated histories and one host |
| R04 | §§5.2, 6.1, 8; original failure kept; new threshold labelled separately | Original Linux threshold rows/Fig.4/Table7 unchanged; `campaign/selector.csv`, `analysis.json`; 18/18 versus 12/18 agreement | T65536 always log in tested primary range; no optimal crossover |
| R05 | Table5, §§6.2–6.3, 7; native command/parse/canonical phases; probe caveat | `experiments/review_revision.py` PhasedDolt, raw rows; separate `experiments/selector_cost.py`, `evidence/selector-cost-20261016/`, prefix checker | No causal native-startup isolation; warm prefix is not cold-cache overhead or subtraction |
| R06 | §4.2, §4.4; same repository/encoded-value contract; Snapshot/Log-only retained | `tests/test_review_revision.py`, actual native Dolt preflight, per-case observed diff/state hashes; original Table12 | Cross-system interfaces/features still differ; no process-reuse experiment claimed |
| R07 | Main §4 shortened; checksum/count tables and detailed protocol moved to Appendix B | Current Tables16/17, Appendix A/B; `tools/revise_review_manuscript.py`; rendered main methods and appendices checked | The paper remains long, with technical reproducibility detail retained |
| R08 | Table5, §§6.2–6.4, 7, 8 distinguish operation/interface/worker scope | `campaign/summary.csv`, public/scale telemetry; `REVIEW_REVISION_RESULTS.md` | Whole-worker counters include oracle/setup/verification; bytes include representation metadata |
| R09 | §§4.7, 6.3; two additional public families, all three systems | `public_sources/acquisition.json`, raw CO2/wine files, 18 public cases, Table14/Fig9 | Wine generated; CO2 one observed sequence, no domain-general claim |
| R10 | Explicit observed snapshot mapping, exclusions, unnamed fields, information loss | `experiments/review_revision_data.py`, frozen raw snapshots, parser regression tests, regenerated state proofs | Publication history filtered before timing; not NOAA transaction history or independent samples |
| R11 | §4.7 and protocol explain chosen bounded source | `REVIEW_REFERENCE_CHECK.md`, Software Heritage official graph/schema sources, retained CO2 history | Software Heritage not executed; fork events rejected as a record-mutation surrogate |
| R12 | §4.6, staged primary/sensitivity design; generator mix documentation corrected | `campaign/protocol.json`, `selector.csv`, `tests/test_review_revision.py` split/control/mix tests; `experiments/workloads.py` docstring | H/C trade off at fixed operations; not a complete factorial |
| R13 | §6.2; three-seed payload/geometry and matched route/spread C8 controls | All 21 sensitivity results in `campaign/cases/`, `selector.csv`; equal-capacity geometry history hashes agree | Routing test has low C; no universally best geometry or interaction estimate |
| R14 | §§4.7, 6.4; repeated separate local scale runs | 18 `scale-*` case results, `public_scale.csv`, Table15/Fig10; all million-row cases complete | Two sizes, three generated histories sharing initial distribution; old Linux n=1 unchanged |
| R15 | §4.4, §4.6, new captions and limitations name units and descriptive ranges | `campaign/raw_results.csv`, `summary.csv`, `selector.csv`, analysis code; original paired uncertainty unchanged | No population CI or multiple-testing significance; noisy hindsight denominator |
| R16 | §4.4, Appendix B; observed outputs, all states, identity/reverse/integrity/reopen; negative controls | 93 cases / 3,402 queries; `campaign/audit.json`; portable source replay; core and publication tests | Internal semantic/hash consistency is not independent timing reproduction |
| R17 | §6.2/Table5/§8; zero versus missing, counter scope and sampler diagnostic | `aggregate_io`, zero/missing regression, six monitor workers, `monitor.csv`, `telemetry.json` | Off before on confounds causal overhead; 10ms sampling; OS I/O not physical/logical DB reads |
| R18 | §§4.1, 8; Windows-only author-run classification | `campaign/manifest.json`: runtime/CPU/memory/disk/background processes; frozen source hashes | No new Linux, idle-host, OS-causal or independent-party claim |
| R19 | §2.5, Table2, 33-reference bibliography | Primary-source checks, source-capability table, citation identity validator | ForkBase/Noms/Git4Data not benchmarked; Git4Data remains a preprint |
| R20 | §6.5 answers revised RQ1–RQ3 | Current paper and `CLAIM_EVIDENCE_REGISTER.md` RQ mapping | Switching benefit and broad generalisation remain open; adverse findings visible |
| R21 | All headline sections and scope/limitations aligned | Claim register, full-text/source audit, preserved historical numeric/figure gate | Evidence families never pooled; no unsupported superiority inferred |
| R22 | Appendix A, availability, README/reproduction and separate revision archive | `tools/check_review_campaign.py`, `check_selector_cost.py`, `check_review_package.py`; collection/package manifests | Authorised Git publication tracked in verification report; no journal-hosting or independent timing claim |
| R23 | Matched current pair, old 11 tables/7 images preserved, 6 tables/3 figures/2 refs added | 27 PDF + 28 Word-rendered pages; 17 tables/10 figures/33 refs; model/numeric/visual checks, old-pair backup | Word pagination differs; author approval remains separate |
| R24 | Complete matrix, point-by-point response, claim register, results and skeptical audit | `REVIEW_RESPONSE.md`, `CLAIM_EVIDENCE_REGISTER.md`, `FINAL_REVIEW_AUDIT.md`, experiment report and `REVISION_VERIFICATION_REPORT.md` | Research weaknesses remain explicit; no email/submission; authorised Git publication tracked separately |

## Final coverage walk-through

The full reviewer document, including all novelty, datasets and workload-variable
follow-ups, was reread. The suggested numbered citations were treated as
unverified suggestions; technical claims use the checked primary sources.
Reviewers' suggestions to add evidence are met by actual new measurements,
not future-work paragraphs. Software Heritage is a documented alternative
selection decision, not an omitted mandatory dataset. No request in the
declared bounded revision has an unexecuted experiment substituted as completed.
The final verification report contains the actual gate outcomes and baseline
preservation check; broad independent research validation remains open.

## Follow-up to the second verification review

Three defects were reproduced and repaired: required figures now use versioned
publication paths; calibration scores/winner/tie-break/chronology are checked
independently; and the prefix diagnostic is compared with exact retained
production and benchmark sources. An ignored local review document was also
excluded. Twenty-five isolated regression tests cover these changes, including
strict-local versus explicitly portable historical baseline verification. Scientific
measurements and canonical manuscript bytes remain unchanged. See
[REVIEW_REMEDIATION.md](REVIEW_REMEDIATION.md) for chronological work and the
[current verification report](REVISION_VERIFICATION_REPORT.md) for local and
clean-snapshot outcomes. Earlier local success alone did not establish clean
checkout portability; publication status follows the current report.
