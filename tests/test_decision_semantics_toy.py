"""Exact toy checks for the conditional decision-information theorem."""
import math
import unittest

from experiments.decision_semantics.toy_exact_checks import (
    bayes_zero_one_risk,
    conditional_information_loss,
    example_discarding_decisive_fact,
    example_discarding_irrelevant_nuisance,
    exact_example_report,
)


class DecisionSemanticsToyTests(unittest.TestCase):
    def test_discarding_irrelevant_nuisance_preserves_target(self):
        rows = example_discarding_irrelevant_nuisance()
        self.assertAlmostEqual(conditional_information_loss(rows), 0.0, places=12)
        self.assertAlmostEqual(bayes_zero_one_risk(rows, "full_context"), 0.0, places=12)
        self.assertAlmostEqual(bayes_zero_one_risk(rows, "capsule"), 0.0, places=12)

    def test_discarding_decisive_fact_produces_ln2_information_loss(self):
        rows = example_discarding_decisive_fact()
        self.assertAlmostEqual(conditional_information_loss(rows), math.log(2.0), places=12)

    def test_decisive_fact_example_risk_gap_satisfies_pinsker_bound(self):
        rows = example_discarding_decisive_fact()
        full_risk = bayes_zero_one_risk(rows, "full_context")
        capsule_risk = bayes_zero_one_risk(rows, "capsule")
        self.assertAlmostEqual(full_risk, 0.0, places=12)
        self.assertAlmostEqual(capsule_risk, 0.5, places=12)
        self.assertLessEqual(capsule_risk - full_risk,
                             math.sqrt(conditional_information_loss(rows) / 2.0) + 1e-12)

    def test_example_report_passes_and_marks_evidence_boundary(self):
        report = exact_example_report()
        self.assertEqual(report["status"], "PASS", report)
        self.assertIn("not SCRS empirical evidence", report["evidence_status"])

    def test_invalid_probability_mass_is_rejected(self):
        rows = [(0.8, "q", (0, 0), 0, 0), (0.1, "q", (1, 0), 1, 0)]
        with self.assertRaises(ValueError):
            conditional_information_loss(rows)


if __name__ == "__main__":
    unittest.main(verbosity=2)
