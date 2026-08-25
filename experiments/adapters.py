"""Durable model adapters used by the final Chronos experiment harness."""

from __future__ import annotations

import csv
import io
import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Optional

from sqlite_store import SQLiteChronosRepository

from .workloads import Mutation, apply_mutations


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


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

    def checkout(self, version: int) -> dict[str, str]:
        with self._version_path(version).open("r", encoding="utf-8") as stream:
            return json.load(stream)

    def diff(self, left: int, right: int) -> list[str]:
        left_state, right_state = self.checkout(left), self.checkout(right)
        keys = set(left_state) | set(right_state)
        self.work_examined = len(keys)
        missing = object()
        return sorted(
            key
            for key in keys
            if left_state.get(key, missing) != right_state.get(key, missing)
        )

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

    def checkout(self, version: int) -> dict[str, str]:
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
        return state

    def diff(self, left: int, right: int) -> list[str]:
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
        return sorted(
            key
            for key, latest in final.items()
            if first[key]["old_exists"] != latest["new_exists"]
            or first[key]["old"] != latest["new"]
        )

    def storage_bytes(self) -> int:
        return directory_size(self.path)

    def close(self) -> None:
        pass


class ChronosAdapter:
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
            raise ValueError("invalid Chronos strategy")
        self.path = path
        self.strategy_requested = strategy
        self.name = {
            "merkle": "Chronos-M (forced Merkle)",
            "hybrid": "Chronos-H",
            "log": "Chronos-log calibration",
        }[strategy]
        self.repository = SQLiteChronosRepository.create(
            path / "chronos.sqlite",
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

    def checkout(self, version: int) -> dict[str, str]:
        return self.repository.checkout(version)

    def diff(self, left: int, right: int) -> list[str]:
        entries = self.repository.diff_versions(left, right, self.strategy_requested)
        stats = self.repository.last_diff_stats
        self.strategy_selected = stats.strategy
        if stats.strategy == "log":
            self.work_examined = stats.log_operations_examined
            self.work_unit = "log operations"
        else:
            self.work_examined = stats.nodes_compared
            self.work_unit = "tree node pairs"
        return [entry.key for entry in entries]

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

    def __init__(self, path: Path, **_: Any) -> None:
        executable = self.executable()
        if executable is None:
            raise DoltUnavailableError("dolt executable is not on PATH")
        self.executable_path = executable
        self.path = path
        self.path.mkdir(parents=True, exist_ok=True)
        self.version = 0
        self.external_peak_memory: Optional[int] = None
        self._operation_peaks: list[int] = []
        self._run(
            ["init", "--name", "Chronos Benchmark", "--email", "benchmark@chronos.local"]
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
        return self._run(["version"]).stdout.strip().replace("\n", " ")

    def _begin_operation(self) -> None:
        self._operation_peaks = []
        self.external_peak_memory = None

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
        peak: list[int] = []
        stop = threading.Event()

        def sample() -> None:
            try:
                import psutil  # type: ignore[import-not-found]

                tracked = psutil.Process(process.pid)
                while not stop.is_set():
                    processes = [tracked, *tracked.children(recursive=True)]
                    peak.append(
                        sum(
                            child.memory_info().rss
                            for child in processes
                            if child.is_running()
                        )
                    )
                    time.sleep(0.002)
            except (ImportError, OSError):
                return

        monitor = threading.Thread(target=sample, daemon=True)
        monitor.start()
        stdout, stderr = process.communicate(input=input_text)
        stop.set()
        monitor.join(timeout=0.1)
        if peak:
            self._operation_peaks.append(max(peak))
            self.external_peak_memory = max(self._operation_peaks)
        result = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        if result.returncode != 0:
            raise DoltCommandError(
                f"{' '.join(arguments)} failed ({result.returncode}): {stderr.strip()}"
            )
        return result

    @staticmethod
    def _literal(value: str) -> str:
        return "'" + value.replace("'", "''") + "'"

    def _commit_and_tag(self) -> None:
        self._run(["add", "."])
        self._run(["commit", "-m", f"benchmark version {self.version}"])
        self._run(["tag", f"chronos-v{self.version}"])

    def initial_import(self, state: dict[str, str]) -> None:
        self._begin_operation()
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
        self._commit_and_tag()

    def commit(self, mutations: tuple[Mutation, ...]) -> None:
        self._begin_operation()
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
        self._commit_and_tag()

    def checkout(self, version: int) -> dict[str, str]:
        self._begin_operation()
        query = (
            "SELECT id,payload FROM records AS OF "
            + self._literal(f"chronos-v{version}")
            + " ORDER BY id"
        )
        output = self._run(["sql", "-r", "csv", "-q", query]).stdout
        header = output.find("id,payload")
        if header < 0:
            raise DoltCommandError("Dolt CSV query did not return the expected header")
        return {row["id"]: row["payload"] for row in csv.DictReader(io.StringIO(output[header:]))}

    def diff(self, left: int, right: int) -> None:
        self._begin_operation()
        self._run(
            ["diff", f"chronos-v{left}", f"chronos-v{right}", "records"]
        )
        return None

    def storage_bytes(self) -> int:
        return directory_size(self.path)

    def close(self) -> None:
        pass
