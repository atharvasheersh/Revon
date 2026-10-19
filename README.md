# Revon

[![CI](https://github.com/atharvasheersh/Revon/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/atharvasheersh/Revon/actions/workflows/ci.yml)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Revon is a Python research prototype for durable structured key/value
versioning. It stores content-addressed versions in a fixed-depth Merkle hash
trie backed by SQLite, and compares versions through operation-log aggregation
or hash-pruned Merkle traversal. Revon-H selects a diff path using an
operation-count threshold over the requested history interval.

- **Version and recover data:** atomic batch commits, retained history and
  historical checkout in memory or a durable SQLite repository.
- **Compare the diff paths:** forced log, forced Merkle and threshold selection
  over the same stored representation.
- **Inspect correctness and costs:** semantic oracles, recorded environments,
  frozen protocols, raw observations and reproducibility tools.
- **Explore the implementation:** dependency-free Python demos and a local
  REST API, with [architecture documentation](docs/architecture/).

The scope is single-writer, linear-history versioning. Branch references,
merging, concurrent writers and a general SQL query engine are outside the
implemented scope. The experiments compare bounded versioning workflows;
they do not establish a generally faster storage engine or an optimal
adaptive switching policy.

Revon is licensed under the [Apache License 2.0](LICENSE).

[Run the demo](#run-the-demo) · [Open the paper](#paper-and-reproducibility) ·
[Run the tests](#run-the-tests) · [Use the API](#run-the-backend-api)

## Paper and reproducibility

**Revon: Log and Merkle Differencing for Durable Structured Data Versioning**

Read the current manuscript as a
[PDF](paper/Revon%20Research%20Paper%20Springer.pdf) or
[editable DOCX](paper/Revon%20Research%20Paper%20Springer.docx).
It is an unpublished manuscript prepared in the retained Springer reference
layout, written as a first submission with the experiments presented directly.
See the [paper guide](paper/README.md) for formats, rebuilding and
verification; earlier Discover Computing and IEEE exports remain under
[`paper/previous versions/`](paper/previous%20versions/).

### Evaluation evidence

The Linux and Windows campaigns were conducted by the authors and are analysed
separately. Their execution counts, experimental units and environments differ.

| Campaign | Recorded scope | Evidence |
|---|---|---|
| Linux primary | 516 executions, including warm-ups, measured trials and scale diagnostics | [Protocol, sources and results](evidence/linux-validation-20261008/) |
| Linux supplement | 72 geometry/telemetry executions | [Supplement records](evidence/linux-final-supplement-20261008/) |
| Windows evaluation | 93 cases, each in a fresh worker process; 3,402 checked queries, including 756 warm-ups and 2,646 measured queries | [Frozen campaign](evidence/review-revision-20261016/) and [experiment report](docs/experiments/REVIEW_REVISION_RESULTS.md) |
| Windows decision-prefix diagnostic | 18 reconstructed histories; 252,000 measured warm-prefix calls, distinct from full-workflow trials | [Diagnostic records](evidence/selector-cost-20261016/) |

The Windows evaluation uses disjoint calibration and validation histories,
controlled sensitivity experiments, Wine Quality and CO2 public sources, and
repeated runs at 100,000 and 1,000,000 records. Wine corrections are generated;
CO2 uses one observed publication sequence repeated across repositories.
The calibration-frozen threshold T=65,536 selects log throughout the tested
primary operation range. It does not demonstrate a useful adaptive crossover.
Revon's in-process API and Dolt's CLI also have different cost boundaries.

Download the [Windows reproducibility archive](paper/Revon_Review_Revision_Reproducibility_20261016.zip)
and the [Linux reproducibility archive](paper/Revon_Linux_Reproducibility_Supplement.zip)
for executed sources, protocols, semantic checks and raw results. Internal
integrity checks do not reproduce elapsed times or constitute reproduction by
an independent team. Timing rows from different campaigns must not be pooled.
The [claim register](docs/paper/CLAIM_EVIDENCE_REGISTER.md),
[response matrix](docs/paper/REVIEW_RESPONSE_MATRIX.md) and
[verification report](docs/paper/REVISION_VERIFICATION_REPORT.md) document the
supporting evidence and remaining limitations.

Earlier evidence is retained with its original scope:

- The [corrected Windows workflow comparison](evidence/paper-corrected-issues13-17-counterbalanced-final-20260923/)
  contains 540 executions: 120 warm-ups and 420 measured runs. It separates
  Dolt SQL and CSV import workflows and balances model order across trials.
- The [corrected trie sensitivity study](evidence/trie-sensitivity-issues8-20260923/)
  contains 10 warm-ups and 35 measured runs.
- The [original run erratum](evidence/paper-final-20260824/ERRATA.md) identifies
  Dolt diff fields that did not establish observed semantic correctness.

The `output/` directory is reserved for generated local runs and is ignored by
Git. Personal presentation and review material is not part of the repository.

## Maintain publication artifacts

To run the same publication checks as CI, install the small pinned verification
dependency set. These commands read committed artifacts without regenerating
the manuscripts or modifying collected evidence:

```powershell
python -m pip install -r requirements-publication.txt
python -m unittest discover -s tools/tests -v
python tools/check_final_paper.py
```

The publication gate checks the archived Discover Computing and IEEE formats
against their packaged model. It also checks the current Springer manuscript's
numerical tables, figures and references, current GitHub link targets, and
PDF/DOCX agreement for availability and reproducibility text. Together these
checks cover PDF structure/bounds, collection/package/source
hashes, frozen execution order, historical correctness proofs, raw summaries,
paired intervals and the adverse frozen-threshold finding. It needs neither
ignored `output/` files nor private cloud download archives. Visual review and
corresponding-author approval remain separate from this automated gate.
The gate also imports the frozen Windows campaign source on a disposable copy,
regenerates semantic histories, rederives the numerical summaries and checks the
Windows archive. It does not rerun timing. The [verification report](docs/paper/REVISION_VERIFICATION_REPORT.md)
records local commands, layout checks and remaining limits.
Calibration is additionally recalculated from raw calibration records, including
the winner, tie-break and freeze chronology. The selector diagnostic checks its
archived production source and extracted function AST. Required figure assets
are versioned under `paper/review-assets/figures/`; package construction fails
when any is missing. Neither check needs ignored local output.

The architecture PDFs can be rebuilt separately:

```powershell
python tools/build_architecture_pdfs.py
```

The older manuscript builders target superseded evidence and must not be used
to overwrite the current papers. The application core uses only the Python
standard library. Full benchmark, dataset and figure-generation dependencies
remain pinned in `requirements.txt`; they are not needed for the CI checks.

## Run the demo

Requires Python 3.10 or newer and no third-party packages.

```powershell
python -m examples.demo
```

The output shows the root for each version, new/reused nodes, the sharing
percentage, changed keys, and how many identical subtrees the diff skipped.

For a self-checking CLI demonstration that also proves the incremental root is
identical to a clean full rebuild:

```powershell
python -m examples.revon_cli_demo --show-changes
```

Use `--rows`, `--updates`, and `--hybrid-threshold` to change the workload and
observe when Revon-H selects Log or Merkle differencing.

## Verify durable SQLite persistence

Run the complete persistence flow:

```powershell
python -m examples.revon_sqlite_demo --database revon_demo.revon.db --reset
```

The command generates two deterministic CSV states, imports them as versions,
closes the SQLite writer, and launches a separate Python process that:

- reopens the repository;
- verifies every node, changeset, and commit against its content hash;
- checks that `HEAD` references the latest commit;
- checks out both versions; and
- reproduces the version diff.

SQLite is the atomic durable object container. The fixed-depth Merkle trie,
content-addressed commits, and Revon-H diff selection remain Revon logic.

## Run the tests

The core needs no third-party packages; telemetry regression tests require
`psutil`. CI runs this suite on Python 3.10 and 3.14:

```powershell
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```

## Run the backend API

Start the dependency-free local REST API:

```powershell
python -m revon_api
```

It supports repository creation/opening, JSON or CSV import, atomic mutation
batches, history, checkout, structured comparison, and storage/diff metrics.
The health check is `http://127.0.0.1:8000/api/health`; the OpenAPI index is
`http://127.0.0.1:8000/api/openapi.json`.

See [the backend API guide](docs/api/BACKEND_API.md) for endpoint contracts,
examples, frontend CORS configuration, and the current local-only security
boundary.

## Compare the three versioning models

```powershell
python -m experiments.benchmarks
```

This compares a full-snapshot state model, an operation-log model, and the
Revon-H hybrid model. It reports median incremental commit time, median diff
time, logical serialized storage, and how much work each diff examines.

For a shorter sample run:

```powershell
python -m experiments.benchmarks --sizes 1000,10000 --versions 5 --changes 10
```

## Run the final research comparison

The final reproducible harness compares Snapshot, Log-only, the forced-Merkle
ablation, Revon-H, and a real Dolt CLI adapter. It records raw trial CSV,
summary statistics, a run manifest, storage, memory method, work examined, and
correctness against a shared deterministic oracle.

```powershell
python -m experiments.final_benchmark --profile smoke --warmups 1 --trials 3
```

After validating the smoke run and installing Dolt on `PATH`, collect the paper
dataset with:

```powershell
python -m experiments.final_benchmark --profile paper --warmups 2 --trials 7
```

See [the experiment protocol](experiments/README.md) before interpreting or
publishing results. Generated benchmark directories and raw CSV files are not
committed.

## Try it interactively

```python
from versioned_db import VersionedDatabase

db = VersionedDatabase()
v1 = db.commit({"name": "Revon", "status": "prototype", "users": 10})
v2 = db.apply_changes(v1, puts={"status": "demo-ready"})

print(db.commit_stats[1])
print(db.commit_stats[2])
print(db.diff_versions(1, 2, strategy="hybrid"))
print(db.last_diff_stats)
```

Expected changed-key result:

```text
['status']
```

The core supports both direct in-memory experiments and durable single-file
SQLite repositories. Branch references, merging, and concurrent writers remain
outside the current scope. Commit history, addressed objects, historical
checkout, structured Merkle diffs, operation-log diffs, and adaptive Revon-H
selection are implemented.

## CSV snapshot dry run

Generate 1,000 sample rows, matching SQL history, and an after-change export:

```powershell
python -m examples.csv_snapshot_demo --generate-sample
```

Commit both snapshots and print roots, sharing statistics, changed rows, and
changed columns:

```powershell
python -m examples.csv_snapshot_demo data/users_before.csv data/users_after.csv --table users --primary-key id --sql data/changes.sql
```

For an interactive Python session, import `commit` and `show_diff` from
`examples.csv_snapshot_demo`. Commit the before and after files separately, then call
`show_diff(v1, v2)` when you want to print the comparison. The SQL file is
retained as commit metadata; the actual state diff comes from the two CSV
snapshots.
