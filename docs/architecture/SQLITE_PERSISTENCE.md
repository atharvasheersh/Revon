# SQLite persistence contract

## Role

SQLite is Revon's embedded durable object container. It does not perform trie
routing, version differencing, or content-address calculation. Those remain in
the deterministic `VersionedDatabase` model.

```text
CSV / API batch
      |
      v
VersionedDatabase.apply_changes()
      |
      +-- new trie nodes only
      +-- one changeset object
      +-- one commit object
      +-- one version alias
      |
      v
BEGIN IMMEDIATE
      |
      +-- insert addressed objects
      +-- insert version and metrics
      +-- update HEAD
      |
      v
COMMIT or complete rollback
```

## Schema

- `objects(hash, kind, payload)` stores canonical node, changeset, and commit
  payloads.
- `versions(version, commit_hash)` maps human-readable integers to addressed
  commits.
- `commit_stats(...)` stores measurement metadata outside commit identity.
- `refs(name, commit_hash)` stores `HEAD`.
- `metadata(key, value)` stores schema and fixed-trie configuration.

Only node hashes created by the latest incremental write are offered to SQLite.
This keeps persistence on the incremental delta instead of scanning the full
node store after each commit.

## Atomicity

Nodes, changeset, commit, version metrics, and `HEAD` are written in one SQLite
transaction. If any statement fails, SQLite rolls back and the wrapper reloads
the last durable model so its in-memory `HEAD` cannot move ahead of the file.

The test suite injects a trigger failure during version insertion and verifies
that neither the database nor the in-memory repository exposes the failed
version.

## Integrity verification

Opening a repository verifies:

1. canonical JSON encoding;
2. every object against its expected hash domain;
3. internal-node child references;
4. commit root, changeset, and parent references;
5. contiguous versions and their linear parent chain;
6. complete commit metrics; and
7. `HEAD` against the latest version.

The test suite deliberately changes a stored root payload and verifies that
reopening raises `RevonIntegrityError`.

## Reopen demonstration

```powershell
python -m examples.revon_sqlite_demo --database revon_demo.revon.db --reset
```

The writer imports and commits two generated CSV files, closes, then starts a
separate Python interpreter that reopens the file and verifies hashes, history,
checkout, and diff results.

## Current limits

- One linear `HEAD`; named branches and merge commits are not implemented.
- One writer at a time; the final platform should serialize write requests.
- Values remain inline in leaf nodes.
- Garbage collection of unreachable objects is not implemented.
