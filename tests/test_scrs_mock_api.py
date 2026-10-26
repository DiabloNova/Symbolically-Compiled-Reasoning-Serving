"""Contract tests for the zero-cost local mock API."""
from __future__ import annotations

import json
import unittest

from experiments.scrs_runtime.mock_api import synthetic_response


class MockApiTests(unittest.TestCase):
    def test_capsule_fixture_obeys_schema_and_marks_itself_non_semantic(self):
        result = json.loads(synthetic_response({
            "model": "scrs-mock-oracle",
            "messages": [{
                "role": "user",
                "content": json.dumps({
                    "task_id": "fixture-task",
                    "source_input_fields": {"text": "mock source"},
                    "required_json_schema": {
                        "decision_relevant_facts": "array",
                        "conditions_or_qualifiers": "array",
                        "exceptions_or_contraindications": "array",
                        "ambiguities_or_unknowns": "array",
                    },
                }),
            }],
        }))
        self.assertEqual(set(result), {
            "decision_relevant_facts", "conditions_or_qualifiers",
            "exceptions_or_contraindications", "ambiguities_or_unknowns",
        })
        self.assertTrue(result["decision_relevant_facts"])
        self.assertIn("MOCK ONLY", result["ambiguities_or_unknowns"][0])
        self.assertNotIn("answer", result)

    def test_classifier_returns_only_an_allowlisted_fixture_label(self):
        labels = ["yes", "no"]
        result = synthetic_response({
            "model": "scrs-mock-render",
            "messages": [{
                "role": "user",
                "content": json.dumps({"task_id": "fixture-task", "allowed_labels": labels, "text": "fixture"}),
            }],
        })
        self.assertIn(result, labels)

    def test_anchor_fixture_is_neutral_and_bounded(self):
        result = synthetic_response({
            "model": "scrs-mock-anchor",
            "messages": [{"role": "user", "content": "mock anchor input"}],
        })
        self.assertEqual(result, "UNKNOWN")
        self.assertLessEqual(len(result.split()), 5)

    def test_mock_api_never_uses_gold_label_as_a_prediction_source(self):
        payload = {
            "model": "scrs-mock-render",
            "messages": [{
                "role": "user",
                "content": json.dumps({
                    "task_id": "fixture-task",
                    "allowed_labels": ["yes", "no"],
                    "source_input_fields": {"text": "source data"},
                }),
            }],
        }
        first = synthetic_response(payload)
        second = synthetic_response(payload)
        self.assertEqual(first, second)
        self.assertIn(first, ["yes", "no"])


if __name__ == "__main__":
    unittest.main()
