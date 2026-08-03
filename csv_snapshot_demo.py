"""Commit CSV snapshots to Chronos and attach SQL text as commit history.

Interactive usage:

    >>> from csv_snapshot_demo import commit, show_diff, commit_metadata
    >>> v1 = commit("data/users_before.csv", table="users", primary_key="id")
    >>> v2 = commit("data/users_after.csv", table="users", primary_key="id",
    ...             sql_file="data/changes.sql")

The SQL file is metadata only. The state diff is calculated from the CSV files.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any, Optional

from versioned_db import VersionedDatabase


class CSVSnapshotSession:
    """One in-memory Chronos session containing CSV snapshots and metadata."""

    def __init__(self, database: Optional[VersionedDatabase] = None) -> None:
        self.db = database or VersionedDatabase()
        self.snapshots: dict[int, dict[str, dict[str, str]]] = {}
        self.commit_metadata: dict[int, dict[str, Any]] = {}

    @staticmethod
    def load_csv(
        csv_file: str | Path,
        table: str,
        primary_key: str,
    ) -> dict[str, dict[str, str]]:
        path = Path(csv_file)
        if not path.is_file():
            raise FileNotFoundError(f"CSV file not found: {path}")
        if not table.strip():
            raise ValueError("table name cannot be empty")

        state: dict[str, dict[str, str]] = {}
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames:
                raise ValueError(f"CSV has no header: {path}")
            if primary_key not in reader.fieldnames:
                raise ValueError(
                    f"primary key '{primary_key}' not found in {path}; "
                    f"columns are {reader.fieldnames}"
                )

            for row_number, row in enumerate(reader, start=2):
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"malformed CSV row {row_number} in {path}")
                primary_value = row[primary_key]
                if primary_value == "":
                    raise ValueError(
                        f"missing primary key '{primary_key}' on row {row_number}"
                    )

                key = f"{table}:{primary_value}"
                if key in state:
                    raise ValueError(
                        f"duplicate primary key '{primary_value}' on row {row_number}"
                    )
                state[key] = dict(row)

        return state

    def commit_csv(
        self,
        csv_file: str | Path,
        *,
        table: str,
        primary_key: str,
        message: str = "",
        sql_file: str | Path | None = None,
    ) -> int:
        state = self.load_csv(csv_file, table, primary_key)

        sql_text = None
        sql_path = None
        if sql_file is not None:
            candidate = Path(sql_file)
            if not candidate.is_file():
                raise FileNotFoundError(f"SQL file not found: {candidate}")
            sql_path = str(candidate)
            sql_text = candidate.read_text(encoding="utf-8")

        root_hash = self.db.commit(state)
        version = len(self.db.versions)
        self.snapshots[version] = state
        self.commit_metadata[version] = {
            "message": message,
            "table": table,
            "primary_key": primary_key,
            "csv_file": str(Path(csv_file)),
            "sql_file": sql_path,
            "sql_text": sql_text,
            "root_hash": root_hash,
            "row_count": len(state),
        }

        print()
        print(f"Created commit v{version}: {message or '(no message)'}")
        print(f"  CSV: {csv_file} ({len(state):,} rows)")
        if sql_path:
            statement_count = sum(
                1 for statement in sql_text.split(";") if statement.strip()
            )
            print(f"  SQL history: {sql_path} ({statement_count} statements)")
        print(f"  root: {root_hash[:16]}...")
        print(f"  {self.db.commit_stats[version]}")

        if version > 1:
            self.show_diff(version - 1, version)

        return version

    def show_diff(self, left_version: int, right_version: int) -> list[str]:
        try:
            left_root = self.db.versions[left_version]
            right_root = self.db.versions[right_version]
            left_state = self.snapshots[left_version]
            right_state = self.snapshots[right_version]
        except KeyError as exc:
            raise KeyError(f"unknown CSV commit version: {exc.args[0]}") from exc

        changed_keys = self.db.diff(left_root, right_root)
        print()
        print(f"Diff v{left_version} -> v{right_version}")
        print(f"  changed rows: {changed_keys}")
        print(f"  {self.db.last_diff_stats}")

        for key in changed_keys:
            old_row = left_state.get(key)
            new_row = right_state.get(key)
            if old_row is None:
                print(f"  ADDED   {key}: {new_row}")
            elif new_row is None:
                print(f"  DELETED {key}: {old_row}")
            else:
                print(f"  UPDATED {key}")
                for column in sorted(set(old_row) | set(new_row)):
                    old_value = old_row.get(column)
                    new_value = new_row.get(column)
                    if old_value != new_value:
                        print(
                            f"    {column}: {old_value!r} -> {new_value!r}"
                        )

        return changed_keys


def generate_sample_files(
    output_dir: str | Path = "data",
    rows: int = 1_000,
) -> tuple[Path, Path, Path]:
    """Generate a deterministic MySQL Workbench-style dry-run dataset."""
    if rows < 10:
        raise ValueError("sample must contain at least 10 rows")

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    before_path = directory / "users_before.csv"
    after_path = directory / "users_after.csv"
    sql_path = directory / "changes.sql"
    fieldnames = ["id", "name", "status", "balance"]

    before_rows = [
        {
            "id": str(index),
            "name": f"User {index:04d}",
            "status": "active",
            "balance": f"{100 + index / 10:.2f}",
        }
        for index in range(1, rows + 1)
    ]
    after_by_id = {row["id"]: dict(row) for row in before_rows}

    update_status_id = "10"
    update_balance_id = str(max(11, rows // 2))
    delete_id = str(max(12, int(rows * 0.9)))
    insert_id = str(rows + 1)
    after_by_id[update_status_id]["status"] = "inactive"
    after_by_id[update_balance_id]["balance"] = "999.00"
    del after_by_id[delete_id]
    after_by_id[insert_id] = {
        "id": insert_id,
        "name": "New User",
        "status": "active",
        "balance": "150.00",
    }

    def write_csv(path: Path, records: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(records)

    write_csv(before_path, before_rows)
    write_csv(
        after_path,
        sorted(after_by_id.values(), key=lambda row: int(row["id"])),
    )

    sql_path.write_text(
        f"""UPDATE users
