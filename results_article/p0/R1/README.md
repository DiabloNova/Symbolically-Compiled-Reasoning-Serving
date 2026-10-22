# P0 / R1 — Expected output-token and cost accounting

## Scope

This addresses only the expected Oracle output-token model and directly dependent Table 2 / Figure 3 cost calculations. It does not validate latency percentiles, accuracy values, cross-domain safety claims, or other audit findings.

## Confirmed inconsistency

The manuscript reports α_eff = 0.62 and Unified SCRS output = 894 tokens/request. If Equation (17) uses the 2,380-token raw-RAG mean, (1 − 0.62) × 2,380 = 904.4, before any positive anchor output.

Using the capsule-path full Oracle output mean of 2,310 and an unconditional mean of 1.4 anchor interrupts/request at 5 tokens/interrupt gives 0.38 × 2,310 + 1.4 × 5 = 884.8. If 1.4 is conditional on fast-path completion, the result is 0.38 × 2,310 + 0.62 × 1.4 × 5 = 882.14. Neither interpretation yields 894.

## Artifacts

- `rewritten_sections.md`: bounded replacement text for Equation (17), assumptions, Table 2 interpretation, and Appendix A.3.
- `cost_model.md`: variable definitions and reproducible expectation/cost equations.
- `table2_recalculation.csv`: eight configurations with source values separated from calculated values and unresolved values flagged.
- `figure3_cost_data.csv`: API-only cost scenario, excluding unpriced hosting; provisional rows labelled.
- `assumptions.md`: input provenance and unresolved evidence.

## Reproducibility boundary

The supplied workbook uses $2 / million input tokens and $10 / million output tokens as an explicit scenario. These are not claimed to be the uniquely correct tariff. Hosting, retries, cached-input treatment, anchor prompt billing, and some output derivations remain unresolved. The source all-in dollar column cannot be certified from the supplied assumptions.
