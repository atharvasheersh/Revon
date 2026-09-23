"""Deterministic workloads shared by every experimental adapter."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class Mutation:
    """One unambiguous key transition in a generated workload."""

    key: str
    old_exists: bool
    old_value: Any
    new_exists: bool
    new_value: Any

    def as_record(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "old_exists": self.old_exists,
            "old": self.old_value,
            "new_exists": self.new_exists,
            "new": self.new_value,
        }


@dataclass(frozen=True)
class WorkloadSpec:
    name: str
    rows: int
    commits: int
    changes_per_commit: int
    seed: int
    payload_bytes: int = 32
    locality: str = "spread"

    def validate(self) -> None:
        if self.rows < 1:
            raise ValueError("rows must be positive")
        if self.commits < 1:
            raise ValueError("commits must be positive")
        if not 1 <= self.changes_per_commit <= self.rows:
            raise ValueError("changes_per_commit must be between 1 and rows")
        if self.payload_bytes < 8:
            raise ValueError("payload_bytes must be at least 8")
        if self.locality not in {
            "spread",
            "hot",  # legacy alias retained so schema-1-3 evidence can be rechecked
            "application-key-local",
            "range-local",
            "repeated-key",
            "hash-route-local",
        }:
            raise ValueError("unknown workload locality")


@dataclass(frozen=True)
class Workload:
    spec: WorkloadSpec
    initial: dict[str, str]
    batches: tuple[tuple[Mutation, ...], ...]
    states: tuple[dict[str, str], ...]
    digest: str

    @property
    def expected_diff_keys(self) -> list[str]:
        missing = object()
        first, last = self.states[0], self.states[-1]
        return sorted(
            key
            for key in set(first) | set(last)
            if first.get(key, missing) != last.get(key, missing)
        )


def _value(key: str, revision: int, payload_bytes: int) -> str:
    prefix = f"r{revision}:"
    digest = hashlib.sha256(f"{revision}:{key}".encode("utf-8")).hexdigest()
    repeated = digest * ((payload_bytes // len(digest)) + 1)
    return (prefix + repeated)[:payload_bytes]


def apply_mutations(state: dict[str, str], mutations: Iterable[Mutation]) -> None:
    for mutation in mutations:
        if mutation.new_exists:
            state[mutation.key] = mutation.new_value
        else:
            del state[mutation.key]


def build_workload(spec: WorkloadSpec) -> Workload:
    """Build repeatable mixed update/delete/insert batches from one seed.

    Each batch is 80% updates, 10% deletes, and 10% inserts (with sensible
    rounding for small batches). All adapters receive these exact objects.
    """

    spec.validate()
    rng = random.Random(spec.seed)
    initial = {
        f"key-{index:09d}": _value(f"key-{index:09d}", 0, spec.payload_bytes)
        for index in range(spec.rows)
    }
    state = dict(initial)
    states: list[dict[str, str]] = [dict(state)]
    batches: list[tuple[Mutation, ...]] = []
    next_key = spec.rows
    route_prefix_bits = 9
    initial_route_buckets: dict[int, list[str]] = {}
    if spec.locality == "hash-route-local":
        for key in initial:
            route = int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest(), "big") >> (256 - route_prefix_bits)
            initial_route_buckets.setdefault(route, []).append(key)
    route_bucket = (
        max(initial_route_buckets, key=lambda bucket: (len(initial_route_buckets[bucket]), -bucket))
        if initial_route_buckets
        else None
    )

    for revision in range(1, spec.commits + 1):
        change_count = spec.changes_per_commit
        inserts = 1 if change_count >= 10 else 0
        deletes = 1 if change_count >= 10 else 0
        updates = change_count - inserts - deletes

        existing = sorted(state)
        if spec.locality in {"hot", "application-key-local"}:
            hot_size = max(change_count, min(len(existing), max(16, spec.rows // 100)))
            candidates = existing[:hot_size]
        elif spec.locality == "repeated-key":
            hot_size = min(len(existing), max(2 * change_count, 32))
            candidates = existing[:hot_size]
        elif spec.locality == "hash-route-local":
            candidates = [
                key
                for key in existing
                if int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest(), "big")
                >> (256 - route_prefix_bits)
                == route_bucket
            ]
        else:
            candidates = existing
        selection_count = updates + deletes
        if spec.locality == "range-local":
            start = rng.randrange(len(candidates) - selection_count + 1)
            selected = candidates[start : start + selection_count]
        else:
            selected = rng.sample(candidates, selection_count)

        batch: list[Mutation] = []
        for key in selected[:updates]:
            old = state[key]
            new = _value(key, revision, spec.payload_bytes)
            batch.append(Mutation(key, True, old, True, new))
        for key in selected[updates:]:
            batch.append(Mutation(key, True, state[key], False, None))
        for _ in range(inserts):
            key = f"key-{next_key:09d}"
            next_key += 1
            batch.append(
                Mutation(key, False, None, True, _value(key, revision, spec.payload_bytes))
            )

        batch.sort(key=lambda mutation: mutation.key)
        apply_mutations(state, batch)
        batches.append(tuple(batch))
        states.append(dict(state))

    digest_input = {
        "spec": spec.__dict__,
        "initial": initial,
        "batches": [[mutation.as_record() for mutation in batch] for batch in batches],
    }
    encoded = json.dumps(
        digest_input, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    return Workload(
        spec,
        initial,
        tuple(batches),
        tuple(states),
        hashlib.sha256(encoded).hexdigest(),
    )


def profile_specs(profile: str, seed: int, *, phase: str) -> list[WorkloadSpec]:
    """Return intentionally separate calibration and evaluation workloads."""

    if profile not in {"smoke", "paper"}:
        raise ValueError("profile must be 'smoke' or 'paper'")
    if phase == "calibration":
        changes = (1, 8, 32) if profile == "smoke" else (1, 4, 16, 64, 256, 1024)
        rows = 1_000 if profile == "smoke" else 10_000
        return [
            WorkloadSpec(
                name=f"calibration-c{count}",
                rows=rows,
                commits=4,
                changes_per_commit=count,
                seed=seed + index,
            )
            for index, count in enumerate(changes)
        ]
    if phase != "evaluation":
        raise ValueError("phase must be 'calibration' or 'evaluation'")
    if profile == "smoke":
        return [WorkloadSpec("smoke-spread", 1_000, 4, 10, seed)]
    return [
        WorkloadSpec("small-sparse", 1_000, 10, 10, seed),
        WorkloadSpec("medium-sparse", 10_000, 10, 10, seed + 1),
        WorkloadSpec("medium-dense", 10_000, 10, 1_000, seed + 2),
        WorkloadSpec("large-sparse", 100_000, 10, 100, seed + 3),
        WorkloadSpec(
            "large-application-key-local",
            100_000,
            10,
            100,
            seed + 4,
            locality="application-key-local",
        ),
        WorkloadSpec(
            "large-range-local", 100_000, 10, 100, seed + 5, locality="range-local"
        ),
        WorkloadSpec(
            "large-repeated-key", 100_000, 10, 100, seed + 6, locality="repeated-key"
        ),
        WorkloadSpec(
            "large-hash-route-local",
            100_000,
            10,
            100,
            seed + 7,
            locality="hash-route-local",
        ),
    ]
