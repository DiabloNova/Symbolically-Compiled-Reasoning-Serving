# R1 replacement text — expected Oracle output and cost accounting

## Editorial boundary

This is a bounded replacement package for P0 / Finding 1 only. It addresses Equation (17), the directly dependent definitions and cost column for Table 2, the related cost interpretation in Sections 9.1–9.4, and Appendix A.3's reasoning-token derivation. It does not revise Equation (18), TTFT/P50/P95 values, accuracy targets, false-transfer claims, or other findings. Those items remain unvalidated/out of scope for R1.

## 1. Replacement for Section 7.3: expected Oracle output

> **Expected billable Oracle output.** Let \(p_{\mathrm{hit}}\) be the probability that a candidate passes the transfer gate, and let \(p_{\mathrm{halt}}=P(\mathrm{halt}\mid\mathrm{admitted})\) be the conditional probability that an admitted execution halts. Define three mutually exclusive regimes: completed fast path \(F\), admitted execution followed by bail-out \(B\), and retrieval/gate miss \(M\). Their probabilities are
>
> \[
> p_F=p_{\mathrm{hit}}(1-p_{\mathrm{halt}})=\alpha_{\mathrm{eff}},\qquad
> p_B=p_{\mathrm{hit}}p_{\mathrm{halt}},\qquad
> p_M=1-p_{\mathrm{hit}}.
> \]
>
> Let \(\mu_F\), \(\mu_B\), and \(\mu_M\) be the conditional mean **billable Oracle output tokens per request** in those regimes. The completed-fast-path mean \(\mu_F\) includes Anchor output billed by the Oracle and excludes text generated only by the local SLM. The bail-out mean \(\mu_B\) includes any Anchor output billed before the halt and all subsequent Oracle output, counting each token exactly once. The miss mean \(\mu_M\) includes all Oracle output billed on a miss. The expected Oracle output is then
>
> \[
> \boxed{
> E[N^{\mathrm{out}}_{\mathrm{Or}}]
> =\alpha_{\mathrm{eff}}\mu_F
> +p_{\mathrm{hit}}p_{\mathrm{halt}}\mu_B
> +(1-p_{\mathrm{hit}})\mu_M
> }\tag{17}
> \]
>
> Equation (17) is a regime-weighted expectation, not an assumption that the same output mean applies to every fallback request. Where only a single fallback mean is available, the restricted fallback-only component may be shown as \( (1-\alpha_{\mathrm{eff}})\bar N_{\mathrm{CoT}} \); it must not be labelled as total billable Oracle output if Anchor output is also billed. The corresponding expectation for billed Oracle input must include prompts for every Oracle call, including Anchor calls and retries, where applicable.
>
> This model reports projections, not measured outcomes. The numerical results below are reproducible only to the extent that the source supplies the conditional means and input-token aggregation needed by the equation.

**Editorial note (not manuscript text):** Keep Equation (18) and the latency paragraph unchanged in this R1 branch. They are not validated by this token-accounting correction and remain subject to separate audit findings.

## 2. Replacement for the cost-related paragraph in Section 9.1

> The workload contains 10,000 requests across the three stated domains, with the cross-domain and stale-evidence trap proportions specified above. The Table 2 token counts and effective fast-path probabilities are scenario inputs, not deployment measurements. For cost reconstruction, Oracle-billed input and output tokens are counted across all Oracle calls associated with a request; local-SLM generated tokens are accounted for through local serving cost rather than priced as Oracle output. Anchor output and the prompts sent with Anchor calls are part of the Oracle bill where they occur.
>
> The source does not provide enough conditional token means to reproduce every output-token value in Table 2. It also does not provide per-configuration amortised local-hosting allocations. Accordingly, this revision distinguishes (i) output components directly calculated from published assumptions, (ii) source values carried forward solely as reference inputs, and (iii) values that cannot be reproduced without additional assumptions. An explicit API-only price scenario is presented separately from all-in serving cost. API-only values exclude local hosting and any other charges not represented by the token counts; they are not estimates of total serving cost.

## 3. R1 replacement for the Table 2 token/cost accounting columns

The non-cost columns of the original Table 2 are deliberately not recalculated in R1. The following audit table should replace the ambiguous Out-tok/cost interpretation until the missing cost inputs are supplied.

| Configuration | Source Out-tok | R1 expected Oracle output / component (tokens/request) | API-only spend scenario per 10,000 requests (USD) | Reproduction status |
|---|---:|---:|---:|---|
| Baseline (raw RAG + full oracle) | 2,380 | 2,380 (carried-forward reference) | 366.40 | Reference only; total input aggregation not independently verified |
| Tier I only (capsules) | 2,310 | 2,310 (carried-forward reference) | 254.60 | Source output mean is not derived independently |
| Tier II only (hardened JIT) | 905 | 904.4 fallback-only component | 139.24 | \((1-0.62)\times2,380=904.4\); does not exactly reproduce 905 |
| Tier III only (entropy interrupt) | 480 | Not reproducible | Not reproducible | Conditional Anchor/output distribution is missing |
| Tier I + III (no JIT) | 360 | 48 Anchor-token subtotal | 28.40 subtotal only | \(9.6\times5=48\); source 360 needs an additional stated term or different denominator |
| Tier I + II (no entropy interrupt) | 878 | 877.8 fallback-only component | 96.74 | \((1-0.62)\times2,310=877.8\), which rounds to 878 |
| Naive unhardened JIT (no gate) | 690 | 523.6 fallback-only component | 59.96 subtotal only | \((1-0.78)\times2,380=523.6\); total requires any additional billed Oracle outputs |
| Unified SCRS (I + II + III) | 894 | 884.8 under primary interpretation; 882.14 if 1.4 is conditional on fast-path completion | 98.72 under primary interpretation; 98.454 under alternate | Neither token estimate reproduces 894; interpretation of the 1.4-anchor mean must be fixed |

