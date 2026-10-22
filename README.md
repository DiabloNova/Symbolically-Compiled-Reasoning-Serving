# Symbolically-Compiled Reasoning Serving (SCRS)

## Working research repository

**Manuscript status:** partial revision and analytical reconstruction in progress.  
**Evidence status:** latency figures in this repository are synthetic scenario outputs, not production measurements.  
**Source status:** the supplied `SCRS_Manuscript.docx` was not modified. Its archive reported a CRC error in `word/media/image1.png`; therefore this repository must not be treated as a complete replacement manuscript.

This repository separates revised passages, analytical assumptions, telemetry requirements, and synthetic scenario outputs. Results may be described as *measured* only when supported by trace/log provenance, collection method, sample size, and implementation version.

## Contents

- `docs/section-7-3-cost-latency.md` — execution regimes, expected usage, cost, and latency.
- `docs/section-8-3-algorithm.md` — revised execution pipeline and algorithmic caveats.
- `docs/section-8-4-telemetry.md` — telemetry requirements.
- `docs/section-9-4-sensitivity.md` — sensitivity interpretation.
- `docs/appendix-a-3.md` — derivation of expected usage and latency.
- `docs/anchor-telemetry-audit-prior.md` — source-level audit findings.
- `docs/research-validation-ledger.md` — claims and evidence ledger.
- `docs/next-steps.md` — ordered validation plan.
- `telemetry/` — request/event telemetry template and schema.
- `results/scenario-v2/` — reproducible synthetic simulation artifacts.

## Evidence labels

- **Source-derived:** text or values reported in the supplied manuscript.
- **Analytical:** derived from stated assumptions and equations.
- **Scenario / synthetic:** generated under declared assumptions; not production telemetry.
- **Measured:** requires implementation traces or a reproducible experiment and provenance.

## Core model

Let the successful fast-path probability be
\[
\alpha_{\mathrm{eff}}=p_{\mathrm{hit}}(1-p_{\mathrm{halt}}),
\]
where (p_{\mathrm{halt}}) is conditional on fast-path admission. The three regimes are successful fast path (R_1), bailout (R_2), and miss (R_3). The exact accounting and qualifications are documented in the section drafts.

## Critical open questions

1. Inspect the actual Anchor implementation and determine whether each logical interrupt produces a separate HTTP/API round trip, or whether retries, batching, caching, or internal transport changes that mapping.
2. Separate logical anchor events, API attempts, provider-billed generations, and returned anchor tokens.
3. Fix the Algorithm 1 counter issue: the supplied pseudocode initializes `n_int = 0` but does not increment it before using it to report `oracleCallsAvoided`.
4. Do not infer P50/P95 from expected-value equations. Percentiles require empirical traces or a fully specified and clearly labelled simulation.
5. Reconcile Table 2 and Figure 3, including the Unified SCRS output-token inconsistency, using declared assumptions or corrected evidence.

## Status

The repository currently contains working section drafts and a synthetic scenario. It does **not** contain a verified implementation audit or real production telemetry. Claims depending on those sources remain unverified.
