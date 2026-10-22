# Replacement draft — Section 8.4: Telemetry and reproducibility

Collect a request-level record and a separate event-level record for each Oracle/Anchor transport attempt. The request record should identify the configuration and deployment version, anonymized request identifier, terminal regime, end-to-end start/end timestamps, token counts, costs, and terminal status. Event-level records should include event type, parent event, attempt number, provider request identifier (redacted or pseudonymized), queue interval, TTFT, TPOT, input/output tokens, retry/batch status, model, region, and price tier.

For the local runtime, capture generation start/end, rendering start/end, halt-decision timestamp, partial tokens at halt, and fallback start/end. Use monotonic timestamps for durations and UTC timestamps for correlation. Keep logical interrupt events, transport attempts, billed generations, and token totals separate.

Do not log API keys, raw prompts, full responses, or unredacted user identifiers. Document missing telemetry, sampling, clock assumptions, provider-side visibility limits, and software versions. A CSV template and JSON field schema are provided under `telemetry/`.

End-to-end latency alone cannot reconstruct queue wait, TTFT, TPOT, Anchor call counts, or overlap between local generation and remote calls. P50/P95 claims must be computed from event-linked request traces or clearly labelled simulation output.
