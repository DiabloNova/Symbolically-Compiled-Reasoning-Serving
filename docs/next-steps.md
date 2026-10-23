# Next steps, ordered by evidence dependency

1. **Obtain source implementation:** provide the reference implementation repository/commit or source files for Anchor, interrupt handling, retries, batching, and fallback.
2. **Instrument transport semantics:** apply the Section 8.3 counter contract at the actual transport boundary; distinguish logical interrupts, attempts, provider-confirmed generations, and returned/billed tokens.
3. **Validate counter behavior:** test the cases specified in Section 8.3, including no interrupt, multiple interrupts, retries, unknown timeout outcomes, miss fallback, and halt followed by fallback.
4. **Instrument telemetry:** implement the request-level and event-level records in Section 8.4; redact sensitive content and preserve unknown values rather than coercing them to zero.
5. **Validate the equations:** test regime probabilities and expected token/cost formulas, retaining separate bailout and miss means when needed.
6. **Reconcile Table 2 / Figure 3:** recover exact data, price assumptions, and figure source; resolve the Unified SCRS output-token inconsistency.
7. **Re-run latency analysis:** use measured traces where available. Keep synthetic results clearly separated and report all simulation assumptions.
8. **Repair source manuscript copy:** obtain a valid DOCX before attempting a complete manuscript edit; preserve the original and record hashes.
9. **Update claims and limitations:** label each table/figure value as source-derived, analytical, synthetic, or measured.
