"""Instrumented OpenAI-compatible chat client for SCRS model and Anchor calls.

The client does not contain credentials. It reads credentials from environment
variables supplied by the caller and never serializes request prompts or keys to
telemetry. It records attempts and provider outcomes separately.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import time
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


# Process-wide pacing shared by render/oracle/Anchor clients. It is opt-in and
# measured between transport-attempt starts, not between successful responses.
_RATE_LOCK = threading.Lock()
_LAST_PROVIDER_ATTEMPT_START = 0.0


def _pace_provider_attempt(min_interval_seconds: float) -> None:
    global _LAST_PROVIDER_ATTEMPT_START
    if min_interval_seconds <= 0:
        return
    with _RATE_LOCK:
        now = time.monotonic()
        delay = min_interval_seconds - (now - _LAST_PROVIDER_ATTEMPT_START)
        if delay > 0:
            time.sleep(delay)
        _LAST_PROVIDER_ATTEMPT_START = time.monotonic()


class ProviderConfigurationError(RuntimeError):
    """Missing or inconsistent configuration for a live model endpoint."""


class ProviderRequestError(RuntimeError):
    """A provider request failed and carries its captured attempt evidence."""

    def __init__(self, message: str, *, attempts=None, events=None):
        super().__init__(message)
        self.attempts = list(attempts or [])
        self.events = list(events or [])


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ProviderResult:
    content: str
    model: str
    duration_ms: float
    attempts: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, int] | None = None
    usage_evidence: str = "UNAVAILABLE"
    provider_request_id_hash: str | None = None


class OpenAICompatibleClient:
    """Small dependency-free client for /chat/completions-compatible APIs."""

    RETRYABLE_HTTP_CODES = {408, 409, 425, 429, 500, 502, 503, 504}

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str | None,
        role: str,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        allow_unauthenticated: bool = False,
        max_token_parameter: str | None = None,
        reasoning_mode: bool | None = None,
        extra_body: dict[str, Any] | None = None,
        min_interval_seconds: float = 0.0,
    ) -> None:
        base_url = (base_url or "").strip().rstrip("/")
        model = (model or "").strip()
        if not base_url or not model:
            raise ProviderConfigurationError("A non-empty base URL and model ID are required.")
        if timeout_seconds <= 0:
            raise ProviderConfigurationError("timeout_seconds must be positive.")
        if max_retries < 0 or max_retries > 5:
            raise ProviderConfigurationError("max_retries must be between 0 and 5.")
        if min_interval_seconds < 0 or min_interval_seconds > 60:
            raise ProviderConfigurationError("min_interval_seconds must be between 0 and 60.")
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ProviderConfigurationError("Provider base URL must be an absolute HTTP(S) URL.")
        is_loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if not (api_key and api_key.strip()) and not (is_loopback or allow_unauthenticated):
            raise ProviderConfigurationError(
                "A provider API key is required unless the endpoint is loopback or "
                "SCRS_ALLOW_UNAUTHENTICATED_ENDPOINT=true is explicitly set."
            )
        if parsed.scheme != "https" and not is_loopback:
            raise ProviderConfigurationError("Non-loopback provider endpoints must use HTTPS.")

        if max_token_parameter is not None and max_token_parameter not in {"max_tokens", "max_completion_tokens"}:
            raise ProviderConfigurationError(
                "max_token_parameter must be max_tokens or max_completion_tokens."
            )
        is_openai_api = parsed.hostname == "api.openai.com"
        # Reasoning-model request semantics follow the configured model/provider
        # contract, not only the hostname: OpenAI-compatible proxies can serve
        # o-series and GPT-5 models too. Explicit per-role configuration wins.
        model_lower = model.casefold()
        inferred_reasoning_mode = model_lower.startswith(("o1", "o3", "o4", "gpt-5"))
        if reasoning_mode is not None and not isinstance(reasoning_mode, bool):
            raise ProviderConfigurationError("reasoning_mode must be true, false, or None.")
        openai_reasoning_family = (
            inferred_reasoning_mode if reasoning_mode is None else reasoning_mode
        )
        selected_token_parameter = max_token_parameter or (
            "max_completion_tokens" if is_openai_api or openai_reasoning_family else "max_tokens"
        )
        self.base_url = base_url
        self.model = model
        self.api_key = (api_key or "").strip()
        self.role = role
        self.timeout_seconds = float(timeout_seconds)
        self.max_retries = int(max_retries)
        self.min_interval_seconds = float(min_interval_seconds)
        self.max_token_parameter = selected_token_parameter
        self.is_openai_api = is_openai_api
        self.openai_reasoning_family = openai_reasoning_family
        if extra_body is not None and not isinstance(extra_body, dict):
            raise ProviderConfigurationError("extra_body must be a JSON object.")
        reserved = {"model", "messages", "max_tokens", "max_completion_tokens", "stream", "temperature"}
        overlap = sorted(reserved.intersection(extra_body or {}))
        if overlap:
            raise ProviderConfigurationError(
                "Provider extra body cannot override core request field(s): " + ", ".join(overlap)
            )
        try:
            json.dumps(extra_body or {}, ensure_ascii=False, sort_keys=True)
        except (TypeError, ValueError) as exc:
            raise ProviderConfigurationError("Provider extra body must contain JSON-compatible values.") from exc
        self.extra_body = dict(extra_body or {})

    @classmethod
    def from_env(cls, role: str = "render") -> "OpenAICompatibleClient":
        """Create a client with shared defaults and role-specific overrides."""
        prefix = {
            "render": "SCRS_RENDER",
            "oracle": "SCRS_ORACLE",
            "anchor": "SCRS_ANCHOR",
        }.get(role)
        if prefix is None:
            raise ProviderConfigurationError(f"Unknown client role: {role!r}")
        base_url = os.getenv(f"{prefix}_BASE_URL") or os.getenv("SCRS_BASE_URL") or "https://api.openai.com/v1"
        model = (
            os.getenv(f"{prefix}_MODEL")
            or os.getenv("SCRS_MODEL", "")
        )
        api_key = (
            os.getenv(f"{prefix}_API_KEY")
            or os.getenv("SCRS_API_KEY")
            or None
        )
        allow_unauthenticated = os.getenv("SCRS_ALLOW_UNAUTHENTICATED_ENDPOINT", "").lower() == "true"
        timeout = float(os.getenv("SCRS_PROVIDER_TIMEOUT_SECONDS", "60"))
        retries = int(os.getenv("SCRS_PROVIDER_MAX_RETRIES", "2"))
        min_interval = float(os.getenv("SCRS_PROVIDER_MIN_INTERVAL_SECONDS", "0"))
        token_parameter = (
            os.getenv(f"{prefix}_MAX_TOKEN_PARAMETER")
            or os.getenv("SCRS_MAX_TOKEN_PARAMETER")
            or None
        )
        raw_reasoning_mode = (
            os.getenv(f"{prefix}_REASONING_MODE")
            or os.getenv("SCRS_REASONING_MODE")
            or ""
        ).strip().lower()
        if raw_reasoning_mode and raw_reasoning_mode not in {"true", "false"}:
            raise ProviderConfigurationError(
                f"{prefix}_REASONING_MODE / SCRS_REASONING_MODE must be 'true' or 'false'."
            )
        reasoning_mode = (
            raw_reasoning_mode == "true" if raw_reasoning_mode else None
        )
        raw_extra_body = os.getenv("SCRS_PROVIDER_EXTRA_BODY_JSON", "").strip()
        try:
            extra_body = json.loads(raw_extra_body) if raw_extra_body else {}
        except json.JSONDecodeError as exc:
            raise ProviderConfigurationError(
                "SCRS_PROVIDER_EXTRA_BODY_JSON must be valid JSON."
            ) from exc
        if not isinstance(extra_body, dict):
            raise ProviderConfigurationError(
                "SCRS_PROVIDER_EXTRA_BODY_JSON must decode to a JSON object."
            )
        return cls(
            base_url=base_url,
            model=model,
            api_key=api_key,
            role=role,
            timeout_seconds=timeout,
            max_retries=retries,
            allow_unauthenticated=allow_unauthenticated,
            max_token_parameter=token_parameter,
            reasoning_mode=reasoning_mode,
            extra_body=extra_body,
            min_interval_seconds=min_interval,
        )

    def _event_id(self, request_id_hash: str, sequence: int, attempt: int, event_type: str) -> str:
        # Stable identity: request ID hash + causal sequence + attempt + type.
        return _sha(f"{request_id_hash}:{sequence}:{attempt}:{event_type}")[:32]

    def chat(
        self,
        *,
        messages: list[dict[str, str]],
        request_id_hash: str,
        causal_interrupt_seq: int,
        max_tokens: int,
        temperature: float = 0.0,
    ) -> ProviderResult:
        if not request_id_hash or not isinstance(request_id_hash, str):
            raise ValueError("request_id_hash must be a non-empty string.")
        if causal_interrupt_seq < 0:
            raise ValueError("causal_interrupt_seq must be non-negative.")
        if max_tokens < 1:
            raise ValueError("max_tokens must be positive.")
        if not messages or any(
            not isinstance(m, dict) or not isinstance(m.get("role"), str) or not isinstance(m.get("content"), str)
            for m in messages
        ):
            raise ValueError("messages must contain role/content string objects.")

        url = self.base_url + "/chat/completions"
        request_messages = messages
        if self.openai_reasoning_family:
            request_messages = [
                {**message, "role": "developer"} if message.get("role") == "system" else message
                for message in messages
            ]
        payload_object = {
            "model": self.model,
            "messages": request_messages,
            self.max_token_parameter: max_tokens,
            "stream": False,
        }
        if not self.openai_reasoning_family:
            payload_object["temperature"] = temperature
        payload_object.update(self.extra_body)
        payload = json.dumps(
            payload_object,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        start_total = time.monotonic()
        attempts: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        last_error = "provider request failed"
        provider_request_id_hash = None

        for attempt_number in range(1, self.max_retries + 2):
            _pace_provider_attempt(self.min_interval_seconds)
            retry_delay_override: float | None = None
            started = time.monotonic()
            start_ms = round(started * 1000, 3)
            status = "unknown"
            provider_evidence = "UNKNOWN"
            unknown_reason = "TRANSPORT_ERROR"
            http_status: int | None = None
            usage: dict[str, int] | None = None
            body: dict[str, Any] | None = None
            returned_request_id: str | None = None
            retry_reason: str | None = None

            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "SCRS-research-anchor-client/1.0",
            }
            if self.api_key:
                headers["Authorization"] = "Bearer " + self.api_key
            req = Request(url, data=payload, headers=headers, method="POST")

            try:
                with urlopen(req, timeout=self.timeout_seconds) as response:
                    http_status = getattr(response, "status", None)
                    returned_request_id = response.headers.get("x-request-id")
                    raw = response.read()
                decoded = json.loads(raw.decode("utf-8"))
                if not isinstance(decoded, dict):
                    raise ValueError("provider response JSON must be an object")
                choices = decoded.get("choices")
                if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
                    raise ValueError("provider response has no choices[0]")
                message = choices[0].get("message")
                if not isinstance(message, dict) or not isinstance(message.get("content"), str):
                    raise ValueError("provider response has no textual choices[0].message.content")
                body = decoded
                usage_raw = decoded.get("usage")
                if isinstance(usage_raw, dict):
                    input_tokens = usage_raw.get("prompt_tokens", usage_raw.get("input_tokens"))
                    output_tokens = usage_raw.get("completion_tokens", usage_raw.get("output_tokens"))
                    if (
                        isinstance(input_tokens, int) and not isinstance(input_tokens, bool) and input_tokens >= 0
                        and isinstance(output_tokens, int) and not isinstance(output_tokens, bool) and output_tokens >= 0
                    ):
                        usage = {"input_tokens": input_tokens, "output_tokens": output_tokens}
                status = "success"
                provider_evidence = "CONFIRMED"
                unknown_reason = ""
            except HTTPError as exc:
                http_status = exc.code
                status = f"http_{exc.code}"
                provider_evidence = "UNKNOWN"
                unknown_reason = "TRANSPORT_ERROR"
                last_error = f"HTTP {exc.code}"
                if exc.code == 429:
                    # Rate-limit responses are not retried aggressively. Retry only
                    # when the provider supplies a bounded Retry-After instruction.
                    raw_retry_after = getattr(exc, "headers", None)
                    raw_retry_after = raw_retry_after.get("Retry-After") if raw_retry_after else None
                    try:
                        parsed_retry_after = float(raw_retry_after) if raw_retry_after is not None else None
                    except (TypeError, ValueError):
                        parsed_retry_after = None
                    if (
                        parsed_retry_after is not None
                        and 1.0 <= parsed_retry_after <= 30.0
                        and attempt_number <= self.max_retries
                    ):
                        retry_delay_override = parsed_retry_after
                        retry_reason = "HTTP_429_RETRY_AFTER"
                    else:
                        retry_reason = None
                elif exc.code in self.RETRYABLE_HTTP_CODES and attempt_number <= self.max_retries:
                    retry_reason = f"HTTP_{exc.code}"
                else:
                    retry_reason = None
                if retry_reason is None:
                    attempts.append({
                        "attempt_number": attempt_number, "status": status, "http_status": http_status,
                        "duration_ms": round((time.monotonic() - started) * 1000, 3),
                        "provider_generation_evidence": provider_evidence,
                        "provider_generation_unknown_reason": unknown_reason,
                    })
                    self._append_attempt_event(events, request_id_hash, causal_interrupt_seq, attempt_number,
                                               start_ms, started, status, http_status, provider_evidence,
                                               unknown_reason, retry_reason, returned_request_id, None)
                    raise ProviderRequestError(
                        f"{self.role} provider returned HTTP {exc.code}; response body intentionally omitted.",
                        attempts=attempts,
                        events=events,
                    ) from None
            except (TimeoutError, socket.timeout):
                status = "timeout"
                provider_evidence = "UNKNOWN"
                unknown_reason = "TIMEOUT_OUTCOME_UNKNOWN"
                last_error = "timeout outcome unknown"
                if attempt_number <= self.max_retries:
                    retry_reason = "TIMEOUT"
            except URLError as exc:
                if isinstance(getattr(exc, "reason", None), (TimeoutError, socket.timeout)):
                    status = "timeout"
                    provider_evidence = "UNKNOWN"
                    unknown_reason = "TIMEOUT_OUTCOME_UNKNOWN"
                    last_error = "timeout outcome unknown"
                    retry_reason = "TIMEOUT" if attempt_number <= self.max_retries else None
                else:
                    status = "transport_error"
                    provider_evidence = "UNKNOWN"
                    unknown_reason = "TRANSPORT_ERROR"
                    last_error = "transport error"
                    retry_reason = "TRANSPORT_ERROR" if attempt_number <= self.max_retries else None
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                status = "malformed_response"
                provider_evidence = "UNKNOWN"
                unknown_reason = "PROVIDER_RESPONSE_MALFORMED"
                last_error = "malformed provider response"
                if attempt_number <= self.max_retries:
                    retry_reason = "PROVIDER_RESPONSE_MALFORMED"

            duration = round((time.monotonic() - started) * 1000, 3)
            attempts.append({
                "attempt_number": attempt_number, "status": status, "http_status": http_status,
                "duration_ms": duration, "provider_generation_evidence": provider_evidence,
                "provider_generation_unknown_reason": unknown_reason or None, "retry_reason": retry_reason,
            })
            self._append_attempt_event(events, request_id_hash, causal_interrupt_seq, attempt_number,
                                       start_ms, started, status, http_status, provider_evidence,
                                       unknown_reason, retry_reason, returned_request_id, usage)

            if body is not None:
                provider_request_id_hash = _sha(returned_request_id)[:20] if returned_request_id else None
                content = body["choices"][0]["message"]["content"]
                observed_model = decoded.get("model")
                if not isinstance(observed_model, str) or not observed_model.strip():
                    observed_model = self.model
                observed_model = observed_model.strip()
                self._append_provider_response_event(events, request_id_hash, causal_interrupt_seq,
                                                     attempt_number, start_ms, started,
                                                     provider_request_id_hash, usage)
                # Transport attempts record the requested route; a confirmed provider
                # response records the model ID returned by the endpoint.
                events[-1]["model"] = observed_model
                return ProviderResult(
                    content=content,
                    model=observed_model,
                    duration_ms=round((time.monotonic() - start_total) * 1000, 3),
                    attempts=attempts,
                    events=events,
                    usage=usage,
                    usage_evidence="PROVIDER_USAGE_REPORTED" if usage is not None else "UNAVAILABLE",
                    provider_request_id_hash=provider_request_id_hash,
                )

            if retry_reason:
                delay = retry_delay_override
                if delay is None:
                    delay = min(0.5 * (2 ** (attempt_number - 1)), 4.0)
                time.sleep(delay)
                continue

            raise ProviderRequestError(
                f"{self.role} provider failed: {last_error}; response body omitted.",
                attempts=attempts,
                events=events,
            )

        raise ProviderRequestError(
            f"{self.role} provider failed after retries: {last_error}.",
            attempts=attempts,
            events=events,
        )

    def _append_attempt_event(
        self,
        events: list[dict[str, Any]],
        request_id_hash: str,
        sequence: int,
        attempt_number: int,
        start_ms: float,
        started_monotonic: float,
        status: str,
        http_status: int | None,
        evidence: str,
        reason: str,
        retry_reason: str | None,
        raw_request_id: str | None,
        usage: dict[str, int] | None,
    ) -> None:
        event_type = "anchor_transport_attempt" if self.role == "anchor" else "model_transport_attempt"
        now_monotonic = time.monotonic()
        event = {
            "request_id_hash": request_id_hash,
            "event_id": self._event_id(request_id_hash, sequence, attempt_number, event_type),
            "event_id_composition": [request_id_hash, sequence, attempt_number, event_type],
            "parent_event_id": None,
            "causal_interrupt_seq": sequence,
            "event_type": event_type,
            "provider_request_id_redacted": _sha(raw_request_id)[:20] if raw_request_id else None,
            "attempt_number": attempt_number,
            "batch_id": None,
            "start_monotonic_ms": start_ms,
            "end_monotonic_ms": round(now_monotonic * 1000, 3),
            "queue_wait_ms": None,
            "utc_correlation_timestamp": _utc_now(),
            "ttft_ms": None,
            "tpot_ms_per_token": None,
            "input_tokens": usage.get("input_tokens") if usage else None,
            "input_token_basis": "returned" if usage else None,
            "output_tokens": usage.get("output_tokens") if usage else None,
            "output_token_basis": "returned" if usage else None,
            "evidence_status": "provider-confirmed" if evidence == "CONFIRMED" else "unknown",
            "provider_generation_evidence": evidence,
            "provider_generation_unknown_reason": reason or None,
            "status": status,
            "http_status": http_status,
            "retry_reason": retry_reason,
            "model": self.model,
            "region": None,
            "price_tier": None,
            "ingest_replay_mark": False,
            "ingest_conflict_flag": False,
        }
        events.append(event)

    def _append_provider_response_event(
        self,
        events: list[dict[str, Any]],
        request_id_hash: str,
        sequence: int,
        attempt_number: int,
        start_ms: float,
        started_monotonic: float,
        request_id_hash_from_provider: str | None,
        usage: dict[str, int] | None,
    ) -> None:
        event_type = "anchor_provider_response" if self.role == "anchor" else "model_provider_response"
        now_monotonic = time.monotonic()
        events.append({
            "request_id_hash": request_id_hash,
            "event_id": self._event_id(request_id_hash, sequence, attempt_number, event_type),
            "event_id_composition": [request_id_hash, sequence, attempt_number, event_type],
            "parent_event_id": self._event_id(
                request_id_hash, sequence, attempt_number,
                "anchor_transport_attempt" if self.role == "anchor" else "model_transport_attempt"
            ),
            "causal_interrupt_seq": sequence,
            "event_type": event_type,
            "provider_request_id_redacted": request_id_hash_from_provider,
            "attempt_number": attempt_number,
            "batch_id": None,
            "start_monotonic_ms": start_ms,
            "end_monotonic_ms": round(now_monotonic * 1000, 3),
            "queue_wait_ms": None,
            "utc_correlation_timestamp": _utc_now(),
            "ttft_ms": None,
            "tpot_ms_per_token": None,
            "input_tokens": usage.get("input_tokens") if usage else None,
            "input_token_basis": "returned" if usage else None,
            "output_tokens": usage.get("output_tokens") if usage else None,
            "output_token_basis": "returned" if usage else None,
            "evidence_status": "provider-confirmed",
            "provider_generation_evidence": "CONFIRMED",
            "provider_generation_unknown_reason": None,
            "status": "success",
            "retry_reason": None,
            "model": self.model,
            "region": None,
            "price_tier": None,
            "ingest_replay_mark": False,
            "ingest_conflict_flag": False,
        })


class AnchorClient:
    """Executable Anchor-generation adapter with a hard max-token cap."""

    def __init__(self, client: OpenAICompatibleClient, max_tokens: int = 5) -> None:
        if max_tokens < 1 or max_tokens > 5:
            raise ValueError("SCRS Anchor generation is capped at 5 output tokens in this prototype.")
        self.client = client
        self.max_tokens = max_tokens

    def generate_anchors(
        self,
        *,
        task_description: str,
        allowed_labels: list[str],
        capsule: dict[str, Any],
        graph_trace: list[dict[str, Any]],
        request_id_hash: str,
        causal_interrupt_seq: int = 1,
    ) -> ProviderResult:
        prompt = {
            "task": task_description,
            "allowed_labels": allowed_labels,
            "capsule": capsule,
            "verified_graph_trace": graph_trace,
            "instruction": (
                "Return exactly one short evidence phrase of one to five output tokens, "
                "copying the most decision-relevant words from decision_relevant_facts. "
                "Do not output a classification label, explanation, or punctuation. "
                "If no useful fact exists, return UNKNOWN."
            ),
        }
        return self.client.chat(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an Anchor extractor. Read only the supplied capsule. "
                        "Return exactly one short evidence phrase of 1–5 output tokens, "
                        "copying the most decision-relevant words from decision_relevant_facts. "
                        "Do not output a classification label, explanation, or punctuation. "
                        "If no useful fact exists, return UNKNOWN."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False, sort_keys=True)},
            ],
            request_id_hash=request_id_hash,
            causal_interrupt_seq=causal_interrupt_seq,
            max_tokens=self.max_tokens,
            temperature=0.0,
        )
