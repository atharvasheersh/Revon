# Response to the supervisor's review

Thank you for the detailed comments. We revised the manuscript around a bounded
systems contribution, added controlled local experiments and two public source
families, and retained the earlier adverse findings. The current title is
**Log and Merkle Differencing for Durable Structured Data Versioning**. The trie
is fixed; selection applies to differencing paths. Author details are unchanged.

The numbered responses below cover both the main review table and the later
novelty, dataset and benchmark-control follow-ups. IDs match
`REVIEW_RESPONSE_MATRIX.md`. These are responses to the comments, not statements
that the supervisor has approved the revision.

## R01 — Novelty and incremental engineering

Sections 1.2 and 2 now distinguish established mechanisms, their integration,
the tested policy and the evaluation contribution. The paper does not claim a
new Merkle index, new persistence primitive or feature parity with Dolt and
ForkBase. Table 2 compares the different abstraction levels. The contribution
is a prototype with two correct diff paths over one durable representation and
an auditable empirical study. Its algorithmic novelty remains limited.

## R02 — Scope of headline claims

We narrowed the title, rewrote the abstract and contribution list, scoped all
three research questions, and aligned the discussion, conclusion and limitations.
The text makes workflow claims rather than SQL-engine, concurrency or
production superiority claims. The claim register explicitly labels unsupported
claims, including universal optimal selection and independent reproduction.

## R03 — Separate calibration and validation

The existing Windows split was retained rather than described as absent. We
added a separate frozen local campaign: 12 calibration cases from two seeds and
18 validation cases from three different seeds. Primary row count, history
length, payload and geometry are fixed; locality and changes/commit are crossed.
Four candidate thresholds and the objective were declared before execution.
`frozen_selection.json` timestamps the choice before validation starts. See
§4.6, Appendix B, the protocol and case records.

## R04 — Adverse threshold outcomes and transfer limits

The old Linux case where T=16,384 selects slower Merkle remains unchanged in
Fig. 4 and Table 7. New calibration chooses T=65,536. It agrees with the lower
forced-path median in 18/18 held-out cases, versus 12/18 for T=4,096; mean
normalised latencies are 1.012 and 1.101. However, every tested primary interval
contains at most 32,768 operations, so the winner always selects log. Section
6.1 states that this does not establish useful adaptive switching or a global
crossover. We did not tune another policy after observing validation results.

## R05 — Workflow and engine boundaries

Table 5 gives the operation, correctness and resource boundaries. The new Dolt
adapter times native JSON-diff command execution, parsing and common output
construction separately. The command still combines launch, native execution
and JSON emission. We do not subtract a generic startup measurement or label
the residual storage-engine time. Sections 6.3 and 7 explain the resulting
limits on cross-system comparisons.

The main decision probe also includes copying through a detached public view.
We explicitly identify that limitation. A separate warm production-prefix
diagnostic on 18 histories and two thresholds records 252,000 measured calls:
median of case/threshold medians 2.674 µs, range 1.612–3.678 µs. It uses the
actual extracted production code and does not retune policy or subtract costs
from the frozen main campaign. See §6.2 and `evidence/selector-cost-20261016/`.

## R06 — Comparable controls and output semantics

Forced log, forced Merkle and all candidate hybrids query the same durable
repository and history within each selector case. Each returns the same sorted
key/old-value-hash/new-value-hash contract, checked against an independent
workload oracle. A real Dolt preflight confirms the phased adapter matches the
native adapter's actual output. Snapshot and Log-only controls remain in the
historical workflow study; no untested process-reuse interface is introduced.

## R07 — Methods readability

Section 4 now explains preparation, repository construction, timing, verification
and analysis as a connected workflow. Detailed historical timing/counter
definitions, source snapshots, seeds and case counts are in Appendix B and the
protocol. Appendix A explains access. The checksum-heavy historical table and
the new full count table are in the methods appendix rather than the main text.

## R08 — Algorithm, workflow and resources

The results and discussion separately treat same-representation diff behaviour,
complete API/CLI workflow costs, and whole-worker resources. RSS includes oracle
and history state; persistent bytes include metadata; neither is an isolated
algorithm cost. The main timing table and §8 repeat these boundaries where
needed for interpretation.

## R09 — Additional public sources

The new study adds UCI Wine Quality (6,497 records, CC BY 4.0) and the DataHub
NOAA-derived CO2 publication sequence (ODC-PDDL-1.0). Eighteen cases cover both
sources, three repositories/histories each and M/H/Dolt. Sources, licences,
checksums, keys, transformations and generated versus observed edits are
recorded in the acquisition manifest. Table 14 and Fig. 9 report all systems.

## R10 — Observed revision history

We acquired eleven file-changing CO2 revisions before timing. One header-only
publication failure was retained but excluded before protocol freeze. Ten
populated snapshots yield nine observed transitions, initially 812 records.
Dates are keys; order/formatting are discarded; unnamed trailing fields are
preserved. This is one filtered repository publication sequence, not NOAA
transaction logs or three independently sampled histories. Wine updates remain
explicitly generated.

## R11 — Software Heritage and fork-event suggestions

We checked the official Software Heritage graph documentation. It is a valid
candidate for larger sampled histories, but a bounded CSV publication history
allowed actual record changes without bulk graph acquisition on this host.
Repository fork events alone do not supply record-level mutations. We explain
this choice in §4.7 and the protocol rather than imply that fork counts validate
the diff selector.

