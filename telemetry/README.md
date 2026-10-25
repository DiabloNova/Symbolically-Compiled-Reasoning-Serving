# SCRS telemetry contract checker

validate_telemetry.py checks consistency between request-level summaries and request-linked event rows under telemetry-schema.json (schema version 2). It is an **offline reference checker**: it does not instrument or validate a production SCRS runtime or Anchor client and cannot establish real retry, batching, generation, or billing behaviour.

## Run the contract suite

From the repository root:

\`\`\`sh
python -m unittest discover -s tests -p 'test_telemetry_validation.py' -v
\`\`\`

The suite covers no-interrupt fast-path completion, multiple logical interrupts, retries, unknown timeout outcomes, a cache/admission miss followed by fallback, halt followed by fallback, identical replay deduplication, conflicting duplicate event IDs, unavailable billing, counter mismatches, missing unknown-state reason codes, and orphan events.

## Validate captured CSV records

Export request-level and event-level rows using the columns in implementation-telemetry-template.csv and event-telemetry-template.csv, then run:

\`\`\`sh
python telemetry/validate_telemetry.py \\
  --requests path/to/requests.csv \\
  --events path/to/events.csv \\
  --report telemetry-validation-report.json
\`\`\`

Exit codes: 0 = contract pass, 1 = contract violations found, 2 = unreadable input or report output error. The JSON report includes errors and replay/conflict counts. Treat conflicts as excluded from aggregation; do not pick one payload arbitrarily. Unknown/unavailable provider outcomes and billed-token values are never coerced to zero.

## Aggregation semantics

- Request counters must reconcile with distinct event IDs after identical-replay deduplication.
- A conflicting payload for a reused event ID excludes every copy of that event ID from event aggregation and raises an error.
- Only CONFIRMED provider-response events contribute to confirmed-generation counts. Transport attempts and logical interrupts remain separate units.
- Unknown provider outcomes require a reason code. A timeout with no confirmed provider outcome must remain UNKNOWN / TIMEOUT_OUTCOME_UNKNOWN.
- full_oracle_fallback_avoided=TRUE is valid only for a known FAST_PATH terminal regime with zero full fallback operations.
- Unknown or unavailable billing must not be represented by a numeric zero.

A passing contract suite is not a measured result. Before interpreting real-world counters, the project still needs the actual runtime and transport-client implementation, provider-side evidence, and request-linked event logs.
