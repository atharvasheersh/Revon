# Commit note: Transactional SQLite persistence

- Date: 2026-08-21
- Commit: `PENDING`
- Author: atharvasheersh / Chronos team
- Scope: storage and core

## Objective

Make Chronos durable without replacing its fixed-depth Merkle trie, and prove
that committed history survives process boundaries with verifiable integrity.

## Changes

- Added a single-file SQLite repository with schema/configuration metadata.
- Persisted new trie nodes, changesets, commits, version aliases, metrics, and
  the `HEAD` reference.
- Wrote every version as one `BEGIN IMMEDIATE` transaction.
- Reloaded the last durable state after any failed persistence transaction.
- Verified canonical encodings, hash domains, object references, version
  continuity, parent chains, metrics, and `HEAD` on reopen.
- Added a separate-process CSV persistence CLI demonstration.
- Made CSV sessions use durable checkout instead of session-only snapshots.
- Added database-file ignore patterns and persistence documentation.

## Verification

```text
python -m unittest discover -v
30 tests passed

python chronos_sqlite_demo.py --database test_data/sqlite/manual-demo.chronos.db --rows 100 --reset
2 versions; 271 content objects; 267 trie nodes; 4-row reopened diff.
PASS: atomic CSV commits, separate-process hash verification, exact checkout,
and Hybrid diff reproduction.
```

Additional tests inject a SQLite transaction failure and corrupt a stored root
payload. The failed version is fully rolled back, and the tampered repository
is rejected on open.

## Design decisions

- SQLite is an embedded object container, not the Chronos indexing model.
- The rollback journal and `synchronous=FULL` prioritize correctness for the
  final prototype.
- Commit measurements are stored outside the content-addressed commit payload.
- Incremental persistence consumes the model's new-node delta only.
- Repository configuration is fixed at creation and restored on reopen.

## Known limitations

- History remains linear and writes must target `HEAD`.
- There is no object garbage collection or concurrent-writer API.
- SQL audit-file contents are not yet persisted as separate addressed metadata.

## Next action

Build the reproducible Snapshot, Log-only, Chronos-M, Chronos-H, and Dolt
benchmark harness over durable repositories.