## R12 — Controlled workload matrix

The primary design fixes N=12,000, H=8, payload=32 and b8-d4. It crosses two
localities with C=64/512/4,096 using two calibration and three held-out seeds.
The sensitivity design then changes N, interval, payload or geometry with
matched controls. H=16/C=256 matches the base's operation count, so interval and
density still trade off; this is a staged design, not a full factorial. The
generator documentation now accurately states its insert/delete mix.

## R13 — Payload, routing and geometry

Twenty-one sensitivity cases cover three seeds and seven variations/controls,
including payload=256, equal-capacity b4-d6/b16-d3 and matched hash-route/spread
C=8. Application-key adjacency is distinguished from shared hash-route locality.
Full outcomes are retained in `selector.csv`; §6.2 reports every variation.
These measurements do not identify a universally best geometry.

## R14 — Repeated scale observations

Eighteen separate local cases cover 100,000 and 1,000,000 rows, three generated
seeds and M/H/Dolt, with H=4/C=64/payload=32 fixed. Each repository has two
warm-ups and seven cached measured diff queries. Table 15 and Fig. 10 report
these local observations. The original single-run Linux million-row table is
unchanged and remains feasibility-only. Two sizes and three related histories
do not establish a general scaling law.

## R15 — Experimental units and uncertainty

We distinguish fresh worker/repository cases, generated seed histories, cached
query repetitions and repetitions of the same observed CO2 sequence. New
summaries report repository medians/IQRs and medians/ranges across three
histories or repositories, without population confidence claims. The historical
paired Linux intervals remain intact. Lower forced medians are noisy hindsight
references; exploratory sensitivity comparisons receive no significance claim.

## R16 — Observed correctness and complete accounting

All 93 planned cases completed: 3,402 observed diff queries, including 2,646
measured queries. Actual decoded output hashes and every historical state are
checked against separately constructed oracles. Revon additionally checks
identity/reverse requests, stored-object integrity and reopen behaviour outside
timing. Tests reject wrong output. Case/configuration/order checks and portable
frozen-source replay retain complete accounting. There were no timed failures
or performance-based exclusions.

## R17 — Zero/missing telemetry and monitor impact

The original Linux read-counter ambiguity remains disclosed. New telemetry and
tests distinguish supported zero from unavailable data. Counters cover the
worker and sampled children at 10 ms, including setup and verification. Windows
process I/O is not direct physical-disk traffic or DB logical activity. Three
sampler off/on pairs are reported; their fixed off-before-on order confounds
causal overhead estimation, so no correction is subtracted or negligible
overhead asserted.

## R18 — Environment and independence

Only the authorised Windows computer was used. The manifest records Windows,
Python 3.14.3, SQLite 3.50.4, Dolt 2.3.1, psutil 7.1.0, CPU topology, memory,
disk availability and background process names. Preparation found about 2 GiB
available RAM, which limits resource interpretation. The study is author-run;
we make no additional-Linux or independent-party reproduction claim.

## R19 — Structured related work

Table 2 supplements the original literature summary with representation/history,
diff/persistence, branches/queries and reproducibility/evaluation scope. Primary
papers and official sources support Dolt, ForkBase, Noms and Git4Data entries.
Git4Data is labelled a preprint; its results are not our measurements. “Not
evaluated” is kept distinct from “not supported.” Source checks are retained in
`REVIEW_REFERENCE_CHECK.md`.

## R20 — Research-question takeaways

Section 6.5 answers each revised RQ. Workflow trade-offs are observed with
interface confounds; unseen-history results favour log within the tested range
without proving adaptive switching; staged sensitivities show conditional
effects without a general geometry optimum. Dense-case uncertainty and the
adverse threshold result remain visible in the historical section.

## R21 — Consistent claims and limitations

The abstract, introduction, RQs, results, discussion, conclusion and limitations
now use the same campaign boundaries and narrower contribution. The separate
claim register maps hypotheses, metrics, evidence and limits, including explicit
unsupported and inconclusive claims. Historical Linux, repaired source and new
Windows timing rows are never pooled.

## R22 — Reproducibility and dissemination

The new versioned `Revon_Review_Revision_Reproducibility_20261016.zip` retains the
new collection, exact executed sources, raw observations, acquisition metadata,
analysis and audit tools. It has a separate package manifest. The old Linux
ZIP is unchanged. Manuscript links follow the repository and `main`, as
requested; exact source identities remain inside evidence. Git publication is
separately authorised, with status in the verification report. No journal-hosted
supplement is claimed.

## R23 — Publication artifacts and visual checks

The Springer PDF and DOCX are updated together in the selected reference layout.
The original eleven numerical tables and seven figure assets are preserved,
with table/reference renumbering checked. Six tables, three evidence-derived
figures and two dataset references are added. Archived versions remain intact.
Every final PDF and Word-rendered page is checked; Word pagination may differ.
The verification report records actual final counts and any layout repairs.

## R24 — Full coverage and final audit

The response matrix traces all 24 consolidated requests, including the later
follow-ups. The experiment report records completion, preflight problems,
exclusions and resource limits. The final skeptical audit separates stronger
controls and broader evidence from limited novelty, single-host inference,
interface confounds and the unestablished adaptive-switching benefit. Passing
tests and a longer manuscript do not imply Q1 acceptance or scientific approval.
