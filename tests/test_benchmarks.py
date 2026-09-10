import unittest

from benchmarks import build_workload, run_scenario


class BenchmarkTests(unittest.TestCase):
    def test_workload_records_correct_old_values(self) -> None:
        initial, batches = build_workload(100, versions=4, changes_per_commit=3)
        state = dict(initial)
        for batch in batches:
            for operation in batch:
                self.assertEqual(state[operation.key], operation.old_value)
                state[operation.key] = operation.new_value

    def test_all_models_produce_comparable_results(self) -> None:
        results = run_scenario(
            rows=100, versions=3, changes_per_commit=2, diff_repeats=1
        )

        self.assertEqual(len(results), 3)
        self.assertEqual({result.changed_keys for result in results}, {4})
        for result in results:
            self.assertGreaterEqual(result.commit_ms, 0)
            self.assertGreaterEqual(result.diff_ms, 0)
            self.assertGreater(result.storage_bytes, 0)
            self.assertGreater(result.diff_work, 0)


if __name__ == "__main__":
    unittest.main()
