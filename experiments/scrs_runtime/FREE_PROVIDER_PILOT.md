# Reproducible zero-cost provider pilot configuration

This is a research pilot configuration for the SCRS reference runner, not a production service recommendation. Free-model availability, routing, shared rate limits, and reported usage may change without notice.

## Provider settings used for the 2026-10-27 follow-up pilot

- OpenAI-compatible base URL: https://ai-gateway.kilo.ai/api/v1
- Model ID: dots-studio/dots-3-note-preview:free
- API key: not used for the tested anonymous free endpoint
- Temperature: 0
- Capsule maximum output tokens: 384
- Classifier maximum output tokens: 16
- Anchor maximum output tokens: 5 (hard cap in the current runner)
- Provider retry count: 1
- Request extension JSON: {"reasoning":{"effort":"none"}}

The request extension is required for this model on the tested gateway path because, without an explicit non-thinking setting, the model used its completion budget for reasoning text and returned no label content. The extension is now supplied through the versioned client setting SCRS_PROVIDER_EXTRA_BODY_JSON and its key set/hash is recorded in the run manifest. The client rejects extension fields that would override the model, messages, token budget, temperature, or streaming contract.

## Environment

Set these variables in the shell running the pilot:

    SCRS_BASE_URL=https://ai-gateway.kilo.ai/api/v1
    SCRS_MODEL=dots-studio/dots-3-note-preview:free
    SCRS_ALLOW_UNAUTHENTICATED_ENDPOINT=true
    SCRS_PROVIDER_EXTRA_BODY_JSON='{"reasoning":{"effort":"none"}}'
    SCRS_PROVIDER_TIMEOUT_SECONDS=80
    SCRS_PROVIDER_MAX_RETRIES=1
    SCRS_CAPSULE_MAX_TOKENS=384
    SCRS_PREDICTION_MAX_TOKENS=16

The no-key exception is explicitly enabled because this particular provider endpoint was observed to accept unauthenticated free-model requests. Do not set the exception for an endpoint that is not intentionally anonymous. Non-loopback requests still require HTTPS.

Example command:

    python experiments/scrs_runtime/run_legalbench.py \
      --tasks all --max-examples 8 --sample-seed 20261027 \
      --output-root results/public-benchmarks/live-runs \
      --run-id kilo-free-seeded-pilot-2026-10-27

## Evidence and audit rules

- Pin and record the LegalBench archive SHA-256 and upstream revision.
- Record the exact selected test row indices and seed. A fixed seed makes the selection repeatable; it does not make stochastic model generation deterministic.
- The same model ID is used for baseline classification, capsule extraction, capsule-only classification, Anchor, and compiled renderer in this pilot. This is an implementation constraint and a source of role confounding, not an optimized multi-model configuration.
- Preserve raw prediction files, event logs, capsule traces, failures, retries, usage counts, and wall-time records.
- Report provider-reported token counts separately from any cost estimate. The SCRS runner currently does not calculate a billed dollar cost; cost remains not recorded unless a provider-specific price source and billing evidence are added.
- Never treat the model's returned usage cost field as a complete invoice. A zero reported cost means the selected endpoint reported zero for that request, not that all future requests or alternate routes are guaranteed free.
- Keep the six-task small pilot and subsequent larger pilot distinct. The first run selected two rows per task; follow-up runs using a seed select rows from the full pinned test split.
- The compiled-graph path includes fail-closed gates and fallback. Report fallback counts; do not describe every completed result as a pure fast-path execution.
