"""Regression tests for LegalBench runner metrics returned to the live pipeline."""
from __future__ import annotations

import unittest

from experiments.scrs_runtime.run_legalbench import metrics_for


class RunnerMetricsTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {"index": 0, "fields": {"answer": "Yes"}},
            {"index": 1, "fields": {"answer": "No"}},
        ]
        self.labels = ["Yes", "No"]

    def test_metrics_for_returns_scored_metrics_mapping(self):
        result = metrics_for(
            "fixture",
            self.rows,
            [
                {"index": 0, "prediction": "Yes"},
                {"index": 1, "prediction": "Yes"},
            ],
            self.labels,
        )
        self.assertIsInstance(result, dict)
        self.assertEqual(result["n"], 2)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["accuracy"], 0.5)
        self.assertAlmostEqual(result["macro_f1"], 1 / 3)

    def test_invalid_prediction_is_counted_wrong_not_dropped(self):
        result = metrics_for(
            "fixture",
            self.rows,
            [
                {"index": 0, "prediction": "__INVALID__"},
                {"index": 1, "prediction": "No"},
            ],
            self.labels,
        )
        self.assertEqual(result["invalid_outputs"], 1)
        self.assertEqual(result["correct"], 1)
        self.assertEqual(result["accuracy"], 0.5)
        self.assertEqual(result["valid_prediction_rate"], 0.5)

    def test_duplicate_or_missing_prediction_coverage_is_rejected(self):
        with self.assertRaises(ValueError):
            metrics_for(
                "fixture",
                self.rows,
                [{"index": 0, "prediction": "Yes"}, {"index": 0, "prediction": "No"}],
                self.labels,
            )


if __name__ == "__main__":
    unittest.main()
