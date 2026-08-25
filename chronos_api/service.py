"""Framework-independent backend service for Chronos repositories."""

from __future__ import annotations

import re
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Optional

from sqlite_store import SQLiteChronosRepository


REPOSITORY_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")


class APIError(RuntimeError):
    """An expected API failure with an HTTP-compatible status code."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message

    def as_dict(self) -> dict[str, Any]:
        return {"error": {"code": self.code, "message": self.message}}


class RepositoryManager:
    """Resolve server-owned repository paths and serialize local access."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self._guard = threading.Lock()
        self._locks: dict[str, threading.RLock] = {}

    @staticmethod
    def validate_name(name: str) -> str:
        if not isinstance(name, str) or not REPOSITORY_NAME.fullmatch(name):
            raise APIError(
                400,
                "invalid_repository_name",
                "repository names must use 1-64 lowercase letters, digits, '-' or '_'",
            )
        return name

    def path(self, name: str) -> Path:
        valid = self.validate_name(name)
        return self.root / f"{valid}.chronos.db"

    def require_path(self, name: str) -> Path:
        path = self.path(name)
        if not path.is_file():
            raise APIError(404, "repository_not_found", f"repository '{name}' does not exist")
        return path

    @contextmanager
    def locked(self, name: str) -> Iterator[None]:
        valid = self.validate_name(name)
        with self._guard:
            lock = self._locks.setdefault(valid, threading.RLock())
        with lock:
            yield

    def list_names(self) -> list[str]:
        suffix = ".chronos.db"
        return sorted(
            name
            for path in self.root.glob(f"*{suffix}")
            if path.is_file()
            if (name := path.name[: -len(suffix)])
            if REPOSITORY_NAME.fullmatch(name)
        )


