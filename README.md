# Chronos hash-tree demo

Chronos is a minimal, in-memory versioned key-value database. Each immutable
tree node is stored under a SHA-256 hash of its content, so unchanged subtrees
are shared by different version roots. During a diff, equal subtree hashes are
skipped without reading their keys.

## Run the demo

Requires Python 3.9 or newer and no third-party packages.

```powershell
python demo.py
```

The output shows the root for each version, new/reused nodes, the sharing
percentage, changed keys, and how many identical subtrees the diff skipped.

## Run the tests

```powershell
python -m unittest -v
```

## Compare the three versioning models

```powershell
python benchmarks.py
```

This compares a full-snapshot state model, an operation-log model, and the
Chronos content-addressed hash tree. It reports median commit time, median diff
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
v2 = db.commit({"name": "Chronos", "status": "demo-ready", "users": 10})

print(db.commit_stats[1])
print(db.commit_stats[2])
print(db.diff(v1, v2))
print(db.last_diff_stats)
```

Expected changed-key result:

```text
['status']
```

This prototype deliberately excludes disk storage, WAL, checkout, branching,
and merging.

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

For an interactive Python session, import `commit` from `csv_snapshot_demo` and
commit the before and after files in the same session. The SQL file is retained
as commit metadata; the actual state diff comes from the two CSV snapshots.
