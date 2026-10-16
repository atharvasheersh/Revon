# Local review revision, 2026-10-16

This collection is a new author-run Windows campaign. It must not be pooled
with the earlier Linux timing rows. All 93 planned workers completed, producing
3,402 checked queries: 756 warm-ups and 2,646 measured queries. The original
Linux collections and archive remain separate and unchanged.

## Contents and integrity

- `baseline.json`: pre-edit hashes of 1,329 protected historical files.
- `preflight-tests.log`: the successful 77-test gate before measurement.
- `public_sources/acquisition.json`: fixed acquisition versions, raw-file
  checksums, source licences and transformations.
- `campaign/protocol.json`: the full prespecified case list and analysis rules.
- `campaign/manifest.json`: actual runtime, machine conditions and seven
  executed-source hashes. Available RAM was about 2 GiB at preparation; this
  was not an idle laboratory machine.
- `campaign/frozen_selection.json`: calibration scores and the parameter freeze
  before any held-out worker began.
- `campaign/cases/`: all started records, actual query/state observations and
  worker telemetry. Repositories were scratch state and are not redistributed.
- `campaign/raw_results.csv`, `summary.csv`, `selector.csv`, `public_scale.csv`,
  `monitor.csv`, `analysis.json`: derived numerical results.
- `SHA256SUMS.json`: exact collection bytes, excluding this checksum file and
  interpreter caches. Checksum agreement is integrity evidence, not proof that
  elapsed timings are independently reproduced.

The seven experiment/implementation files under `campaign/source/` were copied
before measurement and match the manifest. `experiments/__init__.py` and
`experiments/analyze_review_revision.py` are auxiliary package/analysis files
copied after measurement for portable replay; they were not timed implementation
files. Their identities are covered by the collection manifest.

## Read-only verification

From a full repository or the revision ZIP's extracted root, install
`requirements-publication.txt`, then run:

```bash
python tools/check_review_campaign.py
```

This imports the archived source in a fresh interpreter, works on a disposable
copy, maps only the old absolute public-data directory to the retained local
source directory, reconstructs histories and semantic oracles, checks every
trial/configuration/order and rederives the summaries. It does not need Dolt,
does not rerun timed operations, and must leave collected bytes unchanged.

Do not run the writing auditor directly on the collected directory. For a new
timing experiment, follow `docs/experiments/REVIEW_REVISION_PROTOCOL.md`, acquire
the exact public files into a new directory and use a new campaign output.
Python 3.14.3, psutil 7.1.0 and Dolt 2.3.1 were the measured runtime/toolchain.
Changing platform or interpreter produces another campaign.

## Source attribution and exclusions

Wine Quality: Cortez, Cerdeira, Almeida, Matos and Reis (2009), UCI Machine
Learning Repository, DOI https://doi.org/10.24432/C56S3T, CC BY 4.0
(https://creativecommons.org/licenses/by/4.0/). The retained archive contains
red and white tables. We combine 6,497 rows and generate quality-field updates;
these updates are not observed specimen histories.

CO2: DataHub contributors, https://github.com/datasets/co2-ppm, NOAA-derived
Mauna Loa monthly publication data. The retained versioned `datapackage.json`
declares ODC-PDDL-1.0 (https://opendatacommons.org/licenses/pddl/1-0/).
Eleven raw CSV revisions were acquired. `co2-03.csv` is header-only and was
excluded before protocol freeze. Ten populated snapshots yield nine transitions.
Dates are keys; row order and formatting are discarded. Unnamed trailing fields
are retained as `_extra_0`, etc., without scientific interpretation. The sequence
is an observed repository publication history, not NOAA transactional history.
Three fresh repositories repeat this same sequence.

An initial acquisition preflight rejected the unexpected trailing CSV fields;
the adapter was corrected to preserve them before tests and timing. A native
Dolt preflight passed output equivalence but exposed a brief Windows directory
lock during cleanup; bounded cleanup retry was added before the successful
77-test gate. Neither is a discarded timed result. No case failed after protocol
freeze, no latency-based exclusion or replacement run occurred, and no extra
cloud resource was used.

The monitor diagnostic runs off before on, so its ratios confound sampling,
order, background load and cache. They cannot be subtracted as causal overhead.
Whole-worker RSS/CPU/I/O include setup and verification; Windows process I/O is
neither direct physical-disk traffic nor database logical reads. Zero and missing
counters remain distinct. Three-seed ranges are descriptive, not confidence
intervals over a population of systems or machines.
