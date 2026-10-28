"""Reproducibility tests for seeded LegalBench sampling and provider request options."""
from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.scrs_runtime.anchor_client import (
    OpenAICompatibleClient,
    ProviderConfigurationError,
)
from experiments.scrs_runtime.run_legalbench import (
    apply_seeded_sample,
    exclude_test_rows,
    load_exclusion_indices,
    selected_test_row_indices,
)


class FakeResponse:
    status = 200
    headers = {"x-request-id": "repro-test-id"}

    def __init__(self):
        self.payload = json.dumps({
            "id": "fake-completion",
            "model": "resolved-provider-model",
            "choices": [{"message": {"role": "assistant", "content": "UCC"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 1},
        }).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class SeededSamplingTests(unittest.TestCase):
    def fixture_tasks(self):
        return {
            task: [{"index": i, "fields": {"text": f"{task}-{i}", "answer": "x"}}
                   for i in range(40)]
            for task in ("alpha", "beta")
        }

    def test_seeded_sample_is_repeatable_and_keeps_full_pool(self):
        first = self.fixture_tasks()
        second = self.fixture_tasks()
        apply_seeded_sample(first, 8, 20261027)
        apply_seeded_sample(second, 8, 20261027)
        selected_first = selected_test_row_indices(first, 8)
        selected_second = selected_test_row_indices(second, 8)
        self.assertEqual(selected_first, selected_second)
        for task, rows in first.items():
            self.assertEqual(len(rows), 40)
            self.assertEqual(len(selected_first[task]), 8)
            self.assertEqual(len(set(selected_first[task])), 8)
            self.assertEqual(set(row["index"] for row in rows), set(range(40)))
            self.assertEqual(
                selected_first[task],
                [row["index"] for row in rows[:8]],
            )

    def test_different_seeds_change_sample_and_none_preserves_first_n(self):
        one = self.fixture_tasks()
        two = self.fixture_tasks()
        apply_seeded_sample(one, 8, 11)
        apply_seeded_sample(two, 8, 12)
        self.assertNotEqual(
            selected_test_row_indices(one, 8)["alpha"],
            selected_test_row_indices(two, 8)["alpha"],
        )
        original = self.fixture_tasks()
        apply_seeded_sample(original, 8, None)
        self.assertEqual(selected_test_row_indices(original, 8)["alpha"], list(range(8)))

    def test_full_run_does_not_drop_or_reorder_rows(self):
        tasks = self.fixture_tasks()
        original = copy.deepcopy(tasks)
        apply_seeded_sample(tasks, 0, 20261027)
        self.assertEqual(tasks, original)

    def test_explicit_exclusions_remove_only_named_rows_and_are_manifestable(self):
        tasks = self.fixture_tasks()
        applied = exclude_test_rows(tasks, {"alpha": [3, 12], "beta": [7]})
        self.assertEqual(applied, {"alpha": [3, 12], "beta": [7]})
        self.assertEqual(len(tasks["alpha"]), 38)
        self.assertEqual(len(tasks["beta"]), 39)
        self.assertNotIn(3, [row["index"] for row in tasks["alpha"]])
        self.assertNotIn(12, [row["index"] for row in tasks["alpha"]])
        self.assertNotIn(7, [row["index"] for row in tasks["beta"]])
        self.assertEqual(set(row["index"] for row in tasks["alpha"]), set(range(40)) - {3, 12})

    def test_missing_requested_exclusion_fails_closed(self):
        tasks = self.fixture_tasks()
        with self.assertRaises(ValueError):
            exclude_test_rows(tasks, {"alpha": [999]})

    def test_exclusion_map_loader_rejects_boolean_and_duplicate_indices(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "exclusions.json"
            p.write_text(json.dumps({"alpha": [True]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_exclusion_indices(p)
            p.write_text(json.dumps({"alpha": [1, 1]}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_exclusion_indices(p)
            p.write_text(json.dumps({"alpha": [1, 2]}), encoding="utf-8")
            self.assertEqual(load_exclusion_indices(p), {"alpha": [1, 2]})


class ProviderExtraBodyTests(unittest.TestCase):
    @patch("experiments.scrs_runtime.anchor_client.urlopen")
    def test_explicit_json_provider_options_reach_wire_request(self, urlopen_mock):
        urlopen_mock.return_value = FakeResponse()
        env = {
            "SCRS_BASE_URL": "http://localhost:8000/v1",
            "SCRS_MODEL": "test-model",
            "SCRS_PROVIDER_EXTRA_BODY_JSON": '{"reasoning":{"effort":"none"}}',
            "SCRS_PROVIDER_MAX_RETRIES": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            client = OpenAICompatibleClient.from_env("render")
            result = client.chat(
                messages=[{"role": "user", "content": "classify"}],
                request_id_hash="a" * 32,
                causal_interrupt_seq=1,
                max_tokens=8,
            )
        sent = json.loads(urlopen_mock.call_args.args[0].data.decode("utf-8"))
        self.assertEqual(sent["reasoning"], {"effort": "none"})
        self.assertEqual(result.content, "UCC")
        self.assertEqual(result.model, "resolved-provider-model")
        self.assertEqual(result.events[-1]["model"], "resolved-provider-model")

    def test_provider_options_cannot_override_core_request_fields(self):
        with self.assertRaises(ProviderConfigurationError):
            OpenAICompatibleClient(
                base_url="http://localhost:8000/v1",
                model="test-model",
                api_key=None,
                role="render",
                extra_body={"model": "different-model"},
            )

    def test_provider_options_must_be_valid_json_object(self):
        env = {
            "SCRS_BASE_URL": "http://localhost:8000/v1",
            "SCRS_MODEL": "test-model",
            "SCRS_PROVIDER_EXTRA_BODY_JSON": '["not", "an", "object"]',
        }
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ProviderConfigurationError):
                OpenAICompatibleClient.from_env("render")


if __name__ == "__main__":
    unittest.main()
