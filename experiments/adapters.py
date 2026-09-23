"""Durable model adapters used by the final Revon experiment harness."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import re
import csv
from pathlib import Path
from typing import Any, Optional

from sqlite_store import SQLiteRevonRepository

from .workloads import Mutation, apply_mutations


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def value_digest(value: Optional[str]) -> Optional[str]:
    return hashlib.sha256(value.encode("utf-8")).hexdigest() if value is not None else None


def canonical_state_bytes(state: dict[str, str]) -> bytes:
    """The common checkout result is sorted UTF-8 JSON key/value pairs."""
    return canonical_bytes({"records": [[key, state[key]] for key in sorted(state)]})


def decode_state_bytes(output: bytes) -> dict[str, str]:
    try:
        document = json.loads(output)
        records = document["records"]
        if not isinstance(records, list):
            raise TypeError
        result: dict[str, str] = {}
        for row in records:
            if not isinstance(row, list) or len(row) != 2:
                raise TypeError
            key, value = row
            if not isinstance(key, str) or not isinstance(value, str) or key in result:
                raise TypeError
            result[key] = value
        return result
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("checkout did not materialize the canonical state contract") from exc


def canonical_diff_bytes(changes: dict[str, tuple[Optional[str], Optional[str]]]) -> bytes:
    """Normalize every implementation to sorted changed keys and value hashes."""
    records = [
        {
            "key": key,
            "old_value_sha256": value_digest(old),
            "new_value_sha256": value_digest(new),
        }
        for key, (old, new) in sorted(changes.items())
        if old != new
    ]
    return canonical_bytes({"changes": records})


def decode_diff_bytes(output: bytes) -> dict[str, tuple[Optional[str], Optional[str]]]:
    """Decode the public key/hash contract for correctness checks."""
    try:
        document = json.loads(output)
        records = document["changes"]
        if not isinstance(records, list):
            raise TypeError
        decoded: dict[str, tuple[Optional[str], Optional[str]]] = {}
        previous = None
        for record in records:
            key = record["key"]
            old = record["old_value_sha256"]
            new = record["new_value_sha256"]
            if (
                not isinstance(key, str)
                or key in decoded
                or (previous is not None and key <= previous)
                or (old is not None and not isinstance(old, str))
                or (new is not None and not isinstance(new, str))
                or old == new
                or not any(value is not None for value in (old, new))
                or any(
                    value is not None
                    and (len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value))
                    for value in (old, new)
                )
            ):
                raise TypeError
            decoded[key] = (old, new)
            previous = key
        if canonical_bytes(document) != output:
            raise TypeError
        return decoded
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError("diff did not materialize the canonical key/hash contract") from exc


def durable_write(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(canonical_bytes(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def directory_size(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


class SnapshotAdapter:
    name = "Snapshot"
    strategy_requested = "full-scan"

    def __init__(self, path: Path, **_: Any) -> None:
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self.version = 0
        self.state: dict[str, str] = {}
        self.work_examined: Optional[int] = None
        self.work_unit = "keys"
        self.strategy_selected = "full-scan"
        self.external_peak_memory: Optional[int] = None

    def initial_import(self, state: dict[str, str]) -> None:
        self.state = dict(state)
        self.version = 1
        durable_write(self._version_path(1), self.state)

    def commit(self, mutations: tuple[Mutation, ...]) -> None:
        apply_mutations(self.state, mutations)
        self.version += 1
        durable_write(self._version_path(self.version), self.state)

    def checkout(self, version: int) -> bytes:
        with self._version_path(version).open("r", encoding="utf-8") as stream:
            return canonical_state_bytes(json.load(stream))

    def diff(self, left: int, right: int) -> bytes:
        left_state = decode_state_bytes(self.checkout(left))
        right_state = decode_state_bytes(self.checkout(right))
        keys = set(left_state) | set(right_state)
        self.work_examined = len(keys)
        missing = object()
        changes = {
            key: (left_state.get(key), right_state.get(key))
            for key in keys
            if left_state.get(key, missing) != right_state.get(key, missing)
        }
        return canonical_diff_bytes(changes)

    def storage_bytes(self) -> int:
        return directory_size(self.path)

    def close(self) -> None:
        pass

    def _version_path(self, version: int) -> Path:
        return self.path / f"version-{version:06d}.json"


class LogOnlyAdapter:
    name = "Log-only"
    strategy_requested = "operation-log"

    def __init__(self, path: Path, **_: Any) -> None:
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self.base_path = path / "base.json"
        self.log_path = path / "commits.jsonl"
        self.version = 0
        self.state: dict[str, str] = {}
        self.work_examined: Optional[int] = None
        self.work_unit = "operations"
        self.strategy_selected = "operation-log"
        self.external_peak_memory: Optional[int] = None

    def initial_import(self, state: dict[str, str]) -> None:
        self.state = dict(state)
        self.version = 1
        durable_write(self.base_path, self.state)
        self.log_path.touch()

    def commit(self, mutations: tuple[Mutation, ...]) -> None:
        record = {
            "version": self.version + 1,
            "changes": [mutation.as_record() for mutation in mutations],
        }
        with self.log_path.open("ab") as stream:
            stream.write(canonical_bytes(record) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        apply_mutations(self.state, mutations)
        self.version += 1

    def _records(self) -> list[dict[str, Any]]:
        with self.log_path.open("r", encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]

    def checkout(self, version: int) -> bytes:
        if not 1 <= version <= self.version:
            raise KeyError(f"unknown version: {version}")
        with self.base_path.open("r", encoding="utf-8") as stream:
            state = json.load(stream)
        for record in self._records():
            if record["version"] > version:
                break
            for change in record["changes"]:
                if change["new_exists"]:
                    state[change["key"]] = change["new"]
                else:
                    del state[change["key"]]
        return canonical_state_bytes(state)

    def diff(self, left: int, right: int) -> bytes:
        if not 1 <= left <= right <= self.version:
            raise KeyError("versions must satisfy 1 <= left <= right <= HEAD")
        first: dict[str, dict[str, Any]] = {}
        final: dict[str, dict[str, Any]] = {}
        examined = 0
        for record in self._records():
            if left < record["version"] <= right:
                for change in record["changes"]:
                    examined += 1
                    first.setdefault(change["key"], change)
                    final[change["key"]] = change
        self.work_examined = examined
        changes = {
            key: (
                first[key]["old"] if first[key]["old_exists"] else None,
                latest["new"] if latest["new_exists"] else None,
            )
            for key, latest in final.items()
            if first[key]["old_exists"] != latest["new_exists"]
            or first[key]["old"] != latest["new"]
        }
        return canonical_diff_bytes(changes)

    def storage_bytes(self) -> int:
        return directory_size(self.path)

    def close(self) -> None:
        pass


class RevonAdapter:
    def __init__(
        self,
        path: Path,
        *,
        strategy: str,
        hybrid_threshold: int,
        branching_factor: int = 8,
        tree_depth: int = 4,
    ) -> None:
        if strategy not in {"merkle", "hybrid", "log"}:
            raise ValueError("invalid Revon strategy")
        self.path = path
        self.strategy_requested = strategy
        self.name = {
            "merkle": "Revon-M (forced Merkle)",
            "hybrid": "Revon-H",
            "log": "Revon-log calibration",
        }[strategy]
        self.repository = SQLiteRevonRepository.create(
            path / "revon.sqlite",
            branching_factor=branching_factor,
            tree_depth=tree_depth,
            hybrid_log_threshold=hybrid_threshold,
        )
        self.root: Optional[str] = None
        self.version = 0
        self.work_examined: Optional[int] = None
        self.work_unit = ""
        self.strategy_selected = strategy
        self.external_peak_memory: Optional[int] = None

    def initial_import(self, state: dict[str, str]) -> None:
        self.root = self.repository.commit(state, message="benchmark initial import")
        self.version = 1

    def commit(self, mutations: tuple[Mutation, ...]) -> None:
        if self.root is None:
            raise RuntimeError("initial import has not run")
        puts = {
            mutation.key: mutation.new_value
            for mutation in mutations
            if mutation.new_exists
        }
        deletes = {
            mutation.key for mutation in mutations if not mutation.new_exists
        }
        self.root = self.repository.apply_changes(
            self.root,
            puts=puts,
            deletes=deletes,
            message=f"benchmark version {self.version + 1}",
        )
        self.version += 1

    def checkout(self, version: int) -> bytes:
        return canonical_state_bytes(self.repository.checkout(version))

    def diff(self, left: int, right: int) -> bytes:
        entries = self.repository.diff_versions(left, right, self.strategy_requested)
        stats = self.repository.last_diff_stats
        self.strategy_selected = stats.strategy
        if stats.strategy == "log":
            self.work_examined = stats.log_operations_examined
            self.work_unit = "log operations"
        else:
            self.work_examined = stats.nodes_compared
            self.work_unit = "tree node pairs"
        return canonical_diff_bytes(
            {entry.key: (entry.old_value, entry.new_value) for entry in entries}
        )

    def storage_bytes(self) -> int:
        return directory_size(self.path)

    def close(self) -> None:
        self.repository.close()


class DoltUnavailableError(RuntimeError):
    pass


class DoltCommandError(RuntimeError):
    pass


class DoltAdapter:
    """Dolt CLI adapter; each SQL/VC operation is a real Dolt operation."""

    name = "Dolt"
    strategy_requested = "dolt-native"
    strategy_selected = "dolt-native"
    work_examined: Optional[int] = None
    work_unit = "not exposed by Dolt CLI"

    @staticmethod
    def executable() -> Optional[str]:
        return shutil.which("dolt")

    def __init__(self, path: Path, *, bulk_import: bool = False, **_: Any) -> None:
        executable = self.executable()
        if executable is None:
            raise DoltUnavailableError("dolt executable is not on PATH")
        self.executable_path = executable
        self.path = path
        self.bulk_import = bulk_import
        self.path.mkdir(parents=True, exist_ok=True)
        self.version = 0
        self.version_hashes: list[str] = []
        self._run(
            ["init", "--name", "Revon Benchmark", "--email", "benchmark@revon.local"]
        )
        self._run(
            [
                "sql",
                "-q",
                "CREATE TABLE records (id VARCHAR(255) PRIMARY KEY, payload LONGTEXT NOT NULL)",
            ]
        )

    @property
    def version_text(self) -> str:
        text = self._run(["version"]).stdout.strip().replace("\n", " ")
        match = re.search(r"\bdolt\s+version\s+([0-9]+(?:\.[0-9]+){1,3})\b", text, re.IGNORECASE)
        return f"Dolt {match.group(1)}" if match else text

    def _run(
        self, arguments: list[str], *, input_text: Optional[str] = None
    ) -> subprocess.CompletedProcess[str]:
        command = [self.executable_path, *arguments]
        process = subprocess.Popen(
            command,
            cwd=self.path,
            stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        stdout, stderr = process.communicate(input=input_text)
        result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        if result.returncode != 0:
            raise DoltCommandError(
                f"{' '.join(arguments)} failed ({result.returncode}): {stderr.strip()}"
            )
        return result

    @staticmethod
    def _literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def _commit_and_remember_hash(self) -> None:
        self._run(["add", "."])
        result = self._run(["commit", "-m", f"benchmark version {self.version}"])
        match = re.search(r"\b[a-z0-9]{20,64}\b", result.stdout, re.IGNORECASE)
        if match is None:
            raise DoltCommandError("Dolt commit did not return a commit hash")
        commit_hash = match.group(0)
        self.version_hashes.append(commit_hash)

    def initial_import(self, state: dict[str, str]) -> None:
        if self.bulk_import:
            import_file = self.path.parent.resolve() / "dolt-initial-import.csv"
            try:
                with import_file.open("w", newline="", encoding="utf-8") as stream:
                    writer = csv.writer(stream, lineterminator="\n")
                    writer.writerow(("id", "payload"))
                    writer.writerows(sorted(state.items()))
                self._run(["table", "import", "-r", "records", str(import_file)])
            finally:
                import_file.unlink(missing_ok=True)
        else:
            ordered = sorted(state.items())
            statements: list[str] = []
            for start in range(0, len(ordered), 1_000):
                rows = ",".join(
                    f"({self._literal(key)},{self._literal(value)})"
                    for key, value in ordered[start : start + 1_000]
                )
                statements.append(
                    f"INSERT INTO records (id,payload) VALUES {rows};"
                )
            self._run(["sql"], input_text="\n".join(statements))
        self.version = 1
        self._commit_and_remember_hash()

    def commit(self, mutations: tuple[Mutation, ...]) -> None:
        statements: list[str] = []
        puts = [mutation for mutation in mutations if mutation.new_exists]
        deletes = [mutation for mutation in mutations if not mutation.new_exists]
        if puts:
            rows = ",".join(
                f"({self._literal(change.key)},{self._literal(change.new_value)})"
                for change in puts
            )
            statements.append(
                "INSERT INTO records (id,payload) VALUES "
                + rows
                + " ON DUPLICATE KEY UPDATE payload=VALUES(payload);"
            )
        if deletes:
            keys = ",".join(self._literal(change.key) for change in deletes)
            statements.append(f"DELETE FROM records WHERE id IN ({keys});")
        self._run(["sql"], input_text="\n".join(statements))
        self.version += 1
        self._commit_and_remember_hash()

    def checkout(self, version: int) -> bytes:
        if not 1 <= version <= len(self.version_hashes):
            raise KeyError(f"unknown version: {version}")
        query = (
            "SELECT id,payload FROM records AS OF "
            + self._literal(self.version_hashes[version - 1])
            + " ORDER BY id"
        )
        output = self._run(["sql", "-r", "json", "-q", query]).stdout
        try:
            rows = json.loads(output)["rows"]
            state = {row["id"]: row["payload"] for row in rows}
            if any(not isinstance(k, str) or not isinstance(v, str) for k, v in state.items()):
                raise TypeError
            if len(state) != len(rows):
                raise TypeError
        except (ValueError, KeyError, TypeError) as exc:
            raise DoltCommandError("Dolt checkout did not return the expected JSON rows") from exc
        return canonical_state_bytes(state)

    @staticmethod
    def _parse_diff_json(output: str) -> dict[str, tuple[Optional[str], Optional[str]]]:
        try:
            document = json.loads(output)
            tables = document["tables"]
        except (ValueError, KeyError, TypeError) as exc:
            raise DoltCommandError("Dolt did not return a structured JSON diff") from exc
        if tables == []:
            return {}
        if not isinstance(tables, list) or len(tables) != 1:
            raise DoltCommandError("Dolt JSON diff did not contain exactly one table")
        table = tables[0]
        if (
            not isinstance(table, dict)
            or table.get("name") != "records"
            or table.get("schema_diff") != []
        ):
            raise DoltCommandError("Dolt diff changed the table schema or table identity")
        rows = table.get("data_diff")
        if not isinstance(rows, list):
            raise DoltCommandError("Dolt JSON diff has no data_diff list")
        changed: dict[str, tuple[Optional[str], Optional[str]]] = {}
        for row in rows:
            if not isinstance(row, dict):
                raise DoltCommandError("Dolt JSON diff contains a malformed row")
            old, new = row.get("from_row"), row.get("to_row")
            if not isinstance(old, dict) or not isinstance(new, dict) or not (old or new):
                raise DoltCommandError("Dolt JSON diff contains an empty or malformed change")
            for state in (old, new):
                if state and (set(state) != {"id", "payload"} or not all(
                    isinstance(value, str) for value in state.values()
                )):
                    raise DoltCommandError("Dolt JSON diff contains incomplete row values")
            key = old.get("id") or new.get("id")
            if not key:
                raise DoltCommandError("Dolt JSON diff contains an empty primary key")
            if old and new and old["id"] != new["id"]:
                raise DoltCommandError("Dolt JSON diff changed a primary key in one row")
            if key in changed:
                raise DoltCommandError(f"Dolt JSON diff repeats key {key!r}")
            before = old.get("payload")
            after = new.get("payload")
            if before == after:
                raise DoltCommandError(f"Dolt JSON diff reports an unchanged key {key!r}")
            changed[key] = (before, after)
        return changed

    def diff(self, left: int, right: int) -> bytes:
        if not 1 <= left <= right <= len(self.version_hashes):
            raise KeyError("versions must satisfy 1 <= left <= right <= HEAD")
        output = self._run(
            ["diff", "-r", "json", self.version_hashes[left - 1], self.version_hashes[right - 1], "records"]
        ).stdout
        return canonical_diff_bytes(self._parse_diff_json(output))

    def storage_bytes(self) -> int:
        return directory_size(self.path)

    def close(self) -> None:
        pass
