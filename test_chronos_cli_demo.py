import unittest

from chronos_cli_demo import run_demo


class ChronosCLIDemoTests(unittest.TestCase):
    def test_demo_self_checks_incremental_model(self) -> None:
        result = run_demo(rows=200, updates=3, hybrid_threshold=128)

        self.assertEqual(result.changed_keys, 5)
        self.assertLessEqual(result.new_nodes, result.maximum_path_nodes)
        self.assertGreater(result.shared_percent, 90.0)
        self.assertEqual(result.hybrid_strategy, "log")
        self.assertEqual(len(result.changes), 5)


if __name__ == "__main__":
    unittest.main()
