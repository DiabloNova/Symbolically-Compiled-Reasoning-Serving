# Replacement draft — Section 7.3: Expected usage, cost, and latency (recalculation-v1)

Define three mutually exclusive execution regimes: successful fast-path completion (R1), bailout after partial local execution (R2), and admission miss (R3). Let `p_hit` be the probability of admission and `p_halt` the conditional probability of a halt after admission. Then:

```text
P(R1) = p_hit * (1 - p_halt)
P(R2) = p_hit * p_halt
P(R3) = 1 - p_hit
alpha_eff = P(R1)
```

With scenario assumptions `p_hit = 0.78` and `p_halt = 0.205`, these give `P(R1) = 0.6201`, `P(R2) = 0.1599`, and `P(R3) = 0.22`, which sum to one. These are assumptions, not measured hit/halt rates.

## Oracle-billed output tokens

The general expected output-token accounting follows the law of total expectation:

```text
E[N_oracle,out] =
  P(R1) * E[N_anchor,out | R1]
+ P(R2) * E[N_full,out   | R2]
+ P(R3) * E[N_full,out   | R3]
```

The simplified full-fallback component `(P(R2) + P(R3)) * N_CoT_mean` requires equal conditional fallback output means for bailout and miss. That equality is an explicit scenario assumption in recalculation-v1, not a measured property.

### Anchor-call definition

The source manuscript had an internal conflict: Section 7.3 and Equations (18)/(20) used `n_anchor` as the mean calls **conditional on fast-path completion**, while Section 9.1 and the original Table 2 footnote called it the unconditional per-request mean. This replacement selects the **conditional** definition because the equations explicitly multiply the Anchor terms by `alpha_eff`. Section 9.1 and the Table 2 footnote are updated to match.

With `n_anchor = 1.4` calls per successful fast-path request and `k = 5` tokens returned per call, unified SCRS has expected Anchor output across all requests of:

```text
alpha_eff * n_anchor * k = 0.6201 * 1.4 * 5 = 4.3407 tokens/request
```

Assuming the same 2,310-token full-Oracle output mean for bailout and miss requests:

```text
E[N_oracle,out] = (0.1599 + 0.22) * 2310 + 0.6201 * 1.4 * 5
                = 881.9097, approximately 881.9 tokens/request
```

For the similarity-only/no-gate ablation, with a hit probability of 0.78 and no modeled bailout regime:

```text
E[N_oracle,out] = 0.22 * 2310 + 0.78 * 1.4 * 5
                = 513.66, approximately 513.7 tokens/request
```

For Tier II with Oracle rendering on the successful path, the 900-token fast-path output is an explicit assumption. Using raw/capsule full-fallback means of 2,380/2,310 respectively:

```text
Raw-context Tier II:       0.6201 * 900 + 0.3799 * 2380 = 1462.252
Capsule-context Tier I+II:  0.6201 * 900 + 0.3799 * 2310 = 1435.659
Tier III-only raw output:  11.5 * 5 = 57.5 Anchor tokens/request
Tier I + III output:        9.6 * 5 = 48.0 Anchor tokens/request
```

The 900-token fast-path output and equal conditional fallback means are modeling assumptions. All must be sensitivity-tested against actual route-wise token logs.

## Costs currently reproducible

Under the declared tariffs of USD 2.50 per million input tokens and USD 10.00 per million output tokens, per 10,000 requests:

- Baseline: `6420 * 0.025 + 2380 * 0.10 = USD 398.50`.
- Tier I only: `1180 * 0.025 + 2310 * 0.10 = USD 260.50`, 34.6% lower than baseline.

Total costs and savings deltas for configurations 3–8 are marked NR. The manuscript provides total Anchor prompt lengths but not the stable-prefix/uncached-suffix token split needed to apply the provider's `beta = 0.10` cached-input factor. Route-specific billed Oracle input lengths are also incomplete for several rows. Reverse-engineering those missing inputs from legacy dollar values is not valid.

## Latency evidence

The recalculation-v1 script simulates 100,000 requests/configuration with seed `20261025`, lognormal marginal distributions, a shared request-load latent factor and independent residuals, latent-factor correlation/loading parameters of 0.5, and an assumed 0.30-second fixed service-TTFT floor. The first recalculation attempt imposed accidental perfect correlation and was discarded.

P50/P95 are synthetic scenario percentiles, not values derivable from expected-value equations and not measured production latency. The simulation assumes one serial Oracle round trip per logical Anchor call; the actual client path, retries, batching, cancellations, and provider billing remain unverified.