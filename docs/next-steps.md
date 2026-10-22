# Next steps, ordered by evidence dependency

1. **Obtain source implementation:** provide the reference implementation repository/commit or source files for Anchor, interrupt handling, retries, batching, and fallback.
2. **Audit transport semantics:** trace a logical interrupt through the call stack and determine how it maps to HTTP attempts and billed generations.
3. **Fix algorithm counters:** correct `n_int` and define every reported metric precisely.
4. **Instrument telemetry:** implement the request-level template plus event-level records; redact sensitive content.
5. **Validate the equations:** test regime probabilities and expected token/cost formulas, retaining separate bailout and miss means when needed.
6. **Reconcile Table 2 / Figure 3:** recover exact data, price assumptions, and figure source; resolve the Unified SCRS output-token inconsistency.
7. **Re-run latency analysis:** use measured traces where available. Keep synthetic results clearly separated and report all simulation assumptions.
8. **Repair source manuscript copy:** obtain a valid DOCX before attempting a complete manuscript edit; preserve the original and record hashes.
9. **Update claims and limitations:** label each table/figure value as source-derived, analytical, synthetic, or measured.
