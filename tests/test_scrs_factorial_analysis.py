from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.scrs_runtime.analyze_factorial import (
    AnalysisError,
    analyze,
    exact_mcnemar_two_sided,
    read_cases,
)


def make_case(task: str, index: int, gold: str, labels: dict[str, str]) -> dict:
    predictions = {
        "baseline": {"label": labels["baseline"], "valid": True},
        "capsule_only": {"label": labels["capsule_only"], "valid": labels["capsule_only"] != "__INVALID__"},
        "capsule_graph_no_anchor": {"label": labels["capsule_graph_no_anchor"], "valid": labels["capsule_graph_no_anchor"] != "__INVALID__"},
        "capsule_anchor_no_graph": {"label": labels["capsule_anchor_no_graph"], "valid": labels["capsule_anchor_no_graph"] != "__INVALID__"},
        "compiled_graph_gates": {"label": labels["compiled_graph_gates"], "valid": labels["compiled_graph_gates"] != "__INVALID__"},
    }
    return {"task_id": task, "index": index, "gold_label": gold, "capsule_status": "VALID", "predictions": predictions}


class FactorialAnalysisTests(unittest.TestCase):
    def test_zero_interaction_for_equal_arms_and_task_separation(self):
        cases = [
            make_case("alpha", 0, "Yes", {
                "baseline": "Yes", "capsule_only": "Yes", "capsule_graph_no_anchor": "Yes",
                "capsule_anchor_no_graph": "Yes", "compiled_graph_gates": "Yes",
            }),
            make_case("alpha", 1, "No", {
                "baseline": "Yes", "capsule_only": "No", "capsule_graph_no_anchor": "No",
                "capsule_anchor_no_graph": "No", "compiled_graph_gates": "No",
            }),
            make_case("beta", 0, "UCC", {
                "baseline": "UCC", "capsule_only": "UCC", "capsule_graph_no_anchor": "UCC",
                "capsule_anchor_no_graph": "Common Law", "compiled_graph_gates": "UCC",
            }),
        ]
        result = analyze(cases, bootstrap_replicates=200, seed=17)
        alpha = result["tasks"]["alpha"]
        self.assertEqual(result["task_count"], 2)
        self.assertEqual(alpha["n_paired_rows"], 2)
        self.assertEqual(alpha["conditional_graph_anchor_interaction"]["all_attempted_rows"]["estimate"], 0.0)
        self.assertEqual(alpha["arms"]["compiled_graph_gates"]["accuracy"], 1.0)

    def test_positive_interaction_is_detected(self):
        cases = [
            make_case("task", i, "A", {
                "baseline": "B",
                "capsule_only": "B",
                "capsule_graph_no_anchor": "B",
                "capsule_anchor_no_graph": "B",
                "compiled_graph_gates": "A",
            })
            for i in range(20)
        ]
        report = analyze(cases, bootstrap_replicates=500, seed=1)["tasks"]["task"]
        self.assertEqual(report["conditional_graph_anchor_interaction"]["all_attempted_rows"]["estimate"], 1.0)
        self.assertEqual(report["conditional_graph_anchor_interaction"]["all_attempted_rows"]["bootstrap_percentile_95_ci"], [1.0, 1.0])

    def test_invalid_output_counts_wrong_and_invalid(self):
        cases = [make_case("task", 0, "A", {
            "baseline": "A", "capsule_only": "__INVALID__", "capsule_graph_no_anchor": "A",
            "capsule_anchor_no_graph": "A", "compiled_graph_gates": "A",
        })]
        report = analyze(cases, bootstrap_replicates=100, seed=1)["tasks"]["task"]
        self.assertEqual(report["arms"]["capsule_only"]["accuracy"], 0.0)
        self.assertEqual(report["arms"]["capsule_only"]["invalid_outputs"], 1)

    def test_missing_arm_fails_closed(self):
        case = make_case("task", 0, "A", {
            "baseline": "A", "capsule_only": "A", "capsule_graph_no_anchor": "A",
            "capsule_anchor_no_graph": "A", "compiled_graph_gates": "A",
        })
        del case["predictions"]["capsule_anchor_no_graph"]
        with self.assertRaises(AnalysisError):
            analyze([case], bootstrap_replicates=100, seed=1)

    def test_duplicate_rows_fail_closed(self):
        case = make_case("task", 0, "A", {
            "baseline": "A", "capsule_only": "A", "capsule_graph_no_anchor": "A",
            "capsule_anchor_no_graph": "A", "compiled_graph_gates": "A",
        })
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "cases.jsonl"
            p.write_text(json.dumps(case) + "\n" + json.dumps(case) + "\n", encoding="utf-8")
            with self.assertRaises(AnalysisError):
                read_cases(p)

    def test_exact_mcnemar_symmetric_and_no_discordance(self):
        self.assertEqual(exact_mcnemar_two_sided(5, 5), 1.0)
        self.assertEqual(exact_mcnemar_two_sided(0, 0), None)
        self.assertLess(exact_mcnemar_two_sided(10, 0), 0.01)


if __name__ == "__main__":
    unittest.main()
