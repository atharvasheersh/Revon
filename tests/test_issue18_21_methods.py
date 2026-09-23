from __future__ import annotations

import unittest

from experiments.paired_uncertainty import (
    classify,
    paired_median_ratio_interval,
)
from experiments.robustness_study import specs
from experiments.robustness_summary import cluster_bootstrap_interval


class ReviewIssueMethodTests(unittest.TestCase):
    def test_robustness_matrix_covers_seed_payload_history_and_locality(self) -> None:
        workloads = specs()
        self.assertEqual(len(workloads), 15)
        self.assertEqual(len({workload.seed for workload in workloads}), 3)
        self.assertEqual({workload.payload_bytes for workload in workloads}, {32, 128})
        self.assertEqual({workload.commits for workload in workloads}, {10, 50})
        self.assertEqual(
            {workload.locality for workload in workloads},
            {"spread", "range-local", "repeated-key"},
        )

    def test_paired_bootstrap_is_deterministic_and_reports_parity(self) -> None:
        first = paired_median_ratio_interval([0.9, 1.0, 1.1], seed=4, draws=500)
        second = paired_median_ratio_interval([0.9, 1.0, 1.1], seed=4, draws=500)
        self.assertEqual(first, second)
        self.assertEqual(first[0], 1.0)
        self.assertEqual(classify(*first), "inconclusive: interval includes parity")

    def test_practical_margin_avoids_calling_tiny_ratio_a_win(self) -> None:
        self.assertEqual(
            classify(1.02, 1.01, 1.03),
            "statistically separated but below the 5% practical margin",
        )
        self.assertEqual(
            classify(1.20, 1.10, 1.30),
            "denominator faster by a practically relevant margin",
        )
        self.assertEqual(
            classify(0.80, 0.70, 0.90),
            "numerator faster by a practically relevant margin",
        )

    def test_clustered_bootstrap_resamples_seeds_and_trial_pairs(self) -> None:
        first = cluster_bootstrap_interval(
            {11: [2.0, 2.1, 2.2], 22: [1.8, 1.9, 2.0], 33: [2.1, 2.2, 2.3]},
            seed=17,
            draws=500,
        )
        second = cluster_bootstrap_interval(
            {11: [2.0, 2.1, 2.2], 22: [1.8, 1.9, 2.0], 33: [2.1, 2.2, 2.3]},
            seed=17,
            draws=500,
        )
        self.assertEqual(first, second)
        self.assertGreater(first[1], 1.0)


if __name__ == "__main__":
    unittest.main()
