# Symbolically-Compiled Reasoning Serving (SCRS)

## Purpose: publication-quality, reproducible research

This repository is a research-production workspace for making SCRS scientifically defensible and reproducible. Preserve source facts where supportable, distinguish analytical derivations from simulations and measurements, and never present inferred or synthetic results as empirical evidence.

The paper is not considered submission-ready until its claims, method, algorithm, experiments, statistics, figures, limitations, citations, and reproducibility materials have passed documented review.

## Current manuscript and evidence status

- **Numerical recalculation:** corrected, reproducible scenario and audit are available under `results/recalculation-v1/`.
- **Evidence status:** exact regime probabilities and Oracle-output token calculations are analytical under stated assumptions; P50/P95 values are synthetic Monte Carlo outputs, not deployment measurements.
- **Cost status:** total costs and savings percentages are only reported for the baseline and Tier I-only configurations. Rows 3–8 remain NR because route-specific billed Oracle input means and the stable-prefix/uncached-suffix split are not sufficiently specified.
- **Accuracy status:** Table 3 values remain design targets, not observed results.
- **Manuscript artifact:** the recalculated DOCX is supplied separately. The original manuscript file remains preserved and is not replaced by this text-only PR.

## Research workflow

Follow the staged workflow in [Research-to-publication workflow](docs/research-production-workflow.md): recover and inventory the manuscript; audit claims and equations; map claims to evidence; rewrite sections without inventing results; version data/code; independently regenerate outputs; and conduct journal-specific readiness review only after the evidence is stable.

## Contents

- `docs/section-5-cross-domain-safety.md` — conditional transfer-safety contract and validation protocol.
- `docs/decision-semantics-preservation.md` — task-relative sufficient-capsule definition, exact/approximate decision-risk propositions, proofs, and a validation protocol; analytical specification only.
- `docs/section-7-3-cost-latency.md` — corrected regime equations, output-token calculations, and cost/latency evidence boundaries.
- `docs/recalculation-audit.md` — numerical audit, including the resolved conditional/unconditional Anchor definition conflict.
- `docs/research-validation-ledger.md` — claim-to-evidence ledger.
- `docs/next-steps.md` — evidence-dependent work plan.
- `experiments/cross_domain_safety/` — abstract gate reference model and 26 conformance tests; not production error-rate evidence.
- `experiments/scrs_runtime/` — live OpenAI-compatible inference adapter, five-token Anchor client, capsule compiler, fail-closed decision graph, and paired LegalBench runner; a reference prototype, not production SCRS.
- `experiments/scrs_runtime/MOCK_TESTING.md` — zero-cost local mock API integration test. Synthetic outputs are marked as non-model evidence and accuracy metrics are suppressed.
- `telemetry/` — request/event schema, CSV templates, and offline contract validator (`telemetry/README.md`).
- `results/recalculation-v1/` — current recalculation model, CSV, manifest, and figure generator.
- `results/scenario-v2/` — historical scenario retained for provenance; it is not the current calculation.

## Evidence labels

- **Source-derived:** stated in the manuscript or a cited source.
- **Analytical:** follows from equations and declared assumptions.
- **Scenario / synthetic:** generated with a defined simulation; not production telemetry.
- **Measured:** requires a documented experiment with provenance, collection method, sample size, implementation version, and uncertainty procedure.
- **NR / unresolved:** the needed input values are not available; no value should be reverse-engineered from a legacy headline.

## Core probability model

For gated configurations, with `p_hit = 0.78` and `p_halt = 0.205` conditional on admission:

```text
P(R1) = p_hit * (1 - p_halt) = 0.6201
P(R2) = p_hit * p_halt       = 0.1599
P(R3) = 1 - p_hit            = 0.2200
Sum                            = 1.0000
```

A source inconsistency was resolved by defining `n_anchor` as calls per successful fast-path request, consistent with Equations (18)/(20), where the anchor-call term is multiplied by `alpha_eff`. The manuscript's Section 9.1 and Table 2 footnote were corrected to use this same definition.

## Remaining evidence gaps

1. **Runtime-source blocker:** no SCRS runtime or Anchor transport client is present in the main-branch source inventory. Obtain the implementation repository/path before inferring retry, batching, cancellation, provider-generation, or billing behaviour.
2. The offline telemetry contract validator has 17 passing reference tests; GitHub Actions run #1 passed on PR #7. This does not replace runtime instrumentation or provider evidence. See `telemetry/README.md`.
3. Reconcile provider-billed input/output tokens against actual request/event telemetry and provider-side billing exports.
4. Run the cross-domain gate contract against the real gate and measure end-to-end false-transfer rates on independently labelled test cases.
5. Obtain request-level traces and empirical baseline comparisons before reporting measured P50/P95 or production cost reductions.
6. Specify route-specific billed Oracle input tokens and the stable-prefix/uncached-suffix split before calculating total costs for rows 3–8.
7. Publish baseline and SCRS model predictions only after an execution path is available and the preregistered benchmark has been run.

## Status

The repository contains an executable abstract gate reference model, a corrected synthetic latency scenario, analytically derived token calculations, and a reproducibility plan. It does not contain verified production traces or end-to-end model predictions. Claims requiring those sources remain unverified.
