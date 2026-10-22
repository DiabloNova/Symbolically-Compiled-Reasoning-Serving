# Replacement draft — Section 8.4: Telemetry and reproducibility

Collect a request-level record and a separate event-level record for each logical interrupt, transport attempt, provider response, and full-reasoning fallback operation. A request record identifies the anonymized request, configuration and software versions, terminal regime, request start/end times, final status, and the summary counters defined in Section 8.3. Event records must link to the parent request and, where applicable, to the logical interrupt that caused an attempt.

## Counter definitions and evidence

Keep these quantities separate:

- `anchor_interrupt_count`: logical interrupt events accepted by the local runtime.
- `anchor_transport_attempt_count`: actual Anchor transport attempts, including retries.
- `anchor_provider_generation_count`: provider generations confirmed by response or billing evidence.
- `anchor_tokens_returned`: tokens returned by successful Anchor responses.
- `anchor_tokens_billed`: tokens reported as billable by the provider.
- `full_oracle_fallback_count`: full-reasoning fallback operations initiated after a miss or halt.
- `full_oracle_transport_attempt_count` and `full_oracle_provider_generation_count`: full-fallback attempts and confirmed generations, separate from Anchor activity.

For each count, document its unit, request scope, increment point, and evidence source. A transport timeout does not establish whether the provider generated or billed a response. Record the attempt as observed and the provider outcome as unknown until reconciled; do not treat missing provider telemetry as zero. If the provider does not expose generation-level billing, label the metric unavailable and state the limitation.

## Event record

At minimum, event records should include: event ID; parent request ID; causal interrupt ID where applicable; event type; monotonic start/end times; UTC correlation timestamp; attempt number; retry/batch/cache status; provider request ID in redacted or pseudonymized form; outcome/error category; model and region; input/output token values and whether they are returned or billed; cost basis and price tier; and an explicit evidence status such as `observed`, `provider-confirmed`, `estimated`, or `unknown`.

For local execution, capture candidate admission, gate result, deterministic-execution outcome, rendering start/end, interrupt predicate and accepted interrupt timestamp, partial tokens at halt, fallback start/end, and terminal regime. Use monotonic timestamps for duration calculations and UTC timestamps for cross-system correlation. State how duplicate events are deduplicated and how partial or missing records affect aggregates.

## Derived metrics

Do not emit the original `oracleCallsAvoided = (n_int == 0)` metric. Report `full_oracle_fallback_avoided` only as a request-level outcome derived from a known terminal regime and a zero `full_oracle_fallback_count`. This means full reasoning fallback was avoided; it does not mean that Anchor requests or all Oracle traffic were avoided. If fallback status is unknown, the derived value is unknown.

Request-level and event-level records must be joined before calculating counts, token totals, cost, or latency distributions. Report denominators and missing-data rates. Do not equate logical interrupts, transport attempts, provider generations, and token totals, and do not infer provider billing from client-side attempts alone.

## Privacy and latency validity

Do not log API keys, raw prompts, full responses, or unredacted user identifiers. Document sampling, clock assumptions, provider-side visibility limits, missing telemetry, software versions, and the exact aggregation procedure. End-to-end latency alone cannot reconstruct queue wait, TTFT, TPOT, retries, Anchor calls, or overlap between local generation and remote calls. P50/P95 claims must be computed from event-linked request traces or clearly labelled simulation output.