class ChronosService:
    """Validated operations shared by the HTTP layer and unit tests."""

    def __init__(self, repository_root: str | Path) -> None:
        self.repositories = RepositoryManager(repository_root)

    @staticmethod
    def _require_object(payload: Any) -> Mapping[str, Any]:
        if not isinstance(payload, Mapping):
            raise APIError(400, "invalid_json", "request body must be a JSON object")
        return payload

    @staticmethod
    def _integer(
        value: Any,
        field: str,
        *,
        minimum: int = 0,
        maximum: Optional[int] = None,
    ) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise APIError(400, "invalid_parameter", f"'{field}' must be an integer")
        if value < minimum or (maximum is not None and value > maximum):
            limit = (
                f" between {minimum} and {maximum}"
                if maximum is not None
                else f" at least {minimum}"
            )
            raise APIError(400, "invalid_parameter", f"'{field}' must be{limit}")
        return value

    @staticmethod
    def _commit_payload(repository: SQLiteChronosRepository) -> dict[str, Any]:
        if repository.head is None:
            return {"head": None, "head_hash": None, "root_hash": None}
        commit = repository.commits[repository.head]
        stats = repository.commit_stats[repository.head]
        return {
            "head": repository.head,
            "head_hash": repository.head_hash,
            "root_hash": commit.root_hash,
            "commit": ChronosService._serialize_commit(commit),
            "commit_metrics": {
                "changed_keys": stats.changed_keys,
                "new_nodes": stats.new_nodes,
                "reused_nodes": stats.reused_nodes,
                "bytes_written": stats.bytes_written,
                "shared_percent": stats.shared_percent,
            },
        }

    @staticmethod
    def _serialize_commit(commit: Any) -> dict[str, Any]:
        timestamp = datetime.fromtimestamp(
            commit.timestamp_ns / 1_000_000_000, timezone.utc
        )
        return {
            "version": commit.version,
            "commit_hash": commit.commit_hash,
            "root_hash": commit.root_hash,
            "parent": commit.parent,
            "parent_hash": commit.parent_hash,
            "message": commit.message,
            "timestamp_ns": commit.timestamp_ns,
            "timestamp_utc": timestamp.isoformat(),
            "changeset_hash": commit.changeset_hash,
        }

    @staticmethod
    def _diff_metrics(repository: SQLiteChronosRepository) -> dict[str, Any]:
        stats = repository.last_diff_stats
        if stats.strategy == "log":
            examined = stats.log_operations_examined
            unit = "log operations"
        else:
            examined = stats.nodes_compared
            unit = "tree node pairs"
        return {
            "strategy_selected": stats.strategy,
            "work_examined": examined,
            "work_unit": unit,
            "nodes_compared": stats.nodes_compared,
            "matching_subtrees_skipped": stats.matching_subtrees_skipped,
            "leaf_entries_examined": stats.leaf_entries_examined,
            "log_operations_examined": stats.log_operations_examined,
        }

    @staticmethod
    def _state_from_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
        has_state = "state" in payload
        has_rows = "rows" in payload
        if has_state == has_rows:
            raise APIError(
                400,
                "invalid_dataset",
                "provide exactly one of 'state' or 'rows'",
            )
        if has_state:
            state = payload["state"]
            if not isinstance(state, Mapping) or any(
                not isinstance(key, str) for key in state
            ):
                raise APIError(
                    400,
                    "invalid_dataset",
                    "'state' must be an object with string keys",
                )
            return dict(state)

        rows = payload["rows"]
        primary_key = payload.get("primary_key")
        if not isinstance(rows, list) or not isinstance(primary_key, str):
            raise APIError(
                400,
                "invalid_dataset",
                "row imports require a 'rows' array and string 'primary_key'",
            )
        state: dict[str, Any] = {}
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, Mapping):
                raise APIError(400, "invalid_dataset", f"row {index} is not an object")
            if primary_key not in row:
                raise APIError(
                    400,
                    "invalid_dataset",
                    f"row {index} is missing primary key '{primary_key}'",
                )
            key = str(row[primary_key])
            if key in state:
                raise APIError(409, "duplicate_primary_key", f"duplicate primary key '{key}'")
            state[key] = dict(row)
        return state

    def list_repositories(self) -> dict[str, Any]:
        repositories: list[dict[str, Any]] = []
        for name in self.repositories.list_names():
            with self.repositories.locked(name):
                try:
                    with SQLiteChronosRepository.open(
                        self.repositories.require_path(name), verify=False
                    ) as repository:
                        repositories.append(
                            {
                                "name": name,
                                "head": repository.head,
                                "head_hash": repository.head_hash,
                                "versions": len(repository.versions),
                                "storage_bytes": repository.path.stat().st_size,
                            }
                        )
                except Exception as exc:
                    repositories.append(
                        {"name": name, "status": "unreadable", "error": str(exc)}
                    )
        return {"repositories": repositories, "count": len(repositories)}

    def create_repository(self, payload: Any) -> tuple[int, dict[str, Any]]:
        body = self._require_object(payload)
        name = self.repositories.validate_name(body.get("name"))
        branching_factor = self._integer(
            body.get("branching_factor", 8), "branching_factor", minimum=2
        )
        tree_depth = self._integer(body.get("tree_depth", 4), "tree_depth", minimum=1)
        threshold = self._integer(
            body.get("hybrid_log_threshold", 128),
            "hybrid_log_threshold",
            minimum=0,
        )
        path = self.repositories.path(name)
        with self.repositories.locked(name):
            if path.exists():
                raise APIError(409, "repository_exists", f"repository '{name}' already exists")
            try:
                repository = SQLiteChronosRepository.create(
                    path,
                    branching_factor=branching_factor,
                    tree_depth=tree_depth,
                    hybrid_log_threshold=threshold,
                )
            except ValueError as exc:
                raise APIError(400, "invalid_configuration", str(exc)) from exc
            repository.close()
        return 201, {
            "name": name,
            "status": "created",
            "head": None,
            "configuration": {
                "branching_factor": branching_factor,
                "tree_depth": tree_depth,
                "hybrid_log_threshold": threshold,
            },
        }

    def open_repository(self, name: str) -> dict[str, Any]:
        with self.repositories.locked(name):
            with SQLiteChronosRepository.open(
                self.repositories.require_path(name), verify=False
            ) as repository:
                report = repository.verify_integrity()
                return {
                    "name": name,
                    "status": "open",
                    **self._commit_payload(repository),
                    "versions": len(repository.versions),
                    "storage_bytes": repository.path.stat().st_size,
                    "integrity": {
                        "objects": report.objects,
                        "nodes": report.nodes,
                        "changesets": report.changesets,
                        "commits": report.commits,
                        "versions": report.versions,
                    },
                }

    def import_dataset(self, name: str, payload: Any) -> tuple[int, dict[str, Any]]:
        body = self._require_object(payload)
        state = self._state_from_payload(body)
        message = body.get("message")
        if message is not None and not isinstance(message, str):
            raise APIError(400, "invalid_parameter", "'message' must be a string")
        with self.repositories.locked(name):
            with SQLiteChronosRepository.open(
                self.repositories.require_path(name), verify=True
            ) as repository:
                started = time.perf_counter_ns()
                try:
                    repository.commit(state, message=message or "Import dataset")
                except (TypeError, ValueError) as exc:
                    raise APIError(400, "invalid_dataset", str(exc)) from exc
                elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
                result = {
                    "name": name,
                    "status": "imported",
                    "rows": len(state),
                    "operation_ms": elapsed_ms,
                    "storage_bytes": repository.path.stat().st_size,
                    **self._commit_payload(repository),
                }
        return 201, result

    def commit_batch(self, name: str, payload: Any) -> tuple[int, dict[str, Any]]:
        body = self._require_object(payload)
        puts = body.get("puts", {})
        deletes = body.get("deletes", [])
        message = body.get("message")
        if not isinstance(puts, Mapping) or any(
            not isinstance(key, str) for key in puts
        ):
            raise APIError(400, "invalid_batch", "'puts' must be an object with string keys")
        if not isinstance(deletes, list) or any(
            not isinstance(key, str) for key in deletes
        ):
            raise APIError(400, "invalid_batch", "'deletes' must be an array of strings")
        if len(deletes) != len(set(deletes)):
            raise APIError(400, "invalid_batch", "'deletes' contains duplicate keys")
        if set(puts) & set(deletes):
            raise APIError(400, "invalid_batch", "a key cannot be put and deleted together")
        if message is not None and not isinstance(message, str):
            raise APIError(400, "invalid_parameter", "'message' must be a string")

        with self.repositories.locked(name):
            with SQLiteChronosRepository.open(
                self.repositories.require_path(name), verify=True
            ) as repository:
                if repository.head is None:
                    raise APIError(
                        409,
                        "empty_repository",
                        "import a dataset before committing changes",
                    )
                base_version = body.get("base_version", repository.head)
                base_version = self._integer(base_version, "base_version", minimum=1)
                if base_version != repository.head:
                    raise APIError(
                        409,
                        "stale_base_version",
                        f"base version {base_version} is stale; HEAD is {repository.head}",
                    )
                root = repository.versions[base_version]
                started = time.perf_counter_ns()
                try:
                    repository.apply_changes(
                        root,
                        puts=dict(puts),
                        deletes=deletes,
                        message=message or "Commit batch",
                    )
                except (KeyError, TypeError, ValueError) as exc:
                    raise APIError(400, "invalid_batch", str(exc)) from exc
                elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
                result = {
                    "name": name,
                    "status": "committed",
                    "operation_ms": elapsed_ms,
                    "storage_bytes": repository.path.stat().st_size,
                    **self._commit_payload(repository),
                }
        return 201, result

    def history(self, name: str) -> dict[str, Any]:
        with self.repositories.locked(name):
            with SQLiteChronosRepository.open(
                self.repositories.require_path(name), verify=True
            ) as repository:
                commits = [self._serialize_commit(commit) for commit in repository.log()]
                return {
                    "name": name,
                    "head": repository.head,
                    "head_hash": repository.head_hash,
                    "count": len(commits),
                    "order": "newest-first",
                    "commits": commits,
                }

    def checkout(
        self,
        name: str,
        version: int,
        *,
        offset: int = 0,
        limit: Optional[int] = None,
    ) -> dict[str, Any]:
        version = self._integer(version, "version", minimum=1)
        offset = self._integer(offset, "offset", minimum=0)
        if limit is not None:
            limit = self._integer(limit, "limit", minimum=1, maximum=100_000)
        with self.repositories.locked(name):
            with SQLiteChronosRepository.open(
                self.repositories.require_path(name), verify=True
            ) as repository:
                try:
                    complete = repository.checkout(version)
                except KeyError as exc:
                    raise APIError(404, "version_not_found", str(exc)) from exc
                keys = sorted(complete)
                selected = keys[offset:] if limit is None else keys[offset : offset + limit]
                state = {key: complete[key] for key in selected}
                return {
                    "name": name,
                    "version": version,
                    "commit_hash": repository.version_commits[version],
                    "root_hash": repository.versions[version],
                    "total_rows": len(complete),
                    "offset": offset,
                    "limit": limit,
                    "returned_rows": len(state),
                    "truncated": len(state) < max(0, len(complete) - offset),
                    "state": state,
                }

    def compare(
        self,
        name: str,
        left: int,
        right: int,
        strategy: str = "hybrid",
    ) -> dict[str, Any]:
        left = self._integer(left, "from", minimum=1)
        right = self._integer(right, "to", minimum=1)
        if strategy not in {"hybrid", "log", "merkle"}:
            raise APIError(400, "invalid_strategy", "strategy must be hybrid, log, or merkle")
        with self.repositories.locked(name):
            with SQLiteChronosRepository.open(
                self.repositories.require_path(name), verify=True
            ) as repository:
                started = time.perf_counter_ns()
                try:
                    differences = repository.diff_versions(left, right, strategy)
                except KeyError as exc:
                    raise APIError(404, "version_not_found", str(exc)) from exc
                except ValueError as exc:
                    raise APIError(400, "invalid_comparison", str(exc)) from exc
                elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000
                return {
                    "name": name,
                    "from_version": left,
                    "to_version": right,
                    "strategy_requested": strategy,
                    "changed_keys": len(differences),
                    "differences": [
                        {
                            "key": entry.key,
                            "change_type": entry.change_type,
                            "old_value": entry.old_value,
                            "new_value": entry.new_value,
                        }
                        for entry in differences
                    ],
                    "diff_ms": elapsed_ms,
                    "diff_metrics": self._diff_metrics(repository),
                }

    def metrics(
        self,
        name: str,
        *,
        left: Optional[int] = None,
        right: Optional[int] = None,
        strategy: str = "hybrid",
    ) -> dict[str, Any]:
        with self.repositories.locked(name):
            path = self.repositories.require_path(name)
            with SQLiteChronosRepository.open(path, verify=True) as repository:
                result: dict[str, Any] = {
                    "name": name,
                    "head": repository.head,
                    "head_hash": repository.head_hash,
                    "versions": len(repository.versions),
                    "storage_bytes": path.stat().st_size,
                    "commit_metrics": [
                        {
                            "version": version,
                            "changed_keys": stats.changed_keys,
                            "new_nodes": stats.new_nodes,
                            "reused_nodes": stats.reused_nodes,
                            "bytes_written": stats.bytes_written,
                            "shared_percent": stats.shared_percent,
                        }
                        for version, stats in sorted(repository.commit_stats.items())
                    ],
                }
                if (left is None) != (right is None):
                    raise APIError(
                        400,
                        "invalid_comparison",
                        "metrics requires both 'from' and 'to', or neither",
                    )
                if left is not None and right is not None:
                    comparison = self.compare(name, left, right, strategy)
                    result["comparison"] = {
                        "from_version": left,
                        "to_version": right,
                        "strategy_requested": strategy,
                        "changed_keys": comparison["changed_keys"],
                        "diff_ms": comparison["diff_ms"],
                        **comparison["diff_metrics"],
                    }
                return result
