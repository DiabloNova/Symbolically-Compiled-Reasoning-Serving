"""Regression tests for LegalBench runner metrics returned to the live pipeline."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.scrs_runtime.anchor_client import ProviderRequestError
from experiments.scrs_runtime.run_legalbench import metrics_for, run_live


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

    @patch("experiments.scrs_runtime.run_legalbench.build_full_messages")
    @patch("experiments.scrs_runtime.run_legalbench.build_task_record")
    @patch("experiments.scrs_runtime.run_legalbench.task_description")
    @patch("experiments.scrs_runtime.run_legalbench.OpenAICompatibleClient.from_env")
    def test_failed_case_persists_call_attempt_and_prompt_linkage(
        self, from_env, task_description, build_task_record, build_full_messages
    ):
        class FailingClient:
            model = "fixture-model"

            def chat(self, **kwargs):
                raise ProviderRequestError(
                    "fixture provider timeout",
                    attempts=[{
                        "duration_ms": 12.5,
                        "status": "timeout",
                        "provider_generation_evidence": "UNKNOWN",
                        "provider_generation_unknown_reason": "TIMEOUT_OUTCOME_UNKNOWN",
                    }],
                    events=[],
                )

        from_env.return_value = FailingClient()
        task_description.return_value = "fixture task"
        build_task_record.return_value = {
            "input_fields": {"text": "fixture input"},
            "source_input_sha256": "a" * 64,
            "task_contract_version": "fixture-contract",
        }
        build_full_messages.return_value = [{"role": "user", "content": "fixture prompt"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            with self.assertRaises(ProviderRequestError):
                run_live(
                    tasks={"fixture": [{"index": 4, "fields": {"text": "fixture input", "answer": "Yes"}}]},
                    sidecars={"fixture": {"upstream_revision": "fixture-revision"}},
                    task_manifest={"task_allowlist": {"fixture": {"labels": ["Yes", "No"]}}},
                    max_examples=1,
                    out_dir=out_dir,
                    run_id="fixture-run",
                )

            failure = json.loads((out_dir / "failure.json").read_text(encoding="utf-8"))
            failed_calls = failure["calls_by_condition"]["baseline"]
            self.assertEqual(failure["failed_request_id_hash"], failed_calls[0]["request_id_hash"])
            self.assertEqual(failed_calls[0]["status"], "FAILED_PROVIDER_REQUEST")
            self.assertEqual(failed_calls[0]["prompt_sha256"], __import__("hashlib").sha256(
                b'[{"content":"fixture prompt","role":"user"}]'
            ).hexdigest())
            self.assertEqual(failed_calls[0]["attempts"][0]["status"], "timeout")
            self.assertEqual(failed_calls[0]["attempts"][0]["provider_generation_evidence"], "UNKNOWN")
            self.assertNotIn("fixture prompt", json.dumps(failure))

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
