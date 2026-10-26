# Runnable SCRS + Anchor LegalBench prototype

This folder adds a **reference execution prototype**, not a claim that the full SCRS architecture from the manuscript has been implemented in production. It makes the three requested paths executable against the pinned LegalBench test data and an OpenAI-compatible inference endpoint:

1. **baseline:** full source context -> classifier;
2. **capsule-only:** source context -> model-produced capsule -> classifier that receives only the capsule;
3. **compiled graph + gates + Anchor:** source context -> shared capsule -> fixed decision graph and fail-closed compatibility gates -> bounded real Anchor API call (maximum five output tokens) -> renderer. A rejected gate falls back to a full-context model call; fallback is recorded.

## Configure a live provider

No API key is committed. Set these environment variables in a trusted local environment or as repository Actions secrets:

- \`SCRS_API_KEY\`: required unless using an explicitly permitted loopback inference endpoint.
- \`SCRS_MODEL\`: model ID used by the renderer and (unless overridden) the capsule extractor and Anchor.
- Optional \`SCRS_BASE_URL\`: OpenAI-compatible endpoint base URL, default \`https://api.openai.com/v1\`.
- Optional \`SCRS_RENDER_MODEL\`, \`SCRS_RENDER_API_KEY\`, \`SCRS_RENDER_BASE_URL\`.
- Optional \`SCRS_ORACLE_MODEL\`, \`SCRS_ORACLE_API_KEY\`, \`SCRS_ORACLE_BASE_URL\` for capsule extraction.
- Optional \`SCRS_ANCHOR_MODEL\`, \`SCRS_ANCHOR_API_KEY\`, \`SCRS_ANCHOR_BASE_URL\` for the actual Anchor client.
- Optional \`SCRS_PROVIDER_TIMEOUT_SECONDS\` (default 60), \`SCRS_PROVIDER_MAX_RETRIES\` (default 2), \`SCRS_CAPSULE_MAX_TOKENS\` (default 384), and \`SCRS_PREDICTION_MAX_TOKENS\` (default 16).

The endpoint must implement \`POST /chat/completions\` with \`choices[0].message.content\`. For external endpoints, HTTPS and an API key are required. Loopback URLs can be unauthenticated; an unauthenticated non-loopback endpoint is rejected unless the caller explicitly opts in with \`SCRS_ALLOW_UNAUTHENTICATED_ENDPOINT=true\`.

## Verify data and runtime without making model calls

From the repository root:

\`\`\`sh
python -m unittest discover -s tests -p 'test_scrs_live_runtime.py' -v
python experiments/scrs_runtime/run_legalbench.py --tasks all --max-examples 2 --validate-only
\`\`\`

The validation-only command checks the full archive hash, pinned upstream revision, all manifest-approved splits, selected task rows, prompt construction, capsule schema, and graph gates. It does **not** generate predictions.

## Run a live pilot

A small pilot uses two test rows per selected task (12 total across six tasks):

\`\`\`sh
python experiments/scrs_runtime/run_legalbench.py --tasks all --max-examples 2
\`\`\`

Use \`--tasks abercrombie --max-examples 10\` for a 10-row task pilot. To run every row in all six test splits (799 rows total), use \`--tasks all --full\`. Full evaluation may consume substantial provider tokens; the command defaults to a small pilot and does not silently run all rows.

Run outputs are written under \`results/public-benchmarks/live-runs/<run_id>/\`: request-linked events, capsule/graph traces, per-condition predictions, metrics, a run manifest, and redacted failures. Model output is accepted only when it matches an allowed task label exactly; invalid outputs count as incorrect and are reported. API keys, raw prompts, and full provider responses are never written to telemetry.

## Accounting and evidence boundaries

- All three paths use the same selected source examples, allowed-label inventory, temperature zero, and pinned data revision. Record exact model IDs and provider endpoints in the run manifest.
- Capsule extraction is run once per source row and shared by the capsule-only and compiled-graph counterfactuals. Its usage is charged to each compressed path in the per-path comparison, while run-wide usage counts the physical call once; this policy is recorded in outputs.
- Anchor uses a separate instrumented transport client and a hard \`max_tokens=5\` cap. Logical interrupts, HTTP attempts/retries, successful provider generations, and provider-reported usage are recorded separately.
- A provider-reported usage object is not automatically treated as a bill. Total monetary cost remains \`NR\` unless current pricing and billing semantics are supplied and documented.
- P50/P95 production latency, general semantic preservation, zero transfer errors, and overall SCRS superiority cannot be claimed from a small pilot. Report task-level accuracy, invalid-output rate, confusion matrix, Wilson interval, model version, configuration, and raw event traces.

## Reference implementation limits

The extractor and renderer are live model calls and the Anchor client issues real HTTP requests, but this implementation is a research prototype. The compiler is a fixed schema/version/provenance graph rather than a production general-purpose reasoning AST. Its gates prevent incompatible/stale/unknown capsules from entering the fast path, but they do not establish upstream domain-extraction correctness or decision-semantic preservation. Those must be evaluated separately.
