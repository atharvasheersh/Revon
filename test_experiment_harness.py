from __future__ import annotations

import csv
import json
import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from experiments.final_benchmark import execute, run_trial
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


class HarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("tmp") / f"experiment-test-{uuid.uuid4().hex}"
        self.root.mkdir(parents=True)
        self.workload = build_workload(WorkloadSpec("unit", 100, 2, 10, 7))

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def test_all_python_adapters_match_same_oracle(self) -> None:
        for model in ("snapshot", "log", "chronos-m", "chronos-h"):
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
                self.assertGreater(record.peak_memory_bytes or 0, 0)

    def test_missing_dolt_is_recorded_not_fabricated(self) -> None:
        with patch("experiments.adapters.shutil.which", return_value=None):
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

        self.assertEqual(record.status, "unavailable")
        self.assertIsNone(record.diff_ms)
        self.assertIsNone(record.correctness)

    def test_smoke_execution_writes_raw_summary_and_manifest(self) -> None:
        output = self.root / "results"

        records, threshold = execute(
            profile="smoke",
            output_dir=output,
            warmups=0,
            trials=1,
            seed=123,
            models=("snapshot", "log", "chronos-m", "chronos-h"),
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


if __name__ == "__main__":
    unittest.main()
