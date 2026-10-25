# SCRS recalculation-v1

This directory contains the corrected, reproducible numerical scenario supporting the revised SCRS manuscript.

- `recalculate_scrs_projection.py`: Monte Carlo latency scenario and exact analytical output-token calculations.
- `recalculated_table2.csv`: machine-readable outputs for all eight Table 2 configurations.
- `recalculation_manifest.json`: assumptions, regime probabilities, results, and evidence-status warnings.
- `recalculation_audit.md`: method, formulas, discrepancy log, and limitations.

## Reproduce

Run `python recalculate_scrs_projection.py` with Python 3 and NumPy. The seed is `20261025`; each configuration uses a deterministic derived seed and simulates 100,000 requests. The final code uses a shared request-load latent factor and independent residuals: queue/TTFT correlation 0.5, Oracle TPOT/request-load loading 0.5, and SLM TTFT/TPOT correlation 0.5. The initial recalculation attempt that accidentally forced perfect correlation was discarded.

## Evidence boundaries

- Regime probabilities and expected Oracle output-token means are exact calculations under stated assumptions.
- Latency percentiles are synthetic Monte Carlo outputs, not measurements.
- Input billed tokens and total costs are deliberately NR for rows 3–8 because the stable-prefix/uncached-suffix and route-specific billed-input assumptions are incomplete.
- One serial Oracle API round trip per logical Anchor event remains a scenario assumption; actual retries, batching, transport, and provider billing are unverified.
- Table 3 accuracy values remain design targets, not empirical results.
