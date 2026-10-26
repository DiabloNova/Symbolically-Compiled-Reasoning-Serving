#!/usr/bin/env python3
"""Run paired baseline, capsule-only, and compiled-graph+Anchor LegalBench predictions.

This command performs real inference when configured with an OpenAI-compatible
provider. Without provider credentials it fails closed. --validate-only verifies
the revision-pinned public dataset and exercises prompt/gate construction without
generating or fabricating predictions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tarfile
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "data"))
sys.path.insert(0, str(ROOT / "scripts" / "evaluation"))

from verify_public_evidence_snapshot import verify_archive  # noqa: E402
from score_legalbench import score_rows, ScoringError  # noqa: E402
from experiments.scrs_runtime.anchor_client import (  # noqa: E402
    AnchorClient,
    OpenAICompatibleClient,
    ProviderConfigurationError,
    ProviderRequestError,
)
from experiments.scrs_runtime.scrs_runtime import (  # noqa: E402
    CapsuleValidationError,
    build_capsule_messages,
    build_capsule_only_messages,
    build_compiled_render_messages,
    build_full_messages,
    build_task_record,
    canonical_json,
    compile_decision_graph,
    create_capsule,
    parse_capsule_payload,
    parse_label,
    sha256_json,
    source_input_fields,
    task_description,
    task_contract_version,
    validate_capsule,
)

DATA_MANIFEST = ROOT / "data" / "manifests" / "legalbench.json"
DATA_ARCHIVE = ROOT / "data" / "public" / "legalbench" / "extra-licensed-snapshots-v1.tar.gz"
EXPECTED_ARCHIVE_SHA256 = "f2eed6bdf3bf08d5837c33c04634e1fbb32544ac1d0e1eeacd20e034ce0ade0a"
EXPECTED_UPSTREAM_REVISION = "daec8237410aa23e3faf4bc41ad8b3a7e1696826"
CONDITIONS = ("baseline", "capsule_only", "compiled_graph_gates")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl_bytes(raw: bytes, expected_task: str, expected_split: str) -> list[dict[str, Any]]:
    rows = []
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{expected_task}/{expected_split}: line {line_no} is not an object.")
        if row.get("task") != expected_task or row.get("split") != expected_split:
            raise ValueError(f"{expected_task}/{expected_split}: task/split marker mismatch at line {line_no}.")
        if not isinstance(row.get("index"), int) or not isinstance(row.get("fields"), dict):
            raise ValueError(f"{expected_task}/{expected_split}: malformed normalized row at line {line_no}.")
        rows.append(row)
    if not rows:
        raise ValueError(f"{expected_task}/{expected_split}: archive member has no rows.")
    return rows


def load_verified_task_data(task_ids: list[str]) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    manifest = json.loads(DATA_MANIFEST.read_text(encoding="utf-8"))
    verification = verify_archive(
        DATA_ARCHIVE,
        DATA_MANIFEST,
        expected_sha=EXPECTED_ARCHIVE_SHA256,
        revision=EXPECTED_UPSTREAM_REVISION,
    )
    if verification["archive_sha256"] != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("Verified archive hash unexpectedly differs from the pinned hash.")
    if verification["upstream_revision"] != EXPECTED_UPSTREAM_REVISION:
        raise ValueError("Verified upstream revision unexpectedly differs from the preregistered revision.")

    tasks: dict[str, list[dict[str, Any]]] = {}
    sidecars: dict[str, dict[str, Any]] = {}
    with tarfile.open(DATA_ARCHIVE, "r:gz") as archive:
        members = {m.name: m for m in archive.getmembers()}
        for task_id in task_ids:
            if task_id not in manifest.get("task_allowlist", {}):
                raise ValueError(f"Task {task_id!r} is not in the explicit manifest allowlist.")
            if manifest["task_allowlist"][task_id].get("status") != "approved":
                raise ValueError(f"Task {task_id!r} is not approved by the manifest.")
            prefix = f"data/public/legalbench/{task_id}/test"
            jsonl_name = prefix + ".jsonl"
            sidecar_name = prefix + ".run-manifest.json"
            if jsonl_name not in members or sidecar_name not in members:
                raise ValueError(f"Verified archive is missing the test data or sidecar for {task_id}.")
            jsonl_file = archive.extractfile(members[jsonl_name])
            sidecar_file = archive.extractfile(members[sidecar_name])
            if jsonl_file is None or sidecar_file is None:
                raise ValueError(f"Cannot read archive members for task {task_id}.")
            rows = read_jsonl_bytes(jsonl_file.read(), task_id, "test")
            sidecar = json.loads(sidecar_file.read().decode("utf-8"))
            tasks[task_id] = rows
            sidecars[task_id] = sidecar
    return {**manifest, "_archive_verification": verification}, tasks, sidecars


def exact_task_ids(manifest: dict[str, Any], raw: str) -> list[str]:
    approved = sorted(manifest["task_allowlist"])
    if raw.strip().lower() == "all":
        return approved
    requested = [x.strip() for x in raw.split(",") if x.strip()]
    unknown = sorted(set(requested) - set(approved))
    if not requested or unknown:
        raise ValueError(f"Unknown/empty task selection. Unknown={unknown}; allowed={approved}.")
    if len(set(requested)) != len(requested):
        raise ValueError("Task selection contains duplicates.")
    return requested


def new_request_id(run_id: str, task_id: str, index: int) -> str:
    return digest_text(f"{run_id}:{task_id}:{index}")[:32]


def call_record(result: Any, kind: str, condition: str, seq: int) -> dict[str, Any]:
    return {
        "call_kind": kind,
        "condition": condition,
        "causal_sequence": seq,
        "model": result.model,
        "duration_ms": result.duration_ms,
        "attempt_count": len(result.attempts),
        "attempts": result.attempts,
        "usage": result.usage,
        "usage_evidence": result.usage_evidence,
        "provider_request_id_hash": result.provider_request_id_hash,
    }


def annotate_events(events: list[dict[str, Any]], run_id: str, task_id: str,
                    row_index: int, condition: str, call_kind: str) -> list[dict[str, Any]]:
    enriched = []
    for event in events:
        enriched.append({
            **event,
            "benchmark_run_id": run_id,
            "task_id": task_id,
            "row_index": row_index,
            "condition": condition,
            "call_kind": call_kind,
        })
    return enriched


def logical_interrupt_event(request_id_hash: str, sequence: int, run_id: str,
                            task_id: str, index: int, start_ms: float, end_ms: float) -> dict[str, Any]:
    event_type = "anchor_interrupt"
    event_id = digest_text(f"{request_id_hash}:{sequence}:0:{event_type}")[:32]
    return {
        "request_id_hash": request_id_hash,
        "event_id": event_id,
        "event_id_composition": [request_id_hash, sequence, 0, event_type],
        "parent_event_id": None,
        "causal_interrupt_seq": sequence,
        "event_type": event_type,
        "attempt_number": 0,
        "batch_id": None,
        "start_monotonic_ms": round(start_ms, 3),
        "end_monotonic_ms": round(end_ms, 3),
        "utc_correlation_timestamp": utc_now(),
        "queue_wait_ms": None,
        "ttft_ms": None,
        "tpot_ms_per_token": None,
        "input_tokens": None,
        "input_token_basis": None,
        "output_tokens": None,
        "output_token_basis": None,
        "evidence_status": "observed",
        "provider_generation_evidence": "UNAVAILABLE",
        "provider_generation_unknown_reason": None,
        "status": "accepted",
        "retry_reason": None,
        "model": None,
        "region": None,
        "price_tier": None,
        "ingest_replay_mark": False,
        "ingest_conflict_flag": False,
        "benchmark_run_id": run_id,
        "task_id": task_id,
        "row_index": index,
        "condition": "compiled_graph_gates",
        "call_kind": "logical_interrupt",
    }


def record_result(outputs: dict[str, Any], condition: str, prediction: str | None,
                  request_hash: str, index: int, calls: list[dict[str, Any]],
                  terminal_regime: str, gate_trace: list[dict[str, Any]] | None = None) -> None:
    outputs[condition] = {
        "index": index,
        "prediction": prediction if prediction is not None else "__INVALID__",
        "prediction_valid": prediction is not None,
        "request_id_hash": request_hash,
        "terminal_regime": terminal_regime,
        "calls": calls,
        "gate_trace": gate_trace or [],
    }


def metrics_for(task_id: str, rows: list[dict[str, Any]], predictions: list[dict[str, Any]],
                labels: list[str]) -> dict[str, Any]:
    lookup = {r["index"]: r for r in rows}
    if len(predictions) != len(rows) or {p["index"] for p in predictions} != set(lookup):
        raise ValueError(f"{task_id}: prediction coverage does not match selected rows.")
    normalized_labels = {label.casefold(): label for label in labels}
    counts = {label: {"tp": 0, "fp": 0, "fn": 0, "support": 0} for label in labels}
    confusion = {label: {pred: 0 for pred in labels + ["__INVALID__"]} for label in labels}
    correct = 0
    invalid = 0
    for pred in predictions:
        actual = str(lookup[pred["index"]]["fields"]["answer"])
        guess = pred.get("prediction")
        actual_canonical = normalized_labels.get(actual.casefold())
        guess_canonical = normalized_labels.get(str(guess).casefold()) if isinstance(guess, str) else None
        if actual_canonical is None:
            raise ValueError(f"{task_id}: gold label {actual!r} is not in the allowlisted label inventory.")
        if guess_canonical is None:
            invalid += 1
            confusion[actual_canonical]["__INVALID__"] += 1
            counts[actual_canonical]["fn"] += 1
            counts[actual_canonical]["support"] += 1
            continue
        confusion[actual_canonical][guess_canonical] += 1
        counts[actual_canonical]["support"] += 1
        if actual_canonical == guess_canonical:
            correct += 1
            counts[actual_canonical]["tp"] += 1
        else:
            counts[actual_canonical]["fn"] += 1
            counts[guess_canonical]["fp"] += 1

    per_class = {}
    for label, c in counts.items():
        precision = c["tp"] / (c["tp"] + c["fp"]) if c["tp"] + c["fp"] else 0.0
        recall = c["tp"] / (c["tp"] + c["fn"]) if c["tp"] + c["fn"] else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
        per_class[label] = {"support": c["support"], "precision": precision, "recall": recall, "f1": f1}
    accuracy = correct / len(rows) if rows else 0.0
    # Wilson 95% interval; invalid labels count as incorrect for accuracy.
    z = 1.959963984540054
    n = len(rows)
    if n:
        p = accuracy
        z2 = z * z
        denom = 1 + z2 / n
        center = (p + z2 / (2 * n)) / denom
        margin = z * ((p * (1 - p) + z2 / (4 * n)) / n) ** 0.5 / denom
        ci = [max(0.0, center - margin), min(1.0, center + margin)]
    else:
        ci = None
    return {
        "task_id": task_id,
        "n": n,
        "correct": correct,
        "invalid_outputs": invalid,
        "valid_prediction_rate": (n - invalid) / n if n else None,
        "accuracy": accuracy,
        "accuracy_ci95_wilson": ci,
        "macro_precision": sum(x["precision"] for x in per_class.values()) / len(labels),
        "macro_recall": sum(x["recall"] for x in per_class.values()) / len(labels),
        "macro_f1": sum(x["f1"] for x in per_class.values()) / len(labels),
        "per_class": per_class,
        "confusion_matrix": confusion,
        "strict_existing_scorer": "not-run-invalid-output" if invalid else "compatible",
    }


def validate_mode(tasks: dict[str, list[dict[str, Any]]], sidecars: dict[str, dict[str, Any]],
                  task_manifest: dict[str, Any], max_examples: int, out_dir: Path) -> dict[str, Any]:
    report = {
        "run_status": "VALIDATION_ONLY",
        "predictions_generated": False,
        "evidence_status": "data/gate/prompt validation only; no model inference",
        "archive_verification": task_manifest["_archive_verification"],
        "tasks": {},
    }
    for task_id, rows in tasks.items():
        task_info = task_manifest["task_allowlist"][task_id]
        sidecar = sidecars[task_id]
        revision = sidecar["upstream_revision"]
        selected = rows if max_examples <= 0 else rows[:max_examples]
        examples = []
        for row in selected:
            record = build_task_record(
                task_id, row["index"], row["fields"], task_info, revision
            )
            msgs = build_full_messages(task_id, record["description"], record["labels"], record["input_fields"])
            capsule_msgs = build_capsule_messages(task_id, record["description"], record["labels"], record["input_fields"])
            if "answer" in record["input_fields"]:
                raise ValueError("Gold label was exposed in input fields.")
            facts = {
                "decision_relevant_facts": ["fixture fact"],
                "conditions_or_qualifiers": [],
                "exceptions_or_contraindications": [],
                "ambiguities_or_unknowns": [],
            }
            capsule = create_capsule(task_id, record["task_contract_version"], revision,
                                     record["input_fields"], record["labels"], facts)
            graph = compile_decision_graph(task_id, record["task_contract_version"], revision,
                                           record["source_input_sha256"], record["labels"])
            accepted, trace = validate_capsule(capsule, graph, task_id, record["task_contract_version"],
                                               revision, record["input_fields"], record["labels"])
            if not accepted:
                raise ValueError(f"{task_id}/{row['index']}: constructed reference capsule failed gates.")
            examples.append({
                "index": row["index"],
                "input_sha256": record["source_input_sha256"],
                "full_prompt_sha256": digest_text(canonical_json(msgs)),
                "capsule_prompt_sha256": digest_text(canonical_json(capsule_msgs)),
                "gate_count": len(trace) - 1,
                "gate_terminal": trace[-1]["decision"],
            })
        report["tasks"][task_id] = {
            "gold_rows_total": len(rows),
            "rows_selected_for_validation": len(selected),
            "task_contract_version": task_contract_version(task_id, task_info, revision),
            "upstream_revision": revision,
            "task_test_manifest_sha256": digest_text(canonical_json(sidecar)),
            "examples": examples,
        }
    write_json(out_dir / "validation_report.json", report)
    return report


def run_live(tasks: dict[str, list[dict[str, Any]]], sidecars: dict[str, dict[str, Any]],
             task_manifest: dict[str, Any], max_examples: int, out_dir: Path,
             run_id: str) -> dict[str, Any]:
    # Configuration is validated before any provider call. No test predictions
    # are synthesized if keys/models are unavailable.
    render_client = OpenAICompatibleClient.from_env("render")
    oracle_client = OpenAICompatibleClient.from_env("oracle")
    anchor_provider = OpenAICompatibleClient.from_env("anchor")
    anchor_client = AnchorClient(anchor_provider, max_tokens=5)
    capsule_tokens = int(os.getenv("SCRS_CAPSULE_MAX_TOKENS", "384"))
    prediction_tokens = int(os.getenv("SCRS_PREDICTION_MAX_TOKENS", "16"))
    if not 64 <= capsule_tokens <= 2048:
        raise ValueError("SCRS_CAPSULE_MAX_TOKENS must be between 64 and 2048.")
    if not 1 <= prediction_tokens <= 128:
        raise ValueError("SCRS_PREDICTION_MAX_TOKENS must be between 1 and 128.")

    all_results: dict[str, dict[str, list[dict[str, Any]]]] = {
        task_id: {condition: [] for condition in CONDITIONS} for task_id in tasks
    }
    all_cases: list[dict[str, Any]] = []
    total_provider_calls = 0
    total_confirmed_generations = 0
    total_reported_input_tokens = 0
    total_reported_output_tokens = 0
    event_path = out_dir / "events.jsonl"
    for task_id, rows in tasks.items():
        info = task_manifest["task_allowlist"][task_id]
        sidecar = sidecars[task_id]
        revision = sidecar["upstream_revision"]
        description = task_description(task_id, info)
        labels = info["labels"]
        selected = rows if max_examples <= 0 else rows[:max_examples]
        for row in selected:
            task_record = build_task_record(task_id, row["index"], row["fields"], info, revision)
            request_hash = new_request_id(run_id, task_id, row["index"])
            case_start = time.monotonic()
            outputs: dict[str, Any] = {}
            calls_by_condition: dict[str, list[dict[str, Any]]] = {c: [] for c in CONDITIONS}
            gate_trace: list[dict[str, Any]] = []
            capsule = None
            capsule_status = "NOT_CREATED"
            seq = 0

            def invoke(client: OpenAICompatibleClient, messages: list[dict[str, str]], call_kind: str,
                       condition: str, max_tokens: int, sequence: int):
                nonlocal total_provider_calls, total_confirmed_generations
                nonlocal total_reported_input_tokens, total_reported_output_tokens
                result = client.chat(
                    messages=messages,
                    request_id_hash=request_hash,
                    causal_interrupt_seq=sequence,
                    max_tokens=max_tokens,
                    temperature=0.0,
                )
                total_provider_calls += result.attempts.__len__()
                total_confirmed_generations += sum(
                    1 for e in result.events if e.get("event_type") in {"model_provider_response", "anchor_provider_response"}
                )
                if result.usage:
                    total_reported_input_tokens += result.usage["input_tokens"]
                    total_reported_output_tokens += result.usage["output_tokens"]
                call = call_record(result, call_kind, condition, sequence)
                call["prompt_sha256"] = digest_text(canonical_json(messages))
                call["request_id_hash"] = request_hash
                calls_by_condition[condition].append(call)
                append_jsonl(event_path, annotate_events(result.events, run_id, task_id, row["index"], condition, call_kind))
                return result

            try:
                # Condition A: full-context baseline.
                seq += 1
                baseline_result = invoke(
                    render_client,
                    build_full_messages(task_id, description, labels, task_record["input_fields"]),
                    "full_context_classifier", "baseline", prediction_tokens, seq
                )
                baseline_label = parse_label(baseline_result.content, labels)
                record_result(outputs, "baseline", baseline_label, request_hash, row["index"],
                              calls_by_condition["baseline"], "BASELINE")

                # One capsule is compiled for the two compressed conditions. Its
                # preprocessing usage is allocated to both condition-level costs,
                # while the run-level usage counts the provider call only once.
                seq += 1
                capsule_result = invoke(
                    oracle_client,
                    build_capsule_messages(task_id, description, labels, task_record["input_fields"]),
                    "capsule_extraction", "capsule_only", capsule_tokens, seq
                )
                try:
                    payload = parse_capsule_payload(capsule_result.content)
                    capsule = create_capsule(task_id, task_record["task_contract_version"], revision,
                                             task_record["input_fields"], labels, payload)
                    capsule_status = "VALID"
                except CapsuleValidationError:
                    capsule_status = "INVALID_MODEL_OUTPUT"

                # Condition B: capsule-only. Invalid capsule output is preserved
                # as invalid and counted wrong; it is never replaced by a fake label.
                if capsule is not None:
                    seq += 1
                    cap_result = invoke(
                        render_client,
                        build_capsule_only_messages(task_id, description, labels, capsule),
                        "capsule_only_classifier", "capsule_only", prediction_tokens, seq
                    )
                    cap_label = parse_label(cap_result.content, labels)
                else:
                    cap_label = None
                record_result(outputs, "capsule_only", cap_label, request_hash, row["index"],
                              calls_by_condition["capsule_only"], "CAPSULE_ONLY")

                # Condition C: executable compiled graph and compatibility gates.
                if capsule is not None:
                    graph = compile_decision_graph(
                        task_id, task_record["task_contract_version"], revision,
                        task_record["source_input_sha256"], labels
                    )
                    accepted, gate_trace = validate_capsule(
                        capsule, graph, task_id, task_record["task_contract_version"],
                        revision, task_record["input_fields"], labels
                    )
                else:
                    graph = None
                    accepted = False
                    gate_trace = [{
                        "sequence": 1, "gate_id": "CAPSULE_SCHEMA",
                        "decision": "REJECT", "reason_code": "CAPSULE_OUTPUT_INVALID",
                        "details_redacted": "capsule extractor output failed schema validation",
                    }, {
                        "sequence": 2, "gate_id": "TERMINAL", "decision": "FALLBACK",
                        "reason_code": "FAIL_CLOSED_FALLBACK",
                        "details_redacted": "invalid capsule cannot enter compiled fast path",
                    }]
                graph_trace_path = out_dir / "traces" / task_id / f"{row['index']}.json"
                write_json(graph_trace_path, {
                    "run_id": run_id, "task_id": task_id, "index": row["index"],
                    "capsule_status": capsule_status, "capsule": capsule,
                    "compiled_graph": graph, "gate_trace": gate_trace,
                })
                if accepted and capsule is not None and graph is not None:
                    # One logical interrupt is accepted by the compiled renderer;
                    # transport retries and provider generations are separately logged.
                    logical_start = time.monotonic() * 1000
                    seq += 1
                    anchor_result = anchor_client.generate_anchors(
                        task_description=description,
                        allowed_labels=labels,
                        capsule=capsule["payload"],
                        graph_trace=gate_trace,
                        request_id_hash=request_hash,
                        causal_interrupt_seq=seq,
                    )
                    logical_end = time.monotonic() * 1000
                    logical = logical_interrupt_event(request_hash, seq, run_id, task_id, row["index"],
                                                      logical_start, logical_end)
                    append_jsonl(event_path, [logical])
                    append_jsonl(event_path, annotate_events(anchor_result.events, run_id, task_id,
                                                             row["index"], "compiled_graph_gates", "anchor_generation"))
                    total_provider_calls += len(anchor_result.attempts)
                    total_confirmed_generations += sum(
                        1 for e in anchor_result.events if e.get("event_type") == "anchor_provider_response"
                    )
                    if anchor_result.usage:
                        total_reported_input_tokens += anchor_result.usage["input_tokens"]
                        total_reported_output_tokens += anchor_result.usage["output_tokens"]
                    calls_by_condition["compiled_graph_gates"].append(
                        call_record(anchor_result, "anchor_generation", "compiled_graph_gates", seq)
                    )
                    calls_by_condition["compiled_graph_gates"][-1]["prompt_sha256"] = "redacted-anchor-prompt-hash-not-persisted"
                    calls_by_condition["compiled_graph_gates"][-1]["request_id_hash"] = request_hash

                    seq += 1
                    render_result = invoke(
                        render_client,
                        build_compiled_render_messages(task_id, description, labels, capsule,
                                                       graph, gate_trace, anchor_result.content),
                        "compiled_graph_renderer", "compiled_graph_gates", prediction_tokens, seq
                    )
                    compiled_label = parse_label(render_result.content, labels)
                    terminal = "FAST_PATH"
                else:
                    # Gate rejection must fall back to the full-context provider path.
                    seq += 1
                    fallback_result = invoke(
                        render_client,
                        build_full_messages(task_id, description, labels, task_record["input_fields"]),
                        "full_context_fallback", "compiled_graph_gates", prediction_tokens, seq
                    )
                    compiled_label = parse_label(fallback_result.content, labels)
                    terminal = "FALLBACK"
                calls_by_condition["compiled_graph_gates"].append({
                    "call_kind": "compiled_graph_gate",
                    "condition": "compiled_graph_gates",
                    "gate_accepted": accepted,
                    "terminal_regime": terminal,
                    "trace_path": str(graph_trace_path.relative_to(out_dir)),
                })
                record_result(outputs, "compiled_graph_gates", compiled_label, request_hash, row["index"],
                              calls_by_condition["compiled_graph_gates"], terminal, gate_trace)

                case = {
                    "run_id": run_id,
                    "task_id": task_id,
                    "index": row["index"],
                    "gold_label": row["fields"]["answer"],
                    "source_input_sha256": task_record["source_input_sha256"],
                    "task_contract_version": task_record["task_contract_version"],
                    "capsule_status": capsule_status,
                    "predictions": {
                        condition: {
                            "label": outputs[condition]["prediction"],
                            "valid": outputs[condition]["prediction_valid"],
                            "terminal_regime": outputs[condition]["terminal_regime"],
                        } for condition in CONDITIONS
                    },
                    "elapsed_wall_ms": round((time.monotonic() - case_start) * 1000, 3),
                    "usage_attribution_policy": (
                        "Capsule extraction usage is included in each compressed condition's per-path "
                        "usage summary; run-level provider usage counts the shared extraction call once."
                    ),
                }
                all_cases.append(case)
                for condition in CONDITIONS:
                    prediction = outputs[condition]
                    all_results[task_id][condition].append({
                        "index": row["index"],
                        "prediction": prediction["prediction"],
                        "prediction_valid": prediction["prediction_valid"],
                    })
                append_jsonl(out_dir / "case-results.jsonl", [case])
            except (ProviderConfigurationError, ProviderRequestError, ValueError) as exc:
                # Save a redacted failure report and stop rather than fabricate outputs.
                failure = {
                    "run_id": run_id,
                    "run_status": "FAILED_PROVIDER_OR_CAPSULE_ERROR",
                    "timestamp_utc": utc_now(),
                    "failed_task": task_id,
                    "failed_index": row.get("index"),
                    "error_type": type(exc).__name__,
                    "error_message_redacted": str(exc),
                    "predictions_completed": len(all_cases),
                    "partial_results_preserved": True,
                }
                write_json(out_dir / "failure.json", failure)
                raise

    metrics: dict[str, Any] = {}
    for task_id, task_rows in tasks.items():
        selected_rows = task_rows if max_examples <= 0 else task_rows[:max_examples]
        metrics[task_id] = {}
        for condition in CONDITIONS:
            preds = all_results[task_id][condition]
            metrics[task_id][condition] = metrics_for(
                task_id, selected_rows, preds, task_manifest["task_allowlist"][task_id]["labels"]
            )
            # Use the strict existing scorer as a second check when every prediction
            # is a valid label; otherwise keep the custom metrics and make strict score non-publishable.
            if all(x["prediction_valid"] for x in preds):
                gold_rows = selected_rows
                simple_predictions = [{"index": p["index"], "prediction": p["prediction"]} for p in preds]
                metrics[task_id][condition]["strict_existing_scorer"] = score_rows(
                    gold_rows, simple_predictions,
                    allowed_labels=task_manifest["task_allowlist"][task_id]["labels"]
                )
            write_json(out_dir / "predictions" / task_id / f"{condition}.json", {
                "run_id": run_id,
                "task_id": task_id,
                "condition": condition,
                "model": render_client.model,
                "upstream_revision": sidecars[task_id]["upstream_revision"],
                "gold_sha256": sidecars[task_id]["normalized_jsonl_sha256"],
                "predictions": preds,
            })
    summary = {
        "run_id": run_id,
        "run_status": "COMPLETED",
        "timestamp_utc": utc_now(),
        "experiment_type": "live-provider-paired-legalbench-pilot",
        "conditions": list(CONDITIONS),
        "tasks": metrics,
        "execution": {
            "render_model": render_client.model,
            "oracle_model": oracle_client.model,
            "anchor_model": anchor_provider.model,
            "render_endpoint": render_client.base_url,
            "oracle_endpoint": oracle_client.base_url,
            "anchor_endpoint": anchor_provider.base_url,
            "temperature": 0.0,
            "anchor_max_tokens": anchor_client.max_tokens,
            "capsule_max_tokens": capsule_tokens,
            "prediction_max_tokens": prediction_tokens,
            "retried_requests_included": True,
            "provider_billed_cost": "NR; API token usage is reported separately and prices/accounting are not configured.",
        },
        "run_usage": {
            "provider_transport_attempts": total_provider_calls,
            "confirmed_provider_generations": total_confirmed_generations,
            "provider_reported_input_tokens": total_reported_input_tokens,
            "provider_reported_output_tokens": total_reported_output_tokens,
        },
        "evidence_boundary": (
            "Live provider predictions for the selected LegalBench rows only. Pilot metrics do not establish "
            "general SCRS semantic preservation, production latency, or provider-billed cost. Capsule-extraction "
            "usage is shared physically and allocated to each compressed counterfactual for per-path comparison."
        ),
    }
    write_json(out_dir / "metrics.json", summary)
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="all", help="all or comma-separated allowlisted task IDs")
    parser.add_argument("--max-examples", type=int, default=2,
                        help="First N rows per selected task; use 0 or --full for all test rows.")
    parser.add_argument("--full", action="store_true", help="Use every test row for each selected task.")
    parser.add_argument("--validate-only", action="store_true", help="Verify data/gates/prompts without provider calls.")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results/public-benchmarks/live-runs")
    parser.add_argument("--run-id", help="Optional unique run ID; defaults to a UTC timestamp plus random suffix.")
    args = parser.parse_args(argv)
    if args.max_examples < 0:
        parser.error("--max-examples must be non-negative.")
    if args.full:
        args.max_examples = 0
    if not args.validate_only and not args.run_id:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    else:
        run_id = args.run_id or ("validation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    out_dir = args.output_root / run_id
    out_dir.mkdir(parents=True, exist_ok=False)
    try:
        manifest = json.loads(DATA_MANIFEST.read_text(encoding="utf-8"))
        task_ids = exact_task_ids(manifest, args.tasks)
        manifest, tasks, sidecars = load_verified_task_data(task_ids)
        run_manifest = {
            "run_id": run_id,
            "created_at_utc": utc_now(),
            "tasks": task_ids,
            "split": "test",
            "selected_examples_per_task": "all" if args.max_examples == 0 else args.max_examples,
            "archive_sha256": manifest["_archive_verification"]["archive_sha256"],
            "upstream_revision": manifest["_archive_verification"]["upstream_revision"],
            "provider_calls_enabled": not args.validate_only,
            "credentials_recorded": False,
            "outputs_directory": str(out_dir),
        }
        write_json(out_dir / "run-manifest.json", run_manifest)
        if args.validate_only:
            report = validate_mode(tasks, sidecars, manifest, args.max_examples, out_dir)
            report["run_id"] = run_id
            report["run_manifest"] = run_manifest
            write_json(out_dir / "validation_report.json", report)
            print(json.dumps({
                "run_status": report["run_status"],
                "predictions_generated": False,
                "tasks": {k: v["rows_selected_for_validation"] for k, v in report["tasks"].items()},
                "archive_sha256": report["archive_verification"]["archive_sha256"],
                "output_dir": str(out_dir),
            }, indent=2))
            return 0
        try:
            summary = run_live(tasks, sidecars, manifest, args.max_examples, out_dir, run_id)
        except (ProviderConfigurationError, ProviderRequestError, ValueError) as exc:
            if not (out_dir / "failure.json").exists():
                write_json(out_dir / "failure.json", {
                    "run_id": run_id,
                    "run_status": "FAILED_CONFIGURATION_OR_PROVIDER",
                    "timestamp_utc": utc_now(),
                    "error_type": type(exc).__name__,
                    "error_message_redacted": str(exc),
                    "predictions_generated": False,
                })
            print(f"Live run failed closed: {type(exc).__name__}: {exc}", file=sys.stderr)
            return 2
        print(json.dumps({
            "run_status": summary["run_status"],
            "run_id": run_id,
            "metrics_path": str(out_dir / "metrics.json"),
            "tasks": {k: {c: v["accuracy"] for c, v in t.items()} for k, t in summary["tasks"].items()},
        }, indent=2))
        return 0
    except (OSError, ValueError, json.JSONDecodeError, tarfile.TarError, ScoringError) as exc:
        write_json(out_dir / "failure.json", {
            "run_id": run_id,
            "run_status": "FAILED_DATA_OR_VALIDATION",
            "timestamp_utc": utc_now(),
            "error_type": type(exc).__name__,
            "error_message_redacted": str(exc),
            "predictions_generated": False,
        })
        print(f"Validation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
