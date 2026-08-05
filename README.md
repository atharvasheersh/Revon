# Chronos hash-tree demo

Chronos is a minimal, in-memory versioned key-value database. Each immutable
tree node is stored under a SHA-256 hash of its content, so unchanged subtrees
are shared by different version roots. During a diff, equal subtree hashes are
skipped without reading their keys.

## What works today

- **Content-addressed commits** — `commit(state, message=None)` builds a tree
  whose root hash is determined purely by content, so identical states collapse
  to the same root.
- **Incremental single-key writes** — `put(root, key, value)` and
  `delete(root, key)` rewrite only the `tree_depth + 1` nodes on the routed
  path and reuse every sibling subtree by hash. No full-tree rebuild.
  A 3-key change at 100,000 rows creates 15 new nodes out of 4,681 and runs
  ~1000x faster than the old rebuild path.
- **Commit graph** — real `Commit` objects (version, root hash, parent,
  message, timestamp) with a tracked `head`; `log()` walks parent pointers back
  from HEAD.
- **Time travel** — `checkout(version)` and `materialize(root)` return the full
  state at any point in history.
- **Structural diff** — `diff(left_root, right_root)` prunes every subtree
  whose hashes match, and reports how much it skipped.

Still deliberately excluded: branching, merging, disk storage, WAL, and
transactions. See `PLANS.md` for the roadmap and
`output/docs/Chronos_Work_Remaining.docx` for detail.

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
time, logical serialized storage, and how much work each diff examines. The
Chronos row is measured on the incremental `put()` path.

To measure the incremental path against the old full-rebuild path directly:

```powershell
python incremental_benchmark.py
```

Recorded results are in `BENCHMARK_RESULTS_POST_INCREMENTAL.md`.

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

Incremental writes, history, and time travel:

```python
db = VersionedDatabase()
v1 = db.commit({"a": 1, "b": 2}, message="initial load")
v2 = db.put(v1, "a", 99, message="bump a")      # rewrites 5 nodes, not the tree
v3 = db.delete(v2, "b", message="drop b")

print(db.checkout(1))       # {'a': 1, 'b': 2} — v1 is still intact
print(db.checkout(3))       # {'a': 99}
for entry in db.log():
    print(entry)            # v3 <- v2 <- v1, newest first
```

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

## Incremental commit walkthrough

```powershell
python incremental_demo.py
```

Commits a 20,000-row snapshot, edits one row with `put()` (5 new nodes, sub-
millisecond), adds a message-bearing insert and delete, then prints `log()` and
checks out the original version to show it is unchanged.

For an interactive Python session, import `commit` from `csv_snapshot_demo` and
commit the before and after files in the same session. The SQL file is retained
as commit metadata; the actual state diff comes from the two CSV snapshots.
