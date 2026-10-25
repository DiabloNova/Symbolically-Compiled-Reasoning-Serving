# SCRS Recalculation Audit — 2026-10-25

## Scope and evidence classes

This audit rechecks numerical inconsistencies in the October 2026 SCRS manuscript using the manuscript's stated equations, public repository artifacts, and a reproducible synthetic Monte Carlo scenario. The corrected DOCX is delivered separately; the original manuscript file remains preserved.

The results are separated into: (1) exact analytical calculations under declared assumptions, (2) synthetic Monte Carlo latency values, (3) non-reproducible quantities marked NR, and (4) unmeasured design targets. None of the simulation outputs is represented as deployment evidence.

## 1. Recalculated probabilities

The manuscript states that (p_{hit}=0.78) and (p_{halt}=0.205) is conditional on admission:

[
P(R_1)=0.78(1-0.205)=0.6201,quad
P(R_2)=0.78(0.205)=0.1599,quad
P(R_3)=1-0.78=0.22.
]

These sum to one. The legacy scenario-v2 code used (p_{hit}=0.72), (P(R_2)=0.10), and (P(R_3)=0.28), which conflicts with the probabilities specified in the manuscript. It is retained only as historical provenance and is not the current scenario.

## 2. Recalculated Oracle-billed output tokens

The 1.4 Anchor-call average is conditional on successful fast-path completion. With five output tokens per Anchor, the unified system's expected Anchor output across all requests is:

[
0.6201	imes 1.4	imes 5=4.3407.
]

Assuming the same full-Oracle output mean for bailout and miss requests—2,310 tokens in capsule-context configurations—the unified SCRS expectation is:

[
(0.1599+0.22)	imes 2310+0.6201	imes1.4	imes5
=881.9097approx881.9.
]

For the similarity-only/no-gate ablation:

[
0.22	imes2310+0.78	imes1.4	imes5=513.66approx513.7.
]

For Tier II with Oracle rendering, the 900-token fast-path output is an explicit assumption, not a measurement:

[
0.6201	imes900+0.3799	imes2380=1462.252
]
for raw-context Tier II, and
[
0.6201	imes900+0.3799	imes2310=1435.659
]
for capsule-context Tier I+II. Tier III-only outputs are (11.5	imes5=57.5) tokens for raw context and (9.6	imes5=48.0) for Tier I+III. The equal conditional bailout/miss output means are model assumptions and must be sensitivity-tested.

## 3. Token-based costs that can be calculated

Using the declared tariffs—USD 2.50 per million input tokens and USD 10.00 per million output tokens—for 10,000 requests:

- Baseline: (6420	imes0.025+2380	imes0.10=$398.50).
- Tier I only: (1180	imes0.025+2310	imes0.10=$260.50), a 34.6% reduction.

Costs and cost deltas for rows 3–8 are NR rather than guessed. The manuscript states the total Anchor prompt length but not the count of stable-prefix tokens versus uncached-suffix tokens, and route-specific billed input lengths are missing. Reverse-engineering the terms from legacy total costs would be circular.

## 4. Current synthetic latency scenario

The current script uses seed `20261025`, 100,000 simulated requests/configuration, declared lognormal marginals, and a shared request-load latent factor plus independent residuals. The declared dependence settings are queue/TTFT correlation 0.5, Oracle TPOT/request-load loading 0.5, and SLM TTFT/TPOT correlation 0.5. The service-TTFT input-length scaling with a 0.30-second floor is an explicit sensitivity assumption. Each Anchor event is modelled as one serial API round trip; actual retry/batching/client behavior remains unverified.

| Configuration | Oracle output tokens/req | P50 E2E (s) | P95 E2E (s) | P50 TTFT (s) | Cost per 10,000 |
|---|---:|---:|---:|---:|---:|
| Baseline | 2,380.0 | 43.81 | 60.82 | 1.44 | USD 398.50 |
| Tier I only | 2,310.0 | 41.77 | 58.18 | 0.59 | USD 260.50 |
| Tier II only, Oracle-rendered | 1,462.3 | 20.71 | 54.85 | 1.45 | NR |
| Tier III only, raw context | 57.5 | 22.84 | 36.21 | 0.04 | NR |
| Tier I + III, no JIT | 48.0 | 11.54 | 17.46 | 0.04 | NR |
| Tier I + II, no entropy interrupts | 1,435.7 | 19.79 | 52.26 | 0.60 | NR |
| SCRS without transfer gate | 513.7 | 6.19 | 48.54 | 0.05 | NR |
| Unified SCRS | 881.9 | 7.13 | 53.21 | 0.06 | NR |

The initial recalculation attempt accidentally imposed perfect rank correlation across queue, TTFT, and TPOT and was discarded. The table above was regenerated from the corrected correlation model. All latency percentiles remain synthetic outputs, not measured values.

## 5. Revisions made

1. Corrected the probability split to 0.6201 / 0.1599 / 0.22.
2. Defined the 1.4 Anchor-call mean as conditional on successful fast-path completion; the unconditional expected count is 0.86814/request for unified SCRS.
3. Replaced the former unified and no-gate Oracle-output values of 631 and 369 with 881.9 and 513.7, respectively, under the declared output assumptions.
4. Recalculated all eight P50/P95 and P50-TTFT values using the final seeded Monte Carlo model.
5. Withheld unsupported total-cost values and savings percentages for rows 3–8.
6. Renamed the table column to “No full fallback (%)” to avoid applying the formal (alpha_{eff}) notation to no-JIT ablations.
7. Preserved Table 3 accuracy numbers as hypotheses only.

## 6. Limitations / next evidence

Actual production Anchor transport, retries, batching, provider billing, path-specific billed input token counts, and runtime latency traces remain unavailable. Accuracy targets and the end-to-end cross-domain transfer error rate remain unmeasured. An exact derivation under stated assumptions does not establish that those assumptions describe a deployed system.
