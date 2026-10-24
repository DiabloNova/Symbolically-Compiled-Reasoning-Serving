# Next steps, ordered by evidence dependency

1. **Obtain source implementation:** provide the reference implementation repository/commit or source files for Anchor, interrupt handling, retries, batching, and fallback.
2. **Instrument both counter boundaries:** apply the Section 8.3 counter contract at the correct boundary for each counter. The **runtime-event boundary** (inside the local runtime) owns `anchor_interrupt_count` and `full_oracle_fallback_count`; the **transport boundary** (inside the instrumented API client) owns `anchor_transport_attempt_count`, the tri-state `anchor_provider_generation_count`/`anchor_provider_generation_evidence`, `anchor_tokens_returned`/`anchor_tokens_billed`, and the full-Oracle attempt/generation counters. Runtime-event counters must never be incremented at the transport layer, and attempt counts must never be derived from logical events; only attempt counts belong at the transport boundary in the sense that every increment corresponds to an actual HTTP/API issuance or provider-evidence reconciliation.
3. **Validate counter behavior:** test the cases specified in Section 8.3, including no interrupt, multiple interrupts, retries, unknown timeout outcomes, miss fallback, and halt followed by fallback.
4. **Instrument telemetry:** implement the request-level and event-level records in Section 8.4; redact sensitive content and preserve unknown values rather than coercing them to zero.
5. **Validate the equations:** test regime probabilities and expected token/cost formulas, retaining separate bailout and miss means when needed.
6. **Reconcile Table 2 / Figure 3:** recover exact data, price assumptions, and figure source; resolve the Unified SCRS output-token inconsistency.
7. **Re-run latency analysis:** use measured traces where available. Keep synthetic results clearly separated and report all simulation assumptions.
8. **Repair source manuscript copy:** obtain a valid DOCX before attempting a complete manuscript edit; preserve the original and record hashes.
9. **Update claims and limitations:** label each table/figure value as source-derived, analytical, synthetic, or measured.
