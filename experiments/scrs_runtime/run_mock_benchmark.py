#!/usr/bin/env python3
"""Run the complete SCRS pipeline against a local mock API, without provider costs.

Outputs are explicitly marked synthetic. This is an integration smoke test only;
quality metrics are deliberately suppressed because mock labels are not model
predictions and cannot support scientific accuracy claims.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.scrs_runtime.mock_api import MockApiServer  # noqa: E402
from experiments.scrs_runtime import run_legalbench  # noqa: E402


MOCK_ENV = (
    "SCRS_API_KEY", "SCRS_RENDER_API_KEY", "SCRS_ORACLE_API_KEY", "SCRS_ANCHOR_API_KEY",
    "SCRS_BASE_URL", "SCRS_RENDER_BASE_URL", "SCRS_ORACLE_BASE_URL", "SCRS_ANCHOR_BASE_URL",
    "SCRS_MODEL", "SCRS_RENDER_MODEL", "SCRS_ORACLE_MODEL", "SCRS_ANCHOR_MODEL",
    "SCRS_PROVIDER_MAX_RETRIES", "SCRS_PROVIDER_TIMEOUT_SECONDS",
    "SCRS_ALLOW_UNAUTHENTICATED_ENDPOINT", "SCRS_MAX_TOKEN_PARAMETER",
)


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def mark_outputs_as_mock(out_dir: Path, server: MockApiServer, tasks: list[str], run_id: str) -> dict[str, Any]:
    manifest_path = out_dir / "run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest.update({
        "execution_mode": "LOCAL_MOCK_API_SIMULATION",
        "provider_calls_enabled": False,
        "external_provider_calls": 0,
        "model_predictions_generated": False,
        "mock_responses_generated": True,
        "mock_api_requests": server.request_count,
        "mock_api_models": sorted(set(server.request_models)),
        "mock_api_request_errors": len(server.request_errors),
        "quality_metrics_published": False,
        "evidence_boundary": (
            "Only synthetic deterministic responses from a local test server were used. "
            "No external provider was contacted. Do not interpret outputs as model predictions, "
            "benchmark accuracy, token usage, latency, cost, or evidence of semantic preservation."
        ),
    })
    write_json(manifest_path, manifest)

    # The live runner computes scores for contract validation; remove that score
    # report from the mock output so fabricated labels cannot be mistaken for evidence.
    metrics_path = out_dir / "metrics.json"
    if metrics_path.exists():
        metrics_path.unlink()

    prediction_files = 0
    for path in sorted((out_dir / "predictions").glob("*/*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        value["execution_mode"] = "LOCAL_MOCK_API_SIMULATION"
        value["prediction_evidence"] = "SYNTHETIC_FIXTURE_NOT_MODEL_INFERENCE"
        value["quality_metrics_published"] = False
        for prediction in value.get("predictions", []):
            prediction["evidence_mode"] = "synthetic_mock_response"
        write_json(path, value)
        prediction_files += 1

    cases_path = out_dir / "case-results.jsonl"
    cases = []
    if cases_path.exists():
        for line in cases_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                case = json.loads(line)
                case["execution_mode"] = "LOCAL_MOCK_API_SIMULATION"
                case["prediction_evidence"] = "SYNTHETIC_FIXTURE_NOT_MODEL_INFERENCE"
                for calls in case.get("call_usage_by_condition", {}).values():
                    for call in calls:
                        if not isinstance(call, dict):
                            continue
                        call["execution_mode"] = "LOCAL_MOCK_API_SIMULATION"
                        call["usage"] = None
                        call["usage_evidence"] = "UNAVAILABLE"
                        for attempt in call.get("attempts", []):
                            attempt["provider_generation_evidence"] = "UNAVAILABLE"
                            attempt["provider_generation_unknown_reason"] = None
                            attempt["evidence_scope"] = "mock HTTP response; not provider generation"
                cases.append(case)
        cases_path.write_text(
            "".join(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n" for case in cases),
            encoding="utf-8",
        )

    event_path = out_dir / "events.jsonl"
    event_count = 0
    if event_path.exists():
        updated_events = []
        for line in event_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            event = json.loads(line)
            event["execution_mode"] = "LOCAL_MOCK_API_SIMULATION"
            event["evidence_boundary"] = "Mock HTTP transport only; no provider generation occurred."
            if event.get("event_type") in {"model_provider_response", "anchor_provider_response"}:
                event["provider_generation_evidence"] = "UNAVAILABLE"
                event["provider_generation_unknown_reason"] = None
                event["evidence_status"] = "observed"
                event["status"] = "mock_response_returned"
            updated_events.append(event)
        event_count = len(updated_events)
        event_path.write_text(
            "".join(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n" for event in updated_events),
            encoding="utf-8",
        )

    for path in sorted((out_dir / "traces").glob("*/*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        value["execution_mode"] = "LOCAL_MOCK_API_SIMULATION"
        value["semantic_correctness_verified"] = False
        value["evidence_boundary"] = "Gate acceptance tests metadata/schema only; it is not proof that a synthetic capsule preserves meaning."
        write_json(path, value)

    gate_fast_path = sum(
        1 for case in cases
        if case.get("predictions", {}).get("compiled_graph_gates", {}).get("terminal_regime") == "FAST_PATH"
    )
    fallback_count = sum(
        1 for case in cases
        if case.get("predictions", {}).get("compiled_graph_gates", {}).get("terminal_regime") == "FALLBACK"
    )
    valid_capsules = sum(1 for case in cases if case.get("capsule_status") == "VALID")
    diagnostic = {
        "run_id": run_id,
        "run_status": "MOCK_SIMULATION_COMPLETED",
        "execution_mode": "LOCAL_MOCK_API_SIMULATION",
        "tasks_requested": tasks,
        "cases_exercised": len(cases),
        "prediction_files_written": prediction_files,
        "condition_predictions_written": sum(
            len(case.get("predictions", {})) for case in cases
        ),
        "mock_api_requests": server.request_count,
        "mock_api_request_errors": len(server.request_errors),
        "mock_api_models": sorted(set(server.request_models)),
        "event_records_written": event_count,
        "valid_synthetic_capsules": valid_capsules,
        "compiled_graph_fast_paths": gate_fast_path,
        "compiled_graph_fallbacks": fallback_count,
        "model_predictions_generated": False,
        "external_provider_calls": 0,
        "provider_usage_or_billing_measured": False,
        "benchmark_accuracy_reported": False,
        "quality_metrics": None,
        "reason_metrics_suppressed": (
            "Deterministic mock responses are not model outputs; accuracy or F1 on them would be misleading."
        ),
        "limitations": [
            "This proves the integration flow can execute against an API-compatible local fixture.",
            "The mock capsule is intentionally non-semantic and cannot test meaning preservation.",
            "Gate acceptance establishes schema/provenance compatibility only, not factual correctness.",
            "Synthetic outputs cannot support accuracy, token savings, latency, cost, or production claims.",
        ],
        "archive_sha256": manifest.get("archive_sha256"),
        "outputs_directory": str(out_dir),
    }
    write_json(out_dir / "mock-diagnostics.json", diagnostic)
    return diagnostic


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", default="all", help="all or comma-separated allowlisted task IDs")
    parser.add_argument("--max-examples", type=int, default=2, help="Rows per task; use 0 or --full for all test rows")
    parser.add_argument("--full", action="store_true", help="Run all selected test rows against the mock only")
    parser.add_argument("--output-root", type=Path, default=ROOT / "results/public-benchmarks/mock-runs")
    parser.add_argument("--run-id", help="Optional stable run identifier")
    args = parser.parse_args(argv)
    if args.max_examples < 0:
        parser.error("--max-examples must be non-negative")
    if args.full:
        args.max_examples = 0
    run_id = args.run_id or (
        "mock-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    )
    out_dir = args.output_root / run_id
    if out_dir.exists():
        parser.error(f"Output directory already exists: {out_dir}")

    prior_env = {name: os.environ.get(name) for name in MOCK_ENV}
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    server = MockApiServer(("127.0.0.1", 0))
    port = server.server_address[1]
    base_url = f"http://127.0.0.1:{port}/v1"
    try:
        os.environ["SCRS_BASE_URL"] = base_url
        os.environ["SCRS_RENDER_BASE_URL"] = base_url
        os.environ["SCRS_ORACLE_BASE_URL"] = base_url
        os.environ["SCRS_ANCHOR_BASE_URL"] = base_url
        os.environ["SCRS_MODEL"] = "scrs-mock-render"
        os.environ["SCRS_RENDER_MODEL"] = "scrs-mock-render"
        os.environ["SCRS_ORACLE_MODEL"] = "scrs-mock-oracle"
        os.environ["SCRS_ANCHOR_MODEL"] = "scrs-mock-anchor"
        os.environ["SCRS_PROVIDER_MAX_RETRIES"] = "0"
        os.environ["SCRS_PROVIDER_TIMEOUT_SECONDS"] = "5"
        os.environ["SCRS_ALLOW_UNAUTHENTICATED_ENDPOINT"] = "true"
        os.environ["SCRS_MAX_TOKEN_PARAMETER"] = "max_tokens"
        for name in ("SCRS_API_KEY", "SCRS_RENDER_API_KEY", "SCRS_ORACLE_API_KEY", "SCRS_ANCHOR_API_KEY"):
            os.environ.pop(name, None)

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        runner_args = [
            "--tasks", args.tasks,
            "--max-examples", str(args.max_examples),
            "--output-root", str(args.output_root),
            "--run-id", run_id,
        ]
        # Suppress the live runner's accuracy summary; mock quality metrics are
        # intentionally not part of this run's user-facing output.
        with open(os.devnull, "w", encoding="utf-8") as sink:
            with contextlib.redirect_stdout(sink):
                result = run_legalbench.main(runner_args)
        if result != 0:
            return result
        task_ids = [part.strip() for part in args.tasks.split(",") if part.strip()] if args.tasks.lower() != "all" else []
        if args.tasks.lower() == "all":
            plan = json.loads((ROOT / "data/manifests/legalbench.json").read_text(encoding="utf-8"))
            task_ids = sorted(plan["task_allowlist"])
        diagnostic = mark_outputs_as_mock(out_dir, server, task_ids, run_id)
        print(json.dumps(diagnostic, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        print(f"Mock benchmark failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    finally:
        server.shutdown()
        server.server_close()
        for name, value in prior_env.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


if __name__ == "__main__":
    raise SystemExit(main())
