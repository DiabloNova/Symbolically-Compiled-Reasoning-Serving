from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.scrs_runtime.anchor_client import ProviderResult
from experiments.scrs_runtime import run_legalbench as runner


VALID_CAPSULE = {
    "decision_relevant_facts": ["The source states the decisive fact."],
    "conditions_or_qualifiers": [],
    "exceptions_or_contraindications": [],
    "ambiguities_or_unknowns": [],
}


class FakeClient:
    def __init__(self, role: str):
        self.role = role
        self.model = f"test-{role}-model"
        self.base_url = "https://mock.invalid/v1"
        self.calls = []

    def chat(self, *, messages, request_id_hash, causal_interrupt_seq, max_tokens, temperature=0.0):
        self.calls.append({
            "messages": messages,
            "request_id_hash": request_id_hash,
            "causal_interrupt_seq": causal_interrupt_seq,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        if self.role == "oracle":
            content = json.dumps(VALID_CAPSULE)
        elif self.role == "anchor":
            prompt = json.loads(messages[-1]["content"])
            content = "GRAPH" if prompt.get("verified_graph_trace") else "NO_GRAPH"
        else:
            prompt = json.loads(messages[-1]["content"])
            # Deliberately synthetic outputs: demonstrate the interaction contrast,
            # not benchmark accuracy or real model behaviour.
            if "compiled_graph" in prompt and "anchor_hint" in prompt:
                content = "A"       # full composition correct
            elif "compiled_graph" in prompt:
                content = "B"       # graph without Anchor incorrect
            elif "capsule_payload" in prompt and "anchor_hint" in prompt:
                content = "B"       # Anchor without graph incorrect
            elif "capsule" in prompt:
                content = "A"       # capsule-only correct
            else:
                content = "B"       # original-context baseline incorrect
        return ProviderResult(
            content=content,
            model=self.model,
            duration_ms=1.0,
            attempts=[{
                "attempt_number": 1,
                "duration_ms": 1.0,
                "provider_generation_evidence": "CONFIRMED",
                "status": "success",
            }],
            events=[],
            usage={"input_tokens": 10, "output_tokens": 1},
            usage_evidence="PROVIDER_USAGE_REPORTED",
            provider_request_id_hash=None,
        )


class CompositionArmTests(unittest.TestCase):
    def test_all_five_arms_run_and_interaction_is_measurable(self):
        clients = {role: FakeClient(role) for role in ("render", "oracle", "anchor")}
        tasks = {
            "abercrombie": [
                {"index": 0, "fields": {"description": "sample source", "answer": "A"}}
            ]
        }
        sidecars = {
            "abercrombie": {
                "upstream_revision": "test-revision",
                "normalized_jsonl_sha256": "test-data-hash",
            }
        }
        manifest = {
            "task_allowlist": {
                "abercrombie": {
                    "labels": ["A", "B"],
                    "task_kind": "classification",
                    "task_description": "Select the correct label for the source.",
                }
            }
        }

        with tempfile.TemporaryDirectory() as temp:
            out_dir = Path(temp) / "run"
            out_dir.mkdir()
            with patch.object(
                runner.OpenAICompatibleClient,
                "from_env",
                side_effect=lambda role: clients[role],
            ):
                summary = runner.run_live(
                    tasks, sidecars, manifest, max_examples=1,
                    out_dir=out_dir, run_id="synthetic-arm-contract-test",
                )

            self.assertEqual(
                tuple(summary["conditions"]),
                ("baseline", "capsule_only", "capsule_graph_no_anchor",
                 "capsule_anchor_no_graph", "compiled_graph_gates"),
            )
            rows = summary["tasks"]["abercrombie"]
            self.assertEqual(set(rows), set(summary["conditions"]))
            self.assertEqual(rows["baseline"]["accuracy"], 0.0)
            self.assertEqual(rows["capsule_only"]["accuracy"], 1.0)
            self.assertEqual(rows["capsule_graph_no_anchor"]["accuracy"], 0.0)
            self.assertEqual(rows["capsule_anchor_no_graph"]["accuracy"], 0.0)
            self.assertEqual(rows["compiled_graph_gates"]["accuracy"], 1.0)

            case = json.loads((out_dir / "case-results.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(set(case["predictions"]), set(summary["conditions"]))
            self.assertEqual(case["predictions"]["compiled_graph_gates"]["label"], "A")
            self.assertEqual(case["predictions"]["capsule_graph_no_anchor"]["label"], "B")
            self.assertEqual(case["predictions"]["capsule_anchor_no_graph"]["label"], "B")

            anchor_prompts = [
                json.loads(call["messages"][-1]["content"])
                for call in clients["anchor"].calls
            ]
            self.assertEqual(len(anchor_prompts), 2)
            self.assertEqual(anchor_prompts[0]["verified_graph_trace"], [])
            self.assertTrue(anchor_prompts[1]["verified_graph_trace"])

    def test_prompt_constructors_separate_graph_and_anchor_treatments(self):
        from experiments.scrs_runtime.scrs_runtime import (
            build_capsule_anchor_render_messages,
            build_compiled_render_messages,
            compile_decision_graph,
        )

        fields = {"description": "sample"}
        labels = ["A", "B"]
        graph = compile_decision_graph("abercrombie", "contract-v1", "rev1", "hash1", labels)
        capsule = {
            "payload": VALID_CAPSULE,
        }
        trace = [{"gate_id": "CHECK", "decision": "ACCEPT"}]
        no_anchor = json.loads(build_compiled_render_messages(
            "abercrombie", "classify", labels, capsule, graph, trace, None
        )[-1]["content"])
        with_anchor = json.loads(build_compiled_render_messages(
            "abercrombie", "classify", labels, capsule, graph, trace, "HINT"
        )[-1]["content"])
        anchor_no_graph = json.loads(build_capsule_anchor_render_messages(
            "abercrombie", "classify", labels, capsule, "HINT"
        )[-1]["content"])

        self.assertNotIn("anchor_hint", no_anchor)
        self.assertEqual(with_anchor["anchor_hint"], "HINT")
        self.assertNotIn("compiled_graph", anchor_no_graph)
        self.assertNotIn("verified_gate_trace", anchor_no_graph)
        self.assertEqual(anchor_no_graph["anchor_hint"], "HINT")


if __name__ == "__main__":
    unittest.main()