SET status = 'inactive'
WHERE id = {update_status_id};

UPDATE users
SET balance = 999.00
WHERE id = {update_balance_id};

DELETE FROM users
WHERE id = {delete_id};

INSERT INTO users (id, name, status, balance)
VALUES ({insert_id}, 'New User', 'active', 150.00);
""",
        encoding="utf-8",
    )
    return before_path, after_path, sql_path


# Convenient functions and state for use in an interactive Python terminal.
session = CSVSnapshotSession()
db = session.db
snapshots = session.snapshots
commit_metadata = session.commit_metadata


def commit(*args: Any, **kwargs: Any) -> int:
    return session.commit_csv(*args, **kwargs)


def show_diff(left_version: int, right_version: int) -> list[str]:
    return session.show_diff(left_version, right_version)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Commit and compare before/after CSV snapshots with Chronos."
    )
    parser.add_argument("before_csv", nargs="?")
    parser.add_argument("after_csv", nargs="?")
    parser.add_argument("--table", default="users")
    parser.add_argument("--primary-key", default="id")
    parser.add_argument("--sql")
    parser.add_argument("--generate-sample", action="store_true")
    parser.add_argument("--sample-rows", type=int, default=1_000)
    args = parser.parse_args()

    if args.generate_sample:
        paths = generate_sample_files(rows=args.sample_rows)
        print("Generated dry-run files:")
        for path in paths:
            print(f"  {path}")
        return

    if not args.before_csv or not args.after_csv:
        parser.error(
            "provide BEFORE_CSV and AFTER_CSV, or use --generate-sample"
        )

    commit(
        args.before_csv,
        table=args.table,
        primary_key=args.primary_key,
        message="State before SQL changes",
    )
    commit(
        args.after_csv,
        table=args.table,
        primary_key=args.primary_key,
        message="State after SQL changes",
        sql_file=args.sql,
    )


if __name__ == "__main__":
    main()
