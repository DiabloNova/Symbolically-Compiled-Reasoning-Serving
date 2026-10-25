# SCRS Recalculation Audit — 2026-10-25

## Scope and evidence status

This audit rechecks the numerical inconsistencies in the October 2026 SCRS manuscript against its stated equations, the public repository artifacts, and a reproducible synthetic Monte Carlo scenario. The revised DOCX is supplied separately; the original manuscript is preserved unchanged.

The results are separated into: (1) exact analytical calculations under declared assumptions, (2) synthetic Monte Carlo latency values, (3) non-reproducible quantities marked NR, and (4) unmeasured design targets. No simulation output is represented as deployment evidence.

## 1. Methodology recheck

### 1.1 Regime probabilities

The manuscript states that `p_hit = 0.78` and `p_halt = 0.205` conditional on admission. Therefore:

```text
P(R1) = p_hit * (1 - p_halt) = 0.78 * (1 - 0.205) = 0.6201
P(R2) = p_hit * p_halt       = 0.78 * 0.205       = 0.1599
P(R3) = 1 - p_hit                                  = 0.2200
sum                                                  = 1.0000
```

The historical `scenario-v2` code used `p_hit = 0.72`, `P(R2) = 0.10`, and `P(R3) = 0.28`; this conflicts with the manuscript's own stated assumptions and is superseded.

### 1.2 Resolving the Anchor-call definition conflict

The source manuscript contains a direct definition conflict: Section 7.3 and Equations (18)/(20) define `n_anchor` as the number of Anchor calls conditional on successful fast-path completion, because the terms are multiplied by `alpha_eff`. However, Section 9.1 and the original Table 2 footnote described the same value as an unconditional per-request mean.

The recalculated manuscript adopts the **conditional definition** because it is the definition consistent with the cost/latency equations. Sections 9.1 and the Table 2 footnote are corrected to match it. With `n_anchor = 1.4` per successful fast-path request and `k = 5` output tokens per call, the expected Anchor-call count across all requests is `0.6201 * 1.4 = 0.86814`, and the expected Anchor output across all requests is `0.6201 * 1.4 * 5 = 4.3407` tokens. Retaining the unconditional interpretation would produce 7 Anchor output tokens/request and would require changing Equations (18)/(20) as well; mixing the two conventions is invalid.

### 1.3 Expected Oracle-billed output tokens

Use the law of total expectation by mutually exclusive regime:

```text
E[N_oracle,out] =
  P(R1) * E[N_anchor,out | R1]
+ P(R2) * E[N_full,out   | R2]
+ P(R3) * E[N_full,out   | R3]
```

For the unified configuration, the scenario assumes the same 2,310-token full-Oracle output mean for bailout and miss requests, and uses `n_anchor = 1.4` conditionally on R1:

```text
(0.1599 + 0.22) * 2310 + 0.6201 * 1.4 * 5
= 881.9097, approximately 881.9 tokens/request.
```

This replaces the inconsistent legacy value 631. For the similarity-only/no-gate ablation (hit probability 0.78; no bailout regime in that ablation):

```text
0.22 * 2310 + 0.78 * 1.4 * 5
= 513.66, approximately 513.7 tokens/request.
```

This replaces the inconsistent legacy value 369. For Tier II with Oracle rendering, the successful-path output length of 900 tokens is an explicit scenario assumption:

```text
Raw-context Tier II:      0.6201 * 900 + 0.3799 * 2380 = 1462.252
Capsule-context Tier I+II: 0.6201 * 900 + 0.3799 * 2310 = 1435.659
Tier III-only, raw:        11.5 * 5 = 57.5 Anchor tokens/request
Tier I + III:               9.6 * 5 = 48.0 Anchor tokens/request
```

The equal conditional bailout/miss means and the 900-token successful-path Oracle output are model assumptions, not measurements, and should be sensitivity-tested.

### 1.4 Token-based costs that remain reproducible

At USD 2.50 per million input tokens and USD 10.00 per million output tokens, for 10,000 requests:

- Baseline: `6420 * 0.025 + 2380 * 0.10 = USD 398.50`.
- Tier I only: `1180 * 0.025 + 2310 * 0.10 = USD 260.50`, a 34.6% reduction under these stated token-price assumptions.

