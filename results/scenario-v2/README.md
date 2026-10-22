# Scenario v2 — synthetic, not measured

This directory contains the current Monte Carlo simulation source and its generated outputs. It simulates 100,000 requests per configuration with seed `20261022`. All latency percentiles are **synthetic scenario outputs**, not production telemetry.

## Artifacts

- `SCRS_latency_scenario_v2.py` — simulation source.
- `results.csv` — regenerated summary table aligned with the script's output fields and the snapshot.
- `snapshot.json` — machine-readable assumptions and summary results.
- `SCRS_Latency_Scenario_v2_Snapshot.xlsx` — spreadsheet snapshot.
- `SCRS_Latency_Scenario_v2_P50_P95.png` — plot of synthetic P50/P95 values.
- `manifest.json` — artifact inventory and caveats.

## Critical caveats

The scenario assumes one serial Oracle API round trip per logical Anchor interrupt. The manuscript pseudocode contains one `Oracle.generateAnchors(...)` invocation per interrupt, but the actual implementation's HTTP request count, retries, batching, and caching have not been verified. The simulation uses explicit assumed latency distributions and a `p_hit` value that the manuscript does not specify.

Unified SCRS's simulated P50/P95 are about 8.84 s / 53.65 s under these assumptions. These numbers must not be presented as measured performance or as validation of the architecture. Reproduction requires Python plus `numpy`, `pandas`, `openpyxl`, and `matplotlib`.
