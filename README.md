# Chronos

Chronos is a content-addressed versioned data store for structured key-value
data. Its state index is a persistent fixed-depth Merkle hash trie. Atomic
batch commits copy and re-hash only the affected paths; unchanged subtrees are
shared by their existing hashes. Chronos-H adaptively chooses operation-log or
hash-pruned Merkle differencing for version comparisons.

## Run the demo

Requires Python 3.9 or newer and no third-party packages.

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

## Run the tests

```powershell
python -m unittest -v
```

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

The current core is in-memory and deliberately excludes disk persistence, WAL,
branch references, merging, and concurrent writers. It includes commit
history, content-addressed commits, historical checkout, structured Merkle
diffs, operation-log diffs, and adaptive Chronos-H selection.

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