**API-only scenario notes.** The cost values above use the Table 2 input counts as total billable Oracle input tokens and the explicit scenario price of USD 2 / 1M input tokens and USD 10 / 1M output tokens. No cached-input discount is applied. These values exclude hosting and are not validated all-in costs. For rows 4, 5, and 7, the API-only number is blank or a component subtotal rather than a complete cost because the total output is not reproducible. The CSV artifact preserves source costs and status fields separately.

**Column definition to use in Table 2:** “Out-tok” must mean *expected billable Oracle output tokens per request, including Anchor and fallback outputs, and excluding local-SLM output*. If the authors intend a different quantity, it must be renamed and separate billable-token counts must be provided for each model.

## 4. Replacement for the cost interpretation in Section 9.3

> The cost contribution of each tier must be read against the regime-specific Oracle-token model rather than a single hit-rate multiplier. Tier II-only and Tier I + II provide fallback-only components of 904.4 and 877.8 tokens/request under the stated shared-mean assumptions. For Unified SCRS, adding the reported 1.4 Anchor interrupts per request at five output tokens each gives 884.8 expected Oracle output tokens/request if 1.4 is an unconditional request-level mean. If 1.4 is conditional on a successfully completed fast path, the corresponding estimate is 882.14. The source does not resolve this denominator ambiguity, and neither interpretation yields the 894 tokens/request shown in the original table.
>
> The originally reported 78.4% reduction is derived from the source all-in cost column, whose per-configuration hosting allocation and other billing inputs are not supplied. It therefore cannot be presented as a reproduced total-serving-cost reduction. Under the separate token-price scenario, the baseline and Unified SCRS API-only amounts are USD 366.40 and USD 98.72 per 10,000 requests, respectively, implying a conditional 73.1% API-spend reduction. This is an illustrative scenario only: it assumes the published input-token counts include every billed Oracle input and excludes local hosting, so it is not a validated total-cost result.

## 5. Replacement for the cost-related portion of Section 9.4

> With complete regime-specific means, expected Oracle output cost is linear in the weighted conditional means \(p_F\mu_F+p_B\mu_B+p_M\mu_M\), and API spend is linear in expected billed input and output token counts for a fixed price schedule. Sensitivity analysis must therefore vary the fast-path, bail-out, and miss probabilities together with the corresponding conditional token means; varying only \(\alpha_{\mathrm{eff}}\) while assuming identical fallback output can hide differences between bail-out and miss traffic. Anchor output and Anchor-prompt input must be included in the applicable regimes. A total-serving-cost sensitivity analysis additionally requires a stated local-hosting allocation and charging assumptions. No new latency sensitivity or percentile claim is made in this R1 revision.

## 6. Replacement for the reasoning-token paragraph in Appendix A.3

> **Expected Oracle output tokens.** The three disjoint regimes have probabilities \(p_F=p_{\mathrm{hit}}(1-p_{\mathrm{halt}})\), \(p_B=p_{\mathrm{hit}}p_{\mathrm{halt}}\), and \(p_M=1-p_{\mathrm{hit}}\). Let \(\mu_F\), \(\mu_B\), and \(\mu_M\) denote the conditional mean billable Oracle output for a completed fast path, a bail-out, and a miss, respectively. The regime definitions include Anchor output in the regime where it is billed and count each output token only once. By the law of total expectation,
>
> \[
> E[N^{\mathrm{out}}_{\mathrm{Or}}]=p_F\mu_F+p_B\mu_B+p_M\mu_M.
> \]
>
> The simpler expression \((1-\alpha_{\mathrm{eff}})\bar N_{\mathrm{CoT}}\) is the fallback-only reasoning component under the additional assumption that both fallback regimes share the same conditional full-Oracle output mean. It is not the total Oracle-billed output when fast-path Anchor calls also produce billable tokens. The published Table 2 values must be recalculated from these regime definitions and explicit conditional means; where such inputs are unavailable, the corresponding output and cost must be reported as not reproducible rather than inferred.

## 7. Required follow-through before this cost result is publishable

1. Resolve the conditional meaning of the 1.4 Anchor-interrupt average, and define the conditional means for bail-out and miss.
2. Confirm that In-tok counts aggregate all Oracle input across normal calls, Anchor prompts, bail-outs, and retries.
3. Supply a per-configuration hosting allocation and its amortisation method, or change the table explicitly to API-only cost and remove the all-in cost claim.
4. Regenerate the final Table 2 cost column and Figure 3(a) from the same committed input file/script. Until the missing rows are resolved, Figure 3(a) must not visually imply that all eight all-in cost points are reproducible.
