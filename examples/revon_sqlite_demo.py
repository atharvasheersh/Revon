"""Create, close, and reopen a durable Revon SQLite repository.

The normal command imports two generated CSV states, closes the writer, and
launches a separate Python process that reopens and verifies the repository.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from examples.csv_snapshot_demo import CSVSnapshotSession, generate_sample_files
from sqlite_store import SQLiteRevonRepository


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def inspect_repository(path: Path) -> dict[str, Any]:
    """Open and verify a repository; used by the child process."""
    with SQLiteRevonRepository.open(path, verify=True) as repository:
        if repository.head is None or repository.head < 2:
            raise RuntimeError("demo repository does not contain two versions")
        report = repository.verify_integrity()
        changes = repository.diff_versions(1, 2, strategy="hybrid")
        return {
            "head": repository.head,
            "head_hash": repository.head_hash,
            "versions": len(repository.versions),
            "rows_v1": len(repository.checkout(1)),
            "rows_v2": len(repository.checkout(2)),
            "changed_keys": [entry.key for entry in changes],
            "hybrid_strategy": repository.last_diff_stats.strategy,
            "objects": report.objects,
            "nodes": report.nodes,
            "changesets": report.changesets,
            "commits": report.commits,
        }


def run_demo(database_path: Path, rows: int, reset: bool) -> dict[str, Any]:
    if rows < 20:
        raise ValueError("rows must be at least 20")
    database_path = database_path.resolve()
    if database_path.exists():
        if not reset:
            raise FileExistsError(
                f"repository already exists: {database_path}; use --reset to replace it"
            )
        database_path.unlink()
    journal_path = Path(str(database_path) + "-journal")
    if journal_path.exists():
        journal_path.unlink()

    sample_dir = PROJECT_ROOT / "tests" / "test_data" / "sqlite-demo"
    before, after, sql = generate_sample_files(sample_dir, rows=rows)

    with SQLiteRevonRepository.create(database_path) as repository:
        session = CSVSnapshotSession(repository)
        first = session.commit_csv(
            before,
            table="users",
            primary_key="id",
            message="CSV before changes",
        )
        second = session.commit_csv(
            after,
            table="users",
            primary_key="id",
            message="CSV after changes",
            sql_file=sql,
        )
        if (first, second) != (1, 2):
            raise RuntimeError("demo did not create exactly versions 1 and 2")

    # Reopen in a genuinely separate interpreter, not merely a new object.
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "examples.revon_sqlite_demo",
            "--inspect",
            str(database_path),
        ],
        cwd=PROJECT_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        raise RuntimeError(
            "child-process reopen failed:\n" + (process.stderr or process.stdout)
        )
    try:
        result = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("child process returned invalid verification output") from exc

    expected_changes = ["users:10", f"users:{rows + 1}", f"users:{rows // 2}"]
    expected_changes.append(f"users:{int(rows * 0.9)}")
    if result["changed_keys"] != sorted(set(expected_changes)):
        raise RuntimeError("reopened repository returned an unexpected CSV diff")
    if result["rows_v1"] != rows or result["rows_v2"] != rows:
        raise RuntimeError("reopened checkouts have incorrect row counts")
    if result["versions"] != 2 or result["commits"] != 2:
        raise RuntimeError("reopened history is incomplete")
    result["database"] = str(database_path)
    result["file_bytes"] = database_path.stat().st_size
    return result


def print_report(result: dict[str, Any]) -> None:
    print()
    print("Revon SQLite persistence verification")
    print("=" * 48)
    print(f"Repository          {result['database']}")
    print(f"SQLite file         {result['file_bytes']:,} bytes")
    print(f"Versions            {result['versions']}")
    print(f"Content objects     {result['objects']}")
    print(f"Trie nodes          {result['nodes']}")
    print(f"HEAD                {result['head_hash'][:20]}...")
    print(f"Reopened diff       {len(result['changed_keys'])} changed rows")
    print(f"Hybrid selected     {result['hybrid_strategy']}")
    print()
    print("PASS  CSV versions committed in atomic SQLite transactions")
    print("PASS  separate Python process reopened and verified every object hash")
    print("PASS  v1/v2 checkout and Hybrid diff reproduced identical results")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path("revon_demo.revon.db"),
    )
    parser.add_argument("--rows", type=int, default=100)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--inspect", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.inspect is not None:
        # Suppress incidental output so the parent receives one JSON document.
        with contextlib.redirect_stdout(io.StringIO()):
            result = inspect_repository(args.inspect.resolve())
        print(json.dumps(result, sort_keys=True))
        return

    result = run_demo(args.database, args.rows, args.reset)
    print_report(result)


if __name__ == "__main__":
    main()
