"""Live demo: incremental put(), message-bearing commits, log(), checkout().

    python incremental_demo.py

Commits a large CSV snapshot, edits a single row with put() without rebuilding
the tree, then walks the commit graph and checks out the earlier version.
"""

from __future__ import annotations

import contextlib
import io
import time

from csv_snapshot_demo import CSVSnapshotSession, generate_sample_files

ROWS = 20_000
EDIT_KEY = "users:500"
NEW_KEY = "users:999999"


def rule(title: str) -> None:
    print()
    print(f"--- {title} " + "-" * max(0, 62 - len(title)))


def main() -> None:
    # Written to a scratch directory so the demo never rewrites data/.
    before_csv, _, _ = generate_sample_files("tmp_demo", rows=ROWS)

    session = CSVSnapshotSession()
    db = session.db

    rule(f"1. Baseline commit of {ROWS:,} rows")
    with contextlib.redirect_stdout(io.StringIO()):
        session.commit_csv(
            before_csv, table="users", primary_key="id", message="Initial load"
        )
    root = db.versions[1]
    print(f"  root:        {root[:16]}...")
    print(f"  tree nodes:  {len(db.node_store):,}")
    print(f"  {db.commit_stats[1]}")

    rule("2. put() one row on the already-committed state")
    original_row = db.materialize(root)[EDIT_KEY]
    print(f"  before: {EDIT_KEY} = {original_row}")

    nodes_before = len(db.node_store)
    updated_row = dict(original_row, status="suspended", balance="0.00")
    started = time.perf_counter_ns()
    root = db.put(root, EDIT_KEY, updated_row, message="Suspend user 500")
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000

    print(f"  after:  {EDIT_KEY} = {updated_row}")
    print(f"  new nodes created: {len(db.node_store) - nodes_before} "
          f"(tree_depth + 1 = {db.tree_depth + 1})")
    print(f"  time:              {elapsed_ms:.3f} ms "
          f"(no full-tree rebuild of {ROWS:,} rows)")
    print(f"  root:              {root[:16]}...")

    rule("3. A second incremental commit, with a message")
    root = db.put(
        root,
        NEW_KEY,
        {"id": "999999", "name": "Late Signup", "status": "active",
         "balance": "42.00"},
        message="Insert late signup",
    )
    root = db.delete(root, "users:1", message="Delete user 1")
    print(f"  HEAD is now v{db.head}, root {root[:16]}...")

    rule("4. log() — parent chain from HEAD back to the first commit")
    for entry in db.log():
        parent = f"v{entry.parent}" if entry.parent is not None else "(root)"
        stamp = time.strftime("%H:%M:%S", time.localtime(entry.timestamp))
        print(f"  v{entry.version}  parent={parent:<7} {stamp}  "
              f"{entry.root_hash[:12]}...  {entry.message}")

    rule("5. checkout() an earlier version")
    v1_state = db.checkout(1)
    head_state = db.checkout(db.head)
    print(f"  checkout(1):       {len(v1_state):,} rows, "
          f"{EDIT_KEY} = {v1_state[EDIT_KEY]}")
    print(f"  checkout({db.head}):       {len(head_state):,} rows, "
          f"{EDIT_KEY} = {head_state[EDIT_KEY]}")
    print(f"  v1 still intact:   {v1_state[EDIT_KEY] == original_row}")
    print(f"  'users:1' present at v1={('users:1' in v1_state)}, "
          f"at HEAD={('users:1' in head_state)}")

    rule("6. diff() across the incremental commits")
    changed = db.diff(db.versions[1], root)
    print(f"  changed rows: {changed}")
    print(f"  {db.last_diff_stats}")
    print()


if __name__ == "__main__":
    main()
