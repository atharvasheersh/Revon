# Chronos

Chronos is a content-addressed versioned data store for structured key-value
data. Its state index is a persistent fixed-depth Merkle hash trie. Atomic
batch commits copy and re-hash only the affected paths; unchanged subtrees are
shared by their existing hashes. Chronos-H adaptively chooses operation-log or
hash-pruned Merkle differencing for version comparisons.

## Paper and reproducibility

- The final manuscript is available as
  [PDF](paper/Chronos_Final_Research_Paper.pdf) and
  [DOCX](paper/Chronos_Final_Research_Paper.docx).
- The audited 333-trial comparison is stored in
  [`evidence/paper-final-20260824/`](evidence/paper-final-20260824/).
- The 45-trial trie-parameter sensitivity study is stored in
  [`evidence/trie-sensitivity-20260824/`](evidence/trie-sensitivity-20260824/).
- Architecture documentation and its visual companions are under
  [`docs/architecture/`](docs/architecture/).

The `output/` directory is reserved for generated local runs and is ignored by
Git. Personal presentation and review material is not part of the repository.

## Run the demo

Requires Python 3.10 or newer and no third-party packages.

```powershell
python demo.py
```

The output shows the root for each version, new/reused nodes, the sharing
percentage, changed keys, and how many identical subtrees the diff skipped.

For a self-checking CLI demonstration that also proves the incremental root is
identical to a clean full rebuild:

```powershell
python chronos_cli_demo.py --show-changes
```

Use `--rows`, `--updates`, and `--hybrid-threshold` to change the workload and
observe when Chronos-H selects Log or Merkle differencing.

## Verify durable SQLite persistence

Run the complete persistence flow:

```powershell
python chronos_sqlite_demo.py --database chronos_demo.chronos.db --reset
```

The command generates two deterministic CSV states, imports them as versions,
closes the SQLite writer, and launches a separate Python process that:

- reopens the repository;
- verifies every node, changeset, and commit against its content hash;
- checks that `HEAD` references the latest commit;
- checks out both versions; and
- reproduces the version diff.

SQLite is the atomic durable object container. The fixed-depth Merkle trie,
content-addressed commits, and Chronos-H diff selection remain Chronos logic.

## Run the tests

```powershell
python -m unittest -v
```

## Run the backend API

Start the dependency-free local REST API:

```powershell
python -m chronos_api
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
python benchmarks.py
```

This compares a full-snapshot state model, an operation-log model, and the
Chronos-H hybrid model. It reports median incremental commit time, median diff
time, logical serialized storage, and how much work each diff examines.

For a shorter sample run:

```powershell
python benchmarks.py --sizes 1000,10000 --versions 5 --changes 10
```

## Run the final research comparison

The final reproducible harness compares Snapshot, Log-only, the forced-Merkle
ablation, Chronos-H, and a real Dolt CLI adapter. It records raw trial CSV,
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
v1 = db.commit({"name": "Chronos", "status": "prototype", "users": 10})
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
checkout, structured Merkle diffs, operation-log diffs, and adaptive Chronos-H
selection are implemented.

## CSV snapshot dry run

Generate 1,000 sample rows, matching SQL history, and an after-change export:

```powershell
python csv_snapshot_demo.py --generate-sample
```

Commit both snapshots and print roots, sharing statistics, changed rows, and
changed columns:

```powershell
python csv_snapshot_demo.py data/users_before.csv data/users_after.csv --table users --primary-key id --sql data/changes.sql
```

For an interactive Python session, import `commit` and `show_diff` from
`csv_snapshot_demo`. Commit the before and after files separately, then call
`show_diff(v1, v2)` when you want to print the comparison. The SQL file is
retained as commit metadata; the actual state diff comes from the two CSV
snapshots.