Costs and cost deltas for rows 3–8 are **NR**, not guessed. The source provides total Anchor prompt lengths but omits the stable-prefix/uncached-suffix split needed to apply the provider's beta=0.10 cached-input factor correctly; some route-specific billed Oracle input means are also not specified. Reverse-engineering missing inputs from legacy total costs would be circular.

## 2. Recalculated synthetic latency scenario

The scenario simulates 100,000 requests per configuration with seed `20261025`. It uses lognormal marginals; a shared request-load latent factor plus independent residuals; a 0.5 latent-factor correlation/loading for queue/TTFT, Oracle TPOT/request-load, and local SLM TTFT/TPOT; an explicit 0.30-second fixed service-TTFT floor; and one serial Oracle round trip per logical Anchor interrupt.

The initial recalculation attempt accidentally imposed perfect rank correlation across several marginals and was discarded. The current outputs are regenerated with the corrected correlation construction. Percentiles remain **synthetic scenario values**, not measured latency.

| Configuration | Oracle output tokens/request (analytical) | P50 E2E seconds (synthetic) | P95 E2E seconds (synthetic) | P50 TTFT seconds (synthetic) | Total cost per 10,000 |
|---|---:|---:|---:|---:|---:|
| Baseline (raw RAG + full Oracle) | 2,380.0 | 43.80 | 60.82 | 1.44 | USD 398.50 |
| Tier I only (capsules) | 2,310.0 | 41.77 | 58.18 | 0.59 | USD 260.50 |
| Tier II only (hardened JIT, Oracle-rendered) | 1,462.3 | 20.71 | 54.85 | 1.45 | NR |
| Tier III only (entropy interrupt, raw context) | 57.5 | 22.84 | 36.21 | 0.04 | NR |
| Tier I + III (no JIT) | 48.0 | 11.54 | 17.46 | 0.04 | NR |
| Tier I + II (no entropy interrupt) | 1,435.7 | 19.79 | 52.26 | 0.60 | NR |
| SCRS without transfer gate (similarity-only) | 513.7 | 6.19 | 48.54 | 0.05 | NR |
| Unified SCRS (I + II + III) | 881.9 | 7.13 | 53.21 | 0.06 | NR |

## 3. Discrepancies resolved in the revised manuscript

1. Corrected the stale regime split `0.62 / 0.10 / 0.28` to `0.6201 / 0.1599 / 0.22`.
2. Resolved the conditional-versus-unconditional Anchor-call definition conflict by aligning Section 9.1 and Table 2's note to Equations (18)/(20).
3. Replaced the unified output-token value `631` with `881.9`, and the no-gate value `369` with `513.7`, under the explicit route/output assumptions.
4. Recalculated the output-token means for rows 3–6 and the synthetic latency percentiles for all eight configurations.
5. Removed unsupported savings claims for configurations 3–8, including the former 69.9%/78.3% savings and USD 33 gate-cost claims, because input-token billing assumptions do not uniquely determine total cost.
6. Renamed Table 2's `alpha_eff`-style column to **No full fallback (%)** so it is not incorrectly applied to configurations without the JIT fallback regime.
7. Kept Table 3 accuracy values explicitly labelled as design hypotheses. The abstract gate reference model's 26 conformance tests do not measure the production system's end-to-end cross-domain error rate.

## 4. Limitations and required evidence

- The latency input distributions are declared assumptions; no production traces were available to fit or validate them.
- One serial API round trip per logical Anchor event is a simulation assumption. Actual transport retries, batching, cancellations, provider generations, and billed-token totals remain unverified.
- Total cost for rows 3–8 remains NR until route-specific billed input means and the stable-prefix/uncached-suffix split are specified.
- Quality targets and cross-domain error rates remain unmeasured.
- The corrected projections do not validate the complete SCRS architecture or establish journal readiness.

## 5. Reproduction

From `results/recalculation-v1/`, run:

```bash
python recalculate_scrs_projection.py
python plot_recalculated_figure.py
```

The first command regenerates the CSV and JSON manifest; the second regenerates Figure 3. The revised DOCX is provided as a separate download.