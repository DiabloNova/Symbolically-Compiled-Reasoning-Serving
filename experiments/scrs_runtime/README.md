"""Offline conformance tests for SCRS runtime and Anchor client."""
import json
import os
import socket
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from experiments.scrs_runtime.anchor_client import (
    AnchorClient,
    OpenAICompatibleClient,
    ProviderConfigurationError,
    ProviderRequestError,
)
from experiments.scrs_runtime.scrs_runtime import (
    CapsuleValidationError,
    build_capsule_messages,
    build_capsule_only_messages,
    build_compiled_render_messages,
    build_full_messages,
    compile_decision_graph,
    create_capsule,
    parse_capsule_payload,
    parse_label,
    source_input_fields,
    source_input_hash,
    task_contract_version,
    validate_capsule,
)


TASK = "abercrombie"
INFO = {
    "task_kind": "five-way trademark classification",
    "task_page": "https://example.org/task",
    "labels": ["generic", "descriptive", "suggestive", "arbitrary", "fanciful"],
}
REV = "a" * 40
FIELDS_WITH_GOLD = {"index": 7, "text": "The mark 'Salt' for packages of sodium chloride.", "answer": "generic"}
FIELDS = source_input_fields({"fields": FIELDS_WITH_GOLD})
LABELS = INFO["labels"]
CONTRACT = task_contract_version(TASK, INFO, REV)
PAYLOAD = {
    "decision_relevant_facts": ["The mark Salt is used for packages of sodium chloride."],
    "conditions_or_qualifiers": [],
    "exceptions_or_contraindications": [],
    "ambiguities_or_unknowns": [],
}
CAPSULE = create_capsule(TASK, CONTRACT, REV, FIELDS, LABELS, PAYLOAD)
GRAPH = compile_decision_graph(TASK, CONTRACT, REV, source_input_hash(FIELDS), LABELS)


