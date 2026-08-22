"""Durable SQLite repository for the Chronos-H in-memory model.

SQLite supplies atomic persistence only. Trie routing, content addressing,
version identity, and diff behavior remain defined by ``VersionedDatabase``.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from versioned_db import (
    ChangeOperation,
    Commit,
    CommitStats,
    DiffEntry,
    DiffStats,
    StructuralSharingStats,
    VersionedDatabase,
)


SCHEMA_VERSION = "1"


class ChronosIntegrityError(RuntimeError):
    """Stored hashes, references, or canonical payloads are inconsistent."""


@dataclass(frozen=True)
class IntegrityReport:
    objects: int
    nodes: int
    changesets: int
    commits: int
    versions: int
    head_hash: Optional[str]


class SQLiteChronosRepository:
    """A single-file durable Chronos repository.

    Use ``create`` for a new file and ``open`` for an existing one. Each model
    write is persisted as one ``BEGIN IMMEDIATE`` SQLite transaction containing
    new nodes, the changeset, commit object, version metadata, and HEAD update.
    """

    def __init__(self, path: Path, connection: sqlite3.Connection) -> None:
        self.path = path
        self._connection = connection
        self._db = VersionedDatabase()

    @classmethod
    def create(
        cls,
        path: str | Path,
        *,
        branching_factor: int = 8,
        tree_depth: int = 4,
        hybrid_log_threshold: int = 128,
    ) -> "SQLiteChronosRepository":
        target = Path(path).resolve()
        if target.exists():
            raise FileExistsError(f"Chronos repository already exists: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        connection = cls._connect(target)
        repository = cls(target, connection)
        try:
            repository._create_schema()
            repository._db = VersionedDatabase(
                branching_factor=branching_factor,
                tree_depth=tree_depth,
                hybrid_log_threshold=hybrid_log_threshold,
            )
            repository._write_configuration()
        except Exception:
            connection.close()
            if target.exists():
                target.unlink()
            raise
        return repository

    @classmethod
    def open(
        cls,
        path: str | Path,
        *,
        verify: bool = True,
    ) -> "SQLiteChronosRepository":
        target = Path(path).resolve()
        if not target.is_file():
            raise FileNotFoundError(f"Chronos repository not found: {target}")
        connection = cls._connect(target)
        repository = cls(target, connection)
        try:
            repository._require_schema()
            repository._load_model(verify=verify)
        except Exception:
            connection.close()
            raise
        return repository

    @staticmethod
    def _connect(path: Path) -> sqlite3.Connection:
        connection = sqlite3.connect(
            path,
            isolation_level=None,
            timeout=30.0,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = DELETE")
        connection.execute("PRAGMA synchronous = FULL")
        return connection

    def _create_schema(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            ) WITHOUT ROWID;

            CREATE TABLE objects (
                hash TEXT PRIMARY KEY,
                kind TEXT NOT NULL CHECK (kind IN ('node', 'changeset', 'commit')),
                payload BLOB NOT NULL
            ) WITHOUT ROWID;

            CREATE TABLE versions (
                version INTEGER PRIMARY KEY CHECK (version > 0),
                commit_hash TEXT NOT NULL UNIQUE,
                FOREIGN KEY (commit_hash) REFERENCES objects(hash)
            );

            CREATE TABLE commit_stats (
                version INTEGER PRIMARY KEY,
                new_nodes INTEGER NOT NULL CHECK (new_nodes >= 0),
                reused_nodes INTEGER NOT NULL CHECK (reused_nodes >= 0),
                bytes_written INTEGER NOT NULL CHECK (bytes_written >= 0),
                changed_keys INTEGER NOT NULL CHECK (changed_keys >= 0),
                FOREIGN KEY (version) REFERENCES versions(version)
            );

            CREATE TABLE refs (
                name TEXT PRIMARY KEY,
                commit_hash TEXT NOT NULL,
                FOREIGN KEY (commit_hash) REFERENCES objects(hash)
            ) WITHOUT ROWID;
            """
        )

    def _require_schema(self) -> None:
        tables = {
            row["name"]
            for row in self._connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        required = {"metadata", "objects", "versions", "commit_stats", "refs"}
        missing = required - tables
        if missing:
            raise ChronosIntegrityError(
                f"not a Chronos repository; missing tables: {sorted(missing)}"
            )

    def _write_configuration(self) -> None:
        values = {
            "schema_version": SCHEMA_VERSION,
            "branching_factor": str(self._db.branching_factor),
            "tree_depth": str(self._db.tree_depth),
            "hybrid_log_threshold": str(self._db.hybrid_log_threshold),
        }
        self._connection.execute("BEGIN IMMEDIATE")
        try:
            self._connection.executemany(
                "INSERT INTO metadata(key, value) VALUES (?, ?)",
                values.items(),
            )
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def _configuration(self) -> dict[str, str]:
        values = {
            row["key"]: row["value"]
            for row in self._connection.execute("SELECT key, value FROM metadata")
        }
        required = {
            "schema_version",
            "branching_factor",
            "tree_depth",
            "hybrid_log_threshold",
        }
        missing = required - set(values)
        if missing:
            raise ChronosIntegrityError(
                f"repository metadata is incomplete: {sorted(missing)}"
            )
        if values["schema_version"] != SCHEMA_VERSION:
            raise ChronosIntegrityError(
                "unsupported schema version: " + values["schema_version"]
            )
        return values

    @staticmethod
    def _decode(payload: bytes, object_hash: str) -> Any:
        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ChronosIntegrityError(
                f"object {object_hash} is not canonical JSON"
            ) from exc

    def _load_model(self, *, verify: bool) -> None:
        config = self._configuration()
        database = VersionedDatabase(
            branching_factor=int(config["branching_factor"]),
            tree_depth=int(config["tree_depth"]),
            hybrid_log_threshold=int(config["hybrid_log_threshold"]),
        )

        for row in self._connection.execute(
            "SELECT hash, kind, payload FROM objects ORDER BY kind, hash"
        ):
            object_hash = row["hash"]
            kind = row["kind"]
            value = self._decode(bytes(row["payload"]), object_hash)
            if kind == "node":
                database.node_store[object_hash] = value
            elif kind == "changeset":
                database.changeset_store[object_hash] = tuple(
                    ChangeOperation(
                        key=record["key"],
                        old_exists=record["old_exists"],
                        old_value=record["old"],
                        new_exists=record["new_exists"],
                        new_value=record["new"],
                    )
                    for record in value
                )
            elif kind == "commit":
                database.commit_store[object_hash] = value

        version_rows = list(
            self._connection.execute(
                "SELECT version, commit_hash FROM versions ORDER BY version"
            )
        )
        commit_to_version = {
            row["commit_hash"]: row["version"] for row in version_rows
        }
        stats_by_version = {
            row["version"]: row
            for row in self._connection.execute(
                """
                SELECT version, new_nodes, reused_nodes, bytes_written, changed_keys
                FROM commit_stats
                """
            )
        }
        for row in version_rows:
            version = row["version"]
            commit_hash = row["commit_hash"]
            try:
                payload = database.commit_store[commit_hash]
                stats = stats_by_version[version]
            except KeyError as exc:
                raise ChronosIntegrityError(
                    f"version {version} references missing commit data"
                ) from exc
            parent_hash = payload["parent"]
            parent_version = (
                commit_to_version.get(parent_hash) if parent_hash is not None else None
            )
            record = Commit(
                version=version,
                commit_hash=commit_hash,
                root_hash=payload["root"],
                parent=parent_version,
                parent_hash=parent_hash,
                message=payload["message"] or None,
                timestamp_ns=payload["timestamp_ns"],
                changeset_hash=payload["changeset"],
            )
            database.versions[version] = record.root_hash
            database.commits[version] = record
            database.version_commits[version] = commit_hash
            database.commit_stats[version] = CommitStats(
                version=version,
                new_nodes=stats["new_nodes"],
                reused_nodes=stats["reused_nodes"],
                bytes_written=stats["bytes_written"],
                changed_keys=stats["changed_keys"],
            )

        head_row = self._connection.execute(
            "SELECT commit_hash FROM refs WHERE name = 'HEAD'"
        ).fetchone()
        if head_row is not None:
            database.head_hash = head_row["commit_hash"]
            database.head = commit_to_version.get(database.head_hash)
        database.last_new_node_hashes = ()
        self._db = database
        if verify:
            self.verify_integrity()

    def _insert_object(self, object_hash: str, kind: str, payload: bytes) -> None:
        self._connection.execute(
            "INSERT OR IGNORE INTO objects(hash, kind, payload) VALUES (?, ?, ?)",
            (object_hash, kind, payload),
        )
        row = self._connection.execute(
            "SELECT kind, payload FROM objects WHERE hash = ?", (object_hash,)
        ).fetchone()
        if row is None or row["kind"] != kind or bytes(row["payload"]) != payload:
            raise ChronosIntegrityError(
                f"content-address collision or inconsistent object: {object_hash}"
            )

    def _persist_latest(self) -> None:
        version = self._db.head
        if version is None:
            raise RuntimeError("cannot persist an empty write")
        record = self._db.commits[version]
        stats = self._db.commit_stats[version]
        changes = self._db.changeset_store[record.changeset_hash]

        self._connection.execute("BEGIN IMMEDIATE")
        try:
            for node_hash in self._db.last_new_node_hashes:
                self._insert_object(
                    node_hash,
                    "node",
                    self._db._canonical_bytes(self._db.node_store[node_hash]),
                )
            self._insert_object(
                record.changeset_hash,
                "changeset",
                self._db._canonical_bytes(
                    [change.as_record() for change in changes]
                ),
            )
            self._insert_object(
                record.commit_hash,
                "commit",
                self._db._canonical_bytes(
                    self._db.commit_store[record.commit_hash]
                ),
            )
            self._connection.execute(
                "INSERT INTO versions(version, commit_hash) VALUES (?, ?)",
                (version, record.commit_hash),
            )
            self._connection.execute(
                """
                INSERT INTO commit_stats(
                    version, new_nodes, reused_nodes, bytes_written, changed_keys
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    version,
                    stats.new_nodes,
                    stats.reused_nodes,
                    stats.bytes_written,
                    stats.changed_keys,
                ),
            )
            self._connection.execute(
                """
                INSERT INTO refs(name, commit_hash) VALUES ('HEAD', ?)
                ON CONFLICT(name) DO UPDATE SET commit_hash = excluded.commit_hash
                """,
                (record.commit_hash,),
            )
            self._connection.commit()
        except Exception:
            self._connection.rollback()
            raise

    def _write(self, operation: Any) -> str:
        try:
            root_hash = operation()
            self._persist_latest()
            return root_hash
        except Exception:
            # A failed SQLite transaction must not leave the in-memory HEAD
            # ahead of durable state. Rehydrate from the last committed file.
            self._load_model(verify=True)
            raise

    def commit(self, state: Mapping[str, Any], message: Optional[str] = None) -> str:
        return self._write(lambda: self._db.commit(state, message=message))

    def apply_changes(
        self,
        root_hash: str,
        *,
        puts: Optional[Mapping[str, Any]] = None,
        deletes: Optional[Iterable[str]] = None,
        message: Optional[str] = None,
    ) -> str:
        return self._write(
            lambda: self._db.apply_changes(
                root_hash,
                puts=puts,
                deletes=deletes,
                message=message,
            )
        )

    def put(
        self,
        root_hash: str,
        key: str,
        value: Any,
        message: Optional[str] = None,
    ) -> str:
        return self.apply_changes(
            root_hash, puts={key: value}, message=message
        )

    def delete(
        self, root_hash: str, key: str, message: Optional[str] = None
    ) -> str:
        return self.apply_changes(
            root_hash, deletes={key}, message=message
        )

    def verify_integrity(self) -> IntegrityReport:
        sqlite_check = self._connection.execute("PRAGMA integrity_check").fetchone()[0]
        if sqlite_check != "ok":
            raise ChronosIntegrityError(
                f"SQLite integrity check failed: {sqlite_check}"
            )
        rows = list(
            self._connection.execute(
                "SELECT hash, kind, payload FROM objects ORDER BY hash"
            )
        )
        kinds: dict[str, str] = {}
        values: dict[str, Any] = {}
        counts = {"node": 0, "changeset": 0, "commit": 0}
        for row in rows:
            object_hash = row["hash"]
            kind = row["kind"]
            payload = bytes(row["payload"])
            value = self._decode(payload, object_hash)
            if payload != self._db._canonical_bytes(value):
                raise ChronosIntegrityError(
                    f"object {object_hash} is not canonically encoded"
                )
            if kind == "node":
                calculated = hashlib.sha256(payload).hexdigest()
            else:
                calculated = self._db._content_hash(kind, value)
            if calculated != object_hash:
                raise ChronosIntegrityError(
                    f"hash mismatch for {kind} object {object_hash}"
                )
            kinds[object_hash] = kind
            values[object_hash] = value
            counts[kind] += 1

        for object_hash, value in values.items():
            kind = kinds[object_hash]
            if kind == "node":
                node_type = value.get("type")
                if node_type == "internal":
                    for child_hash in value.get("children", {}).values():
                        if kinds.get(child_hash) != "node":
                            raise ChronosIntegrityError(
                                f"node {object_hash} references missing child {child_hash}"
                            )
                elif node_type != "leaf":
                    raise ChronosIntegrityError(
                        f"node {object_hash} has invalid type {node_type!r}"
                    )
            elif kind == "commit":
                root_hash = value.get("root")
                changeset_hash = value.get("changeset")
                parent_hash = value.get("parent")
                if kinds.get(root_hash) != "node":
                    raise ChronosIntegrityError(
                        f"commit {object_hash} references missing root {root_hash}"
                    )
                if kinds.get(changeset_hash) != "changeset":
                    raise ChronosIntegrityError(
                        f"commit {object_hash} references missing changeset"
                    )
                if parent_hash is not None and kinds.get(parent_hash) != "commit":
                    raise ChronosIntegrityError(
                        f"commit {object_hash} references missing parent"
                    )

        version_rows = list(
            self._connection.execute(
                "SELECT version, commit_hash FROM versions ORDER BY version"
            )
        )
        expected_versions = list(range(1, len(version_rows) + 1))
        actual_versions = [row["version"] for row in version_rows]
        if actual_versions != expected_versions:
            raise ChronosIntegrityError("version numbers are not contiguous")
        previous_hash: Optional[str] = None
        for row in version_rows:
            commit_hash = row["commit_hash"]
            if kinds.get(commit_hash) != "commit":
                raise ChronosIntegrityError(
                    f"version {row['version']} references a missing commit"
                )
            if values[commit_hash].get("parent") != previous_hash:
                raise ChronosIntegrityError(
                    f"version {row['version']} has an invalid parent"
                )
            previous_hash = commit_hash

        stats_count = self._connection.execute(
            "SELECT COUNT(*) AS count FROM commit_stats"
        ).fetchone()["count"]
        if stats_count != len(version_rows):
            raise ChronosIntegrityError("commit statistics are incomplete")

        head_row = self._connection.execute(
            "SELECT commit_hash FROM refs WHERE name = 'HEAD'"
        ).fetchone()
        head_hash = head_row["commit_hash"] if head_row is not None else None
        expected_head = version_rows[-1]["commit_hash"] if version_rows else None
        if head_hash != expected_head:
            raise ChronosIntegrityError("HEAD does not reference the latest version")

        return IntegrityReport(
            objects=len(rows),
            nodes=counts["node"],
            changesets=counts["changeset"],
            commits=counts["commit"],
            versions=len(version_rows),
            head_hash=head_hash,
        )

    @property
    def database(self) -> VersionedDatabase:
        return self._db

    @property
    def versions(self) -> dict[int, str]:
        return self._db.versions

    @property
    def commits(self) -> dict[int, Commit]:
        return self._db.commits

    @property
    def version_commits(self) -> dict[int, str]:
        return self._db.version_commits

    @property
    def commit_stats(self) -> dict[int, CommitStats]:
        return self._db.commit_stats

    @property
    def head(self) -> Optional[int]:
        return self._db.head

    @property
    def head_hash(self) -> Optional[str]:
        return self._db.head_hash

    @property
    def last_diff_stats(self) -> DiffStats:
        return self._db.last_diff_stats

    def get(self, root_hash: str, key: str) -> Any:
        return self._db.get(root_hash, key)

    def checkout(self, version: int) -> dict[str, Any]:
        return self._db.checkout(version)

    def log(self) -> list[Commit]:
        return self._db.log()

    def diff(self, left_root: str, right_root: str) -> list[str]:
        return self._db.diff(left_root, right_root)

    def diff_versions(
        self, left_version: int, right_version: int, strategy: str = "hybrid"
    ) -> list[DiffEntry]:
        return self._db.diff_versions(left_version, right_version, strategy)

    def structural_sharing(
        self, left_root: str, right_root: str
    ) -> StructuralSharingStats:
        return self._db.structural_sharing(left_root, right_root)

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteChronosRepository":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
