# Symbolically-Compiled Reasoning Serving (SCRS)

## Purpose: publication-quality, reproducible research

This repository is a research-production workspace for making SCRS scientifically defensible and reproducible. Preserve source facts where supportable, distinguish analytical derivations from simulations and measurements, and never present inferred or synthetic results as empirical evidence.

The paper is not considered submission-ready until its claims, method, algorithm, experiments, statistics, figures, limitations, citations, and reproducibility materials have passed documented review.

## Current manuscript and evidence status

- **Numerical recalculation:** a corrected, seeded scenario and audit are available under `results/recalculation-v1/`.
- **Evidence status:** exact regime probabilities and output-token calculations are analytical under stated assumptions; P50/P95 values are synthetic Monte Carlo outputs, not deployment measurements.
- **Cost status:** total costs and savings percentages are only reported for the baseline and Tier I-only configurations. Rows 3–8 remain NR because route-specific billed Oracle input means and the stable-prefix/uncached-suffix split are not sufficiently specified.
- **Accuracy status:** Table 3 values remain design targets, not observed results.
- **Manuscript artifact:** a recalculated DOCX was produced from a clean manuscript copy and is supplied separately with the research artifacts. The older binary at `manuscripts/SCRS_Manuscript.docx` remains a historical repository copy and has not been replaced by this text-artifact PR.

## Research workflow

Follow the staged workflow in [Research-to-publication workflow](docs/research-production-workflow.md): recover and inventory the manuscript; audit claims and equations; map claims to evidence; rewrite sections without inventing results; version data/code; independently regenerate outputs; and conduct journal-specific readiness review only after the evidence is stable.

## Contents

- `docs/section-5-cross-domain-safety.md` — conditional transfer-safety contract and validation protocol.
- `docs/section-7-3-cost-latency.md` — corrected regime equations, output-token calculations, and cost/latency evidence boundaries.
- `docs/recalculation-audit.md` — discrepancy log and numerical audit.
- `docs/section-8-3-algorithm.md`, `docs/section-8-4-telemetry.md` — algorithm and telemetry requirements.
- `docs/research-validation-ledger.md` — claim-to-evidence ledger.
- `docs/next-steps.md` — evidence-dependent work plan.
- `experiments/cross_domain_safety/` — abstract gate reference model and 26 conformance tests; not production error-rate evidence.
- `telemetry/` — request/event telemetry schema and templates.
- `results/recalculation-v1/` — current recalculation model, CSV, manifest, and audit.
- `results/scenario-v2/` — historical scenario retained for provenance; it is not the current calculation.

## Evidence labels

- **Source-derived:** stated in the manuscript or a cited source.
- **Analytical:** follows from equations and declared assumptions.
- **Scenario / synthetic:** generated with a defined simulation; not production telemetry.
- **Measured:** requires a documented experiment with provenance, collection method, sample size, implementation version, and uncertainty procedure.
- **NR / unresolved:** the needed input values are not available; no value should be reverse-engineered from a legacy headline.

## Core probability model

For gated configurations, with (p_{hit}=0.78) and (p_{halt}=0.205) conditional on admission:

[
P(R_1)=p_{hit}(1-p_{halt})=0.6201,quad
P(R_2)=p_{hit}p_{halt}=0.1599,quad
P(R_3)=1-p_{hit}=0.22.
]

These probabilities sum to one. The current output-token calculations and synthetic latency outputs are documented in the recalculation manifest and CSV.

## Remaining evidence gaps

1. Inspect the actual Anchor implementation; establish retries, batching, and true HTTP/provider call counts.
2. Reconcile provider-billed input/output tokens against request/event telemetry.
3. Run the conformance contract against the real gate and measure end-to-end false-transfer rates on independently labelled test cases.
4. Obtain request-level traces and empirical baseline comparisons before reporting measured P50/P95 or production cost reductions.
5. Specify route-specific Oracle input tokens and the cached-prefix/uncached-suffix split before calculating total costs for rows 3–8.
6. Publish baseline and SCRS model predictions only after the preregistered benchmark runner and SCRS execution path are available.

## Status

The repository contains an executable abstract gate reference model, a corrected synthetic latency scenario, analytically derived token calculations, and a reproducibility plan. It does not contain verified production traces or end-to-end model predictions. Claims requiring those sources remain unverified.
