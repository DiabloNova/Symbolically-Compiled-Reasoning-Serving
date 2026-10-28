# Zero-cost SCRS mock pipeline

## Purpose

The mock runner exercises the end-to-end reference implementation without an external model, API key, account credit, or network inference request. It starts a local OpenAI-compatible HTTP endpoint, runs the same LegalBench orchestration used by the live runner, and writes diagnostic traces.

This is an **integration test only**. The fixture returns deterministic synthetic labels and a deliberately non-semantic capsule. Its outputs are not language-model predictions and must not be used to estimate accuracy, semantic preservation, token reduction, latency, cost, or production performance.

## Run locally

From the repository root, with Python 3.12 (or a compatible supported Python):

    python -m unittest discover -s tests -p "test_scrs_mock_api.py" -v
    python experiments/scrs_runtime/run_mock_benchmark.py \
      --tasks all --max-examples 2 \
      --output-root results/public-benchmarks/mock-runs \
      --run-id local-mock-pilot

The default run exercises two test rows for each of the six approved tasks. It creates no external API requests and needs no credentials. The full flag exercises all selected rows against the local fixture; it is still synthetic and is not a replacement for a real benchmark run.

## Output safety

The output folder contains:

- **mock-diagnostics.json:** counts and integration status, without accuracy metrics.
- **predictions/:** synthetic outputs, each tagged SYNTHETIC_FIXTURE_NOT_MODEL_INFERENCE.
- **events.jsonl:** local mock transport traces, explicitly marked as mock execution; provider-generation evidence is unavailable.
- **traces/:** gate and capsule records annotated to state that schema/provenance acceptance does not prove semantic correctness.
- **run-manifest.json:** execution mode, verified input archive hash, and evidence boundary.

The runner deliberately removes metrics.json after exercising the live orchestration because any accuracy computed against deterministic fixtures would be misleading. It never reads the gold answer to choose a synthetic label. The capsule fixture only tests schema and plumbing; it does not attempt semantic extraction.

## What this validates

It can demonstrate that the selected source data loads, the three paths invoke the expected client roles, capsule parsing and graph gates complete, outputs/traces are written, and synthetic evidence is labeled.

It does **not** validate whether the capsule preserves meaning, whether an Anchor improves reasoning, or whether SCRS is more accurate, cheaper, or faster than a real baseline model. Those claims require a real model experiment or a separate mathematically justified analytical result.