class FakeResponse:
    def __init__(self, payload, headers=None, status=200):
        self.payload = json.dumps(payload).encode("utf-8")
        self.headers = headers or {"x-request-id": "provider-test-id"}
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def provider_payload(content="generic"):
    return {
        "id": "completion-test",
        "choices": [{"message": {"role": "assistant", "content": content}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 1},
    }


class RuntimeContractTests(unittest.TestCase):
    def test_gold_answer_is_removed_from_all_model_inputs(self):
        fields = source_input_fields({"fields": FIELDS_WITH_GOLD})
        self.assertNotIn("answer", fields)
        full = json.dumps(build_full_messages(TASK, "task description", LABELS, fields))
        extract = json.dumps(build_capsule_messages(TASK, "task description", LABELS, fields))
        self.assertNotIn('"answer": "generic"', full)
        self.assertNotIn('"answer": "generic"', extract)

    def test_capsule_parser_accepts_declared_schema(self):
        parsed = parse_capsule_payload(json.dumps(PAYLOAD))
        self.assertEqual(parsed, PAYLOAD)

    def test_capsule_parser_rejects_predicted_label_extra_field(self):
        raw = dict(PAYLOAD, predicted_label="generic")
        with self.assertRaises(CapsuleValidationError):
            parse_capsule_payload(json.dumps(raw))

    def test_capsule_parser_fails_closed_when_decisive_facts_missing(self):
        raw = dict(PAYLOAD, decision_relevant_facts=[])
        with self.assertRaises(CapsuleValidationError):
            parse_capsule_payload(json.dumps(raw))

    def test_compatible_capsule_and_graph_pass_all_gates(self):
        accepted, trace = validate_capsule(CAPSULE, GRAPH, TASK, CONTRACT, REV, FIELDS, LABELS)
        self.assertTrue(accepted)
        self.assertEqual(trace[-1]["decision"], "FAST_PATH")
        self.assertEqual(sum(1 for x in trace if x["decision"] == "ACCEPT"), 7)

    def test_wrong_source_provenance_fails_closed(self):
        accepted, trace = validate_capsule(CAPSULE, GRAPH, TASK, CONTRACT, REV,
                                           dict(FIELDS, text="changed source"), LABELS)
        self.assertFalse(accepted)
        self.assertEqual(trace[-1]["decision"], "FALLBACK")
        self.assertEqual(trace[-2]["reason_code"], "CHECK_SOURCE_PROVENANCE_FAILED")

    def test_stale_contract_version_fails_closed(self):
        accepted, trace = validate_capsule(CAPSULE, GRAPH, TASK, "old-contract", REV, FIELDS, LABELS)
        self.assertFalse(accepted)
        self.assertEqual(trace[-1]["decision"], "FALLBACK")

    def test_graph_node_reordering_fails_closed(self):
        bad_graph = dict(GRAPH)
        bad_graph["nodes"] = list(reversed(GRAPH["nodes"]))
        accepted, trace = validate_capsule(CAPSULE, bad_graph, TASK, CONTRACT, REV, FIELDS, LABELS)
        self.assertFalse(accepted)
        self.assertEqual(trace[-2]["reason_code"], "CHECK_GRAPH_ORDER_FAILED")

    def test_capsule_with_unapproved_payload_field_fails_closed_at_gate(self):
        bad_capsule = dict(CAPSULE)
        bad_capsule["payload"] = dict(PAYLOAD, raw_source_text="not permitted")
        accepted, trace = validate_capsule(bad_capsule, GRAPH, TASK, CONTRACT, REV, FIELDS, LABELS)
        self.assertFalse(accepted)
        self.assertEqual(trace[-2]["reason_code"], "CHECK_CAPSULE_SCHEMA_FAILED")

    def test_capsule_only_prompt_excludes_source_fields(self):
        prompt = json.dumps(build_capsule_only_messages(TASK, "definition", LABELS, CAPSULE))
        self.assertIn("decision_relevant_facts", prompt)
        self.assertNotIn("The mark 'Salt' for packages of sodium chloride.", prompt)
        self.assertNotIn("source_input_sha256", prompt)

    def test_compiled_prompt_contains_graph_and_gate_trace(self):
        accepted, trace = validate_capsule(CAPSULE, GRAPH, TASK, CONTRACT, REV, FIELDS, LABELS)
        self.assertTrue(accepted)
        prompt = json.dumps(build_compiled_render_messages(TASK, "definition", LABELS, CAPSULE,
                                                          GRAPH, trace, "generic"))
        self.assertIn("CHECK_SOURCE_PROVENANCE", prompt)
        self.assertIn("anchor_hint", prompt)

    def test_label_parser_requires_one_exact_label(self):
        self.assertEqual(parse_label("generic", LABELS), "generic")
        self.assertEqual(parse_label('{"prediction": "Common Law"}', ["UCC", "Common Law"]), "Common Law")
        self.assertIsNone(parse_label("The answer is generic because ...", LABELS))

    def test_experiment_event_schema_is_valid_json_and_separates_event_kinds(self):
        schema_path = Path(__file__).resolve().parents[1] / "experiments" / "scrs_runtime" / "event-schema.v1.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertIn("anchor_transport_attempt", schema["properties"]["event_type"]["enum"])
        self.assertIn("model_transport_attempt", schema["properties"]["event_type"]["enum"])
        self.assertIn("provider_generation_evidence", schema["required"])


class AnchorClientTests(unittest.TestCase):
    def make_client(self, role="anchor", retries=1):
        return OpenAICompatibleClient(
            base_url="http://localhost:8000/v1",
            model="test-model",
            api_key=None,
            role=role,
            timeout_seconds=1,
            max_retries=retries,
        )

    @patch("experiments.scrs_runtime.anchor_client.urlopen")
    def test_anchor_client_sends_request_and_records_provider_usage(self, urlopen_mock):
        urlopen_mock.return_value = FakeResponse(provider_payload("generic"))
        client = self.make_client()
        result = client.chat(
            messages=[{"role": "user", "content": "test"}],
            request_id_hash="a" * 32,
            causal_interrupt_seq=4,
            max_tokens=5,
        )
        self.assertEqual(result.content, "generic")
        self.assertEqual(result.usage, {"input_tokens": 20, "output_tokens": 1})
        self.assertEqual(result.events[0]["event_type"], "anchor_transport_attempt")
        self.assertEqual(result.events[-1]["event_type"], "anchor_provider_response")
        self.assertEqual(result.events[-1]["provider_generation_evidence"], "CONFIRMED")
        sent_request = urlopen_mock.call_args.args[0]
        self.assertEqual(sent_request.full_url, "http://localhost:8000/v1/chat/completions")

    @patch("experiments.scrs_runtime.anchor_client.time.sleep")
    @patch("experiments.scrs_runtime.anchor_client.urlopen")
    def test_timeout_is_unknown_then_retry_success_is_confirmed(self, urlopen_mock, sleep_mock):
        urlopen_mock.side_effect = [socket.timeout(), FakeResponse(provider_payload())]
        result = self.make_client(retries=1).chat(
            messages=[{"role": "user", "content": "test"}],
            request_id_hash="b" * 32,
            causal_interrupt_seq=1,
            max_tokens=5,
        )
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.attempts[0]["provider_generation_evidence"], "UNKNOWN")
        self.assertEqual(result.attempts[0]["provider_generation_unknown_reason"], "TIMEOUT_OUTCOME_UNKNOWN")
        self.assertEqual(result.attempts[1]["provider_generation_evidence"], "CONFIRMED")
        sleep_mock.assert_called_once()


    @patch("experiments.scrs_runtime.anchor_client.time.sleep")
    @patch("experiments.scrs_runtime.anchor_client.urlopen")
    def test_final_timeout_raises_with_attempt_and_event_evidence(self, urlopen_mock, sleep_mock):
        urlopen_mock.side_effect = socket.timeout()
        client = self.make_client(retries=0)
        with self.assertRaises(ProviderRequestError) as raised:
            client.chat(
                messages=[{"role": "user", "content": "test"}],
                request_id_hash="c" * 32,
                causal_interrupt_seq=5,
                max_tokens=5,
            )
        error = raised.exception
        self.assertEqual(len(error.attempts), 1)
        self.assertEqual(error.attempts[0]["status"], "timeout")
        self.assertEqual(error.attempts[0]["provider_generation_unknown_reason"], "TIMEOUT_OUTCOME_UNKNOWN")
        self.assertEqual(len(error.events), 1)
        self.assertEqual(error.events[0]["event_type"], "anchor_transport_attempt")
        sleep_mock.assert_not_called()

    @patch("experiments.scrs_runtime.anchor_client.time.sleep")
    @patch("experiments.scrs_runtime.anchor_client.urlopen")
    def test_timeout_wrapped_by_urlerror_stays_timeout_unknown(self, urlopen_mock, sleep_mock):
        urlopen_mock.side_effect = URLError(socket.timeout("socket timed out"))
        with self.assertRaises(ProviderRequestError) as raised:
            self.make_client(retries=0).chat(
                messages=[{"role": "user", "content": "test"}],
                request_id_hash="d" * 32,
                causal_interrupt_seq=6,
                max_tokens=5,
            )
        self.assertEqual(raised.exception.attempts[0]["provider_generation_unknown_reason"],
                         "TIMEOUT_OUTCOME_UNKNOWN")
        self.assertEqual(raised.exception.events[0]["status"], "timeout")
        sleep_mock.assert_not_called()

    def test_anchor_is_hard_capped_at_five_tokens(self):
        client = self.make_client()
        self.assertEqual(AnchorClient(client, max_tokens=5).max_tokens, 5)
        with self.assertRaises(ValueError):
            AnchorClient(client, max_tokens=6)

    @patch.dict(os.environ, {"SCRS_BASE_URL": "https://api.openai.com/v1", "SCRS_MODEL": "model"}, clear=True)
    def test_live_provider_requires_credentials(self):
        with self.assertRaises(ProviderConfigurationError):
            OpenAICompatibleClient.from_env("render")


if __name__ == "__main__":
    unittest.main(verbosity=2)
