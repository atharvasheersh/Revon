import unittest

from experiments.evidence_audit import (
    _manifest_specs,
    expected_hybrid_strategy,
    tukey_outliers,
)


class EvidenceAuditTests(unittest.TestCase):
    def test_schema_three_keeps_the_recorded_large_hot_name(self) -> None:
        manifest = {"profile": "paper", "schema_version": 3}
        specs = _manifest_specs(manifest, 20270822, phase="evaluation")
        self.assertIn("large-hot", {spec.name for spec in specs})
        self.assertNotIn("large-application-key-local", {spec.name for spec in specs})

    def test_hybrid_threshold_is_inclusive(self) -> None:
        self.assertEqual(expected_hybrid_strategy(4096, 4096), "log")
        self.assertEqual(expected_hybrid_strategy(4097, 4096), "merkle")

    def test_tukey_candidates_are_reported_without_removal(self) -> None:
        values = [10.0, 10.1, 10.2, 10.3, 10.4, 10.5, 50.0]
        lower, upper, indices = tukey_outliers(values)
        self.assertLess(lower, 10.0)
        self.assertLess(upper, 50.0)
        self.assertEqual(indices, [6])


if __name__ == "__main__":
    unittest.main()
