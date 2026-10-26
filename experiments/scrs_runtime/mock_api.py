"""A local-only OpenAI-compatible mock API for zero-cost SCRS pipeline tests.

This service never calls an external provider. Its deterministic outputs are
fixtures for integration testing, not predictions from a language model.
"""
from __future__ import annotations

import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


def _parse_user_prompt(payload: dict[str, Any]) -> dict[str, Any]:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        return {}
    for message in reversed(messages):
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            continue
        try:
            value = json.loads(message["content"])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return {}


def synthetic_response(payload: dict[str, Any]) -> str:
    """Return contract-valid synthetic content without consulting any gold label."""
    model = str(payload.get("model", ""))
    prompt = _parse_user_prompt(payload)

    if model.endswith("-oracle") and "required_json_schema" in prompt:
        source_fields = prompt.get("source_input_fields", {})
        field_names = sorted(source_fields) if isinstance(source_fields, dict) else []
        return json.dumps(
            {
                "decision_relevant_facts": [
                    "MOCK ONLY: capsule schema accepted; source field count="
                    + str(len(field_names))
                ],
                "conditions_or_qualifiers": [],
                "exceptions_or_contraindications": [],
                "ambiguities_or_unknowns": ["MOCK ONLY: semantic content was not evaluated"],
            },
            separators=(",", ":"),
        )

    if model.endswith("-anchor"):
        # A deliberately neutral hint, not a claim derived from source evidence.
        return "UNKNOWN"

    labels = prompt.get("allowed_labels")
    if not isinstance(labels, list) or not labels:
        # Defensive fallback for an unexpected prompt shape. The runner's strict
        # label parser will mark this as invalid rather than invent a label.
        return "__MOCK_UNRECOGNIZED_PROMPT__"

    task_id = str(prompt.get("task_id", "unknown-task"))
    # Vary fixtures deterministically by prompt. This only tests routing and
    # parsing; the result must never be interpreted as model quality.
    digest = hashlib.sha256(
        (task_id + "\n" + json.dumps(prompt, sort_keys=True, ensure_ascii=False)).encode("utf-8")
    ).digest()
    selected = labels[int.from_bytes(digest[:4], "big") % len(labels)]
    return str(selected)


class MockApiServer(ThreadingHTTPServer):
    """Threaded local endpoint with request counters for test diagnostics."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, server_address):
        super().__init__(server_address, MockApiHandler)
        self.request_count = 0
        self.request_models: list[str] = []
        self.request_errors: list[str] = []


class MockApiHandler(BaseHTTPRequestHandler):
    server: MockApiServer

    def log_message(self, format: str, *args: Any) -> None:
        # Request content may contain benchmark inputs; never print it.
        return

    def do_POST(self) -> None:
        if self.path.rstrip("/") != "/v1/chat/completions":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 2_000_000:
                raise ValueError("invalid request body size")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("request body must be an object")
            content = synthetic_response(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            self.server.request_errors.append(type(exc).__name__)
            body = json.dumps({"error": {"message": "invalid mock request"}}).encode("utf-8")
            self.send_response(400)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.server.request_count += 1
        self.server.request_models.append(str(payload.get("model", "")))
        body = json.dumps(
            {
                "id": "mock-completion-not-a-provider-response",
                "object": "chat.completion",
                "model": str(payload.get("model", "mock-model")),
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                # Usage is intentionally omitted: mock token counts and billing
                # must not be mistaken for provider measurements.
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Request-ID", "mock-request-not-provider")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
