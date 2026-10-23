"""Network-free tests for strict LegalBench scoring."""
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "evaluation"))

from score_legalbench import ScoringError, score_rows, wilson_interval  # noqa: E402


def gold_row(index, answer):
    return {
        "index": index, "task": "sample", "split": "test",
        "fields": {"index": index, "answer": answer, "text": f"text-{index}"},
    }


class LegalBenchScoringTests(unittest.TestCase):
    def test_perfect_predictions_return_full_accuracy_and_macro_f1(self):
        gold = [gold_row(0, "generic"), gold_row(1, "descriptive"), gold_row(2, "generic")]
        predictions = [
            {"index": 0, "prediction": " GENERIC "},
            {"index": 1, "prediction": "descriptive"},
            {"index": 2, "prediction": "generic"},
        ]
        result = score_rows(gold, predictions)
        self.assertEqual(result["n"], 3)
        self.assertEqual(result["correct"], 3)
        self.assertEqual(result["accuracy"], 1.0)
        self.assertAlmostEqual(result["macro_f1"], 1.0)
        self.assertEqual(result["label_support"], {"descriptive": 1, "generic": 2})

    def test_mismatched_or_duplicate_indices_fail_closed(self):
        gold = [gold_row(0, "generic"), gold_row(1, "descriptive")]
        with self.assertRaises(ScoringError):
            score_rows(gold, [{"index": 0, "prediction": "generic"}])
        with self.assertRaises(ScoringError):
            score_rows(gold, [
                {"index": 0, "prediction": "generic"},
                {"index": 0, "prediction": "generic"},
            ])

    def test_unknown_prediction_label_is_rejected(self):
        with self.assertRaises(ScoringError):
            score_rows([gold_row(0, "generic")], [{"index": 0, "prediction": "maybe-ish"}])

    def test_gold_duplicate_index_or_invalid_label_is_rejected(self):
        with self.assertRaises(ScoringError):
            score_rows(
                [gold_row(0, "generic"), gold_row(0, "generic")],
                [{"index": 0, "prediction": "generic"}],
            )
        with self.assertRaises(ScoringError):
            score_rows([gold_row(0, "")], [{"index": 0, "prediction": "generic"}])

    def test_wilson_interval_contains_observed_proportion(self):
        ci = wilson_interval(7, 10)
        self.assertIsNotNone(ci)
        assert ci is not None
        self.assertLessEqual(ci[0], 0.7)
        self.assertGreaterEqual(ci[1], 0.7)
        self.assertIsNone(wilson_interval(0, 0))

    def test_wrong_index_type_is_rejected(self):
        with self.assertRaises(ScoringError):
            score_rows([gold_row(0, "generic")], [{"index": "0", "prediction": "generic"}])


if __name__ == "__main__":
    unittest.main()
