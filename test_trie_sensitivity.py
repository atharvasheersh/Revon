import shutil
import unittest
from pathlib import Path

from experiments.trie_sensitivity import TrieConfig, execute_sensitivity
from experiments.workloads import WorkloadSpec


class TrieSensitivityTests(unittest.TestCase):
    def test_configuration_geometry(self) -> None:
        self.assertEqual(TrieConfig(4, 6).leaf_buckets, 4096)
        self.assertEqual(TrieConfig(8, 4).leaf_buckets, 4096)
        self.assertEqual(TrieConfig(16, 3).leaf_buckets, 4096)
        self.assertEqual(TrieConfig(8, 4).routing_bits, 12)

    def test_small_run_is_correct_and_writes_evidence(self) -> None:
        output = Path("tmp") / "test-trie-sensitivity"
        shutil.rmtree(output, ignore_errors=True)
        try:
            records = execute_sensitivity(
                output_dir=output,
                spec=WorkloadSpec(
                    "test-sensitivity",
                    rows=100,
                    commits=2,
                    changes_per_commit=10,
                    seed=1234,
                ),
                configs=(TrieConfig(4, 3), TrieConfig(8, 2)),
                warmups=0,
                trials=1,
            )
            self.assertEqual(len(records), 2)
            self.assertTrue(all(record.status == "ok" for record in records))
            self.assertTrue(all(record.correctness for record in records))
            self.assertEqual(len({record.workload_sha256 for record in records}), 1)
            self.assertTrue((output / "raw_results.csv").is_file())
            self.assertTrue((output / "summary.csv").is_file())
            self.assertTrue((output / "manifest.json").is_file())
        finally:
            shutil.rmtree(output, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
