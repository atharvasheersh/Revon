from __future__ import annotations

import csv
import hashlib
import json
import shutil
from types import SimpleNamespace
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from experiments.adapters import (
    DoltAdapter,
    DoltCommandError,
    canonical_diff_bytes,
    canonical_state_bytes,
    decode_diff_bytes,
)
from experiments.final_benchmark import (
    _blocked_model_order,
    _run_trial_local,
    execute,
    run_trial,
)
from experiments.workloads import WorkloadSpec, build_workload


class WorkloadTests(unittest.TestCase):
    def test_seed_produces_identical_workload_and_digest(self) -> None:
        spec = WorkloadSpec("repeatable", 100, 3, 10, 42)

        first = build_workload(spec)
        second = build_workload(spec)

        self.assertEqual(first, second)
        self.assertEqual(len(first.batches), 3)
        self.assertTrue(
            all(
                len(value.encode("utf-8")) == 32
                for value in first.initial.values()
            )
        )
        self.assertTrue(any(not change.new_exists for change in first.batches[0]))
        self.assertTrue(any(not change.old_exists for change in first.batches[0]))

    def test_different_seed_changes_workload_digest(self) -> None:
        first = build_workload(WorkloadSpec("first", 100, 2, 10, 1))
        second = build_workload(WorkloadSpec("second", 100, 2, 10, 2))

        self.assertNotEqual(first.digest, second.digest)

    def test_locality_workloads_separate_key_range_and_hash_route_patterns(self) -> None:
        range_workload = build_workload(
            WorkloadSpec("range", 1_000, 3, 10, 31, locality="range-local")
        )
        range_keys = [
            int(change.key.rsplit("-", 1)[1])
            for change in range_workload.batches[0]
            if change.old_exists
        ]
        self.assertEqual(max(range_keys) - min(range_keys) + 1, len(range_keys))

        repeated = build_workload(
            WorkloadSpec("repeated", 1_000, 3, 10, 32, locality="repeated-key")
        )
        first_keys = {change.key for change in repeated.batches[0] if change.old_exists}
        second_keys = {change.key for change in repeated.batches[1] if change.old_exists}
        self.assertTrue(first_keys & second_keys)

        routed = build_workload(
            WorkloadSpec("routed", 10_000, 2, 10, 33, locality="hash-route-local")
        )
        route_prefixes = {
            int.from_bytes(hashlib.sha256(change.key.encode()).digest(), "big") >> 247
            for change in routed.batches[0]
            if change.old_exists
        }
        self.assertEqual(len(route_prefixes), 1)
        self.assertEqual(len(routed.expected_diff_keys), len(set(routed.expected_diff_keys)))


class HarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tmp") / f"experiment-test-{uuid.uuid4().hex}"
        self.root.mkdir(parents=True)
        self.workload = build_workload(WorkloadSpec("unit", 100, 2, 10, 7))

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_all_python_adapters_match_same_oracle(self) -> None:
        for model in ("snapshot", "log", "revon-m", "revon-h"):
            with self.subTest(model=model):
                record = run_trial(
                    run_id="test",
                    phase="evaluation",
                    workload=self.workload,
                    model_key=model,
                    trial_kind="measured",
                    trial=1,
                    threshold=8,
                    scratch_root=self.root,
                )
                self.assertEqual(record.status, "ok", record.notes)
                self.assertTrue(record.correctness)
                self.assertEqual(record.changed_keys, len(self.workload.expected_diff_keys))
                self.assertGreater(record.storage_bytes or 0, 0)
                self.assertGreater(record.process_tree_peak_rss_bytes or 0, 0)

    def test_missing_dolt_is_recorded_not_fabricated(self) -> None:
        with patch("experiments.adapters.shutil.which", return_value=None):
            record = _run_trial_local(
                run_id="test",
                phase="evaluation",
                workload=self.workload,
                model_key="dolt",
                trial_kind="measured",
                trial=1,
                threshold=8,
                scratch_root=self.root,
            )

        self.assertEqual(record.status, "unavailable")
        self.assertIsNone(record.diff_ms)
        self.assertIsNone(record.correctness)

    def test_dolt_json_diff_parses_observed_old_and_new_values(self) -> None:
        output = ('{"tables":[{"name":"records","schema_diff":[],"data_diff":['
                  '{"from_row":{"id":"a","payload":"old"},'
                  '"to_row":{"id":"a","payload":"new"}},'
                  '{"from_row":{},"to_row":{"id":"b","payload":"added"}},'
                  '{"from_row":{"id":"c","payload":"deleted"},"to_row":{}}]}]}')
        self.assertEqual(
            DoltAdapter._parse_diff_json(output),
            {"a": ("old", "new"), "b": (None, "added"), "c": ("deleted", None)},
        )
        with self.assertRaises(DoltCommandError):
            DoltAdapter._parse_diff_json(output.replace('"payload":"new"', '"payload":"old"'))

    def test_dolt_version_discards_volatile_update_warning(self) -> None:
        adapter = object.__new__(DoltAdapter)
        with patch.object(
            DoltAdapter,
            "_run",
            return_value=SimpleNamespace(
                stdout="dolt version 2.3.1 Warning: newer version available; extra line"
            ),
        ):
            self.assertEqual(adapter.version_text, "Dolt 2.3.1")

    def test_dolt_trial_validates_observed_diff(self) -> None:
        if DoltAdapter.executable() is None:
            self.skipTest("Dolt is not installed")
        record = run_trial(
            run_id="test",
            phase="evaluation",
            workload=self.workload,
            model_key="dolt",
            trial_kind="measured",
            trial=1,
            threshold=8,
            scratch_root=self.root,
        )
        self.assertEqual(record.status, "ok", record.notes)
        self.assertTrue(record.correctness)
        self.assertEqual(record.changed_keys, len(self.workload.expected_diff_keys))

    def test_dolt_bulk_import_trial_matches_oracle(self) -> None:
        if DoltAdapter.executable() is None:
            self.skipTest("Dolt is not installed")
        record = run_trial(
            run_id="test",
            phase="evaluation",
            workload=self.workload,
            model_key="dolt-bulk",
            trial_kind="measured",
            trial=1,
            threshold=8,
            scratch_root=self.root,
        )
        self.assertEqual(record.status, "ok", record.notes)
        self.assertTrue(record.correctness)
        self.assertEqual(record.changed_keys, len(self.workload.expected_diff_keys))

    def test_dolt_trial_rejects_wrong_diff_values(self) -> None:
        if DoltAdapter.executable() is None:
            self.skipTest("Dolt is not installed")
        with patch.object(
            DoltAdapter,
            "diff",
            return_value=canonical_diff_bytes({"wrong": (None, "value")}),
        ):
            record = _run_trial_local(
                run_id="test",
                phase="evaluation",
                workload=self.workload,
                model_key="dolt",
                trial_kind="measured",
                trial=1,
                threshold=8,
                scratch_root=self.root,
            )
        self.assertEqual(record.status, "error")
        self.assertIsNone(record.correctness)
        self.assertIn("diff disagrees", record.notes)

    def test_common_diff_contract_is_sorted_and_contains_value_hashes(self) -> None:
        result = canonical_diff_bytes({"z": ("old", "new"), "a": (None, "add")})
        decoded = decode_diff_bytes(result)
        self.assertEqual(list(decoded), ["a", "z"])
        self.assertIsNone(decoded["a"][0])
        self.assertIsNotNone(decoded["a"][1])
        self.assertNotIn(b'"old"', result)

    def test_dolt_commit_uses_hashes_without_timed_tags(self) -> None:
        if DoltAdapter.executable() is None:
            self.skipTest("Dolt is not installed")
        adapter = DoltAdapter(self.root / "dolt-hash-check")
        try:
            adapter.initial_import(self.workload.initial)
            adapter.commit(self.workload.batches[0])
            self.assertEqual(len(adapter.version_hashes), 2)
            self.assertEqual(
                adapter.checkout(1), canonical_state_bytes(self.workload.states[0])
            )
            self.assertNotIn("revon-v", adapter._run(["tag"]).stdout)
        finally:
            adapter.close()

    def test_smoke_execution_writes_raw_summary_and_manifest(self) -> None:
        output = self.root / "results"

        records, threshold = execute(
            profile="smoke",
            output_dir=output,
            warmups=0,
            trials=1,
            seed=123,
            models=("snapshot", "log", "revon-m", "revon-h"),
        )

        self.assertGreaterEqual(threshold, 0)
        self.assertTrue(all(record.status == "ok" for record in records))
        with (output / "raw_results.csv").open(newline="", encoding="utf-8") as stream:
            raw = list(csv.DictReader(stream))
        with (output / "summary.csv").open(newline="", encoding="utf-8") as stream:
            summary = list(csv.DictReader(stream))
        manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(len(raw), len(records))
        self.assertTrue(summary)
        self.assertEqual(manifest["hybrid_threshold_operations"], threshold)
        self.assertEqual(manifest["base_seed"], 123)
        self.assertEqual(
            sorted(int(row["execution_order"]) for row in raw if row["scenario"] == "smoke-spread"),
            [1, 2, 3, 4],
        )
        order = _blocked_model_order(
            ("snapshot", "log", "revon-m", "revon-h"),
            seed=123,
            phase="evaluation",
            scenario="smoke-spread",
            kind="measured",
            trial=1,
        )
        self.assertEqual(
            order,
            _blocked_model_order(
                ("snapshot", "log", "revon-m", "revon-h"),
                seed=123,
                phase="evaluation",
                scenario="smoke-spread",
                kind="measured",
                trial=1,
            ),
        )
        first_positions = [
            _blocked_model_order(
                ("snapshot", "log", "revon-m", "revon-h"),
                seed=123,
                phase="evaluation",
                scenario="smoke-spread",
                kind="measured",
                trial=trial,
            )[0]
            for trial in range(1, 8)
        ]
        self.assertEqual(set(first_positions), {"snapshot", "log", "revon-m", "revon-h"})


if __name__ == "__main__":
    unittest.main()
