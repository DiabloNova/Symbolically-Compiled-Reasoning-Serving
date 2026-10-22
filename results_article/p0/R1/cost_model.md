# R1 cost model — expected billable Oracle output and API spend

## Purpose and scope

This file replaces the under-specified expected-output calculation used for the R1 cost-accounting audit. It covers Oracle-billed output tokens and the token-priced component of cost. It does **not** validate or recalculate latency percentiles, quality/accuracy targets, false-transfer rates, or local-model hosting.

## 1. Mutually exclusive request regimes

Let:

- \(p_{\mathrm{hit}} = P(\text{candidate is admitted})\).
- \(p_{\mathrm{halt}} = P(\text{runtime halts}\mid\text{candidate admitted})\).
- \(p_F = p_{\mathrm{hit}}(1-p_{\mathrm{halt}})=\alpha_{\mathrm{eff}}\): admitted and completed fast path.
- \(p_B = p_{\mathrm{hit}}p_{\mathrm{halt}}\): admitted, then bailed out.
- \(p_M = 1-p_{\mathrm{hit}}\): miss; no candidate is admitted.

These are mutually exclusive and exhaustive:

\[
p_F+p_B+p_M
=p_{\mathrm{hit}}(1-p_{\mathrm{halt}})
+p_{\mathrm{hit}}p_{\mathrm{halt}}+(1-p_{\mathrm{hit}})=1.
\]

The conditional definition of \(p_{\mathrm{halt}}\) is intentional; it avoids introducing an independence assumption merely to compute \(p_F\).

## 2. Expected Oracle-billed output tokens

Define all conditional means as **billable Oracle output tokens per request in that regime**:

- \(\mu_F\): completed fast path, including all Anchor output tokens billed to the Oracle; exclude tokens generated only by the local SLM.
- \(\mu_B\): bail-out regime, including any Anchor tokens already billed before the halt and all subsequent Oracle output, counting each token once.
- \(\mu_M\): miss regime, including the Oracle output billed on a miss.

Then the general expected-output equation is:

\[
\boxed{
E[N^{\mathrm{out}}_{\mathrm{Or}}]
=p_F\mu_F+p_B\mu_B+p_M\mu_M
}
\]

Equivalently, after substituting the event probabilities:

\[
E[N^{\mathrm{out}}_{\mathrm{Or}}]
=\alpha_{\mathrm{eff}}\mu_F
+p_{\mathrm{hit}}p_{\mathrm{halt}}\mu_B
+(1-p_{\mathrm{hit}})\mu_M.
\]

This formulation does not force bail-out and miss requests to have the same mean Oracle output. It also makes the billed Anchor contribution explicit. The regime means must be defined so an Anchor token already counted in \(\mu_B\) is not added a second time.

A corresponding expected-input equation is required for complete API billing:

\[
E[N^{\mathrm{in}}_{\mathrm{Or}}]
=p_F\nu_F+p_B\nu_B+p_M\nu_M,
\]

where each \(\nu_r\) includes all billable prompt/input tokens for **all Oracle calls** in regime \(r\), including Anchor-call prompts and retries if those are part of the scenario. The current Table 2 does not establish whether the reported In-tok values use this denominator.

## 3. When the manuscript's simpler equation is valid

The original Equation (17),

\[
E[N_{\mathrm{Or}}]=(1-\alpha_{\mathrm{eff}})\bar N_{\mathrm{CoT}},
\]

is valid only for the narrower quantity “full Oracle reasoning output on fallback requests” when (a) the full-reasoning mean is the same for every fallback request, (b) the fast path incurs no Oracle output, or Anchor tokens are intentionally excluded from the metric, and (c) \(\bar N_{\mathrm{CoT}}\) is the correct conditional fallback mean. Those conditions do not, by themselves, define total billable Oracle output when Anchor calls also produce output.

For the table's all-Oracle-output metric, Equation (17) should therefore be replaced with the regime-weighted equation above. If the authors want to retain Equation (17) as a secondary fallback-only metric, it must be labelled as such and the expected Anchor output must be reported separately.

## 4. Checks against the currently published inputs

### Unified SCRS

The manuscript gives \(\alpha_{\mathrm{eff}}=0.62\), a capsule-path full-Oracle output mean of 2,310 tokens (Table 2, Tier I only), and 1.4 Anchor interrupts per answer with \(k=5\) tokens per interrupt (Section 9.3). Applying the simplified fallback assumption gives:

\[
(1-0.62)\times 2310=877.8.
\]

If 1.4 interrupts is an unconditional mean over all requests, the implied Anchor subtotal is \(1.4\times5=7\), and the combined estimate is:

\[
877.8+7=884.8\text{ tokens/request}.
\]

If 1.4 is conditional on a completed fast-path request, the Anchor contribution is \(0.62\times1.4\times5=4.34\), giving:

\[
877.8+4.34=882.14\text{ tokens/request}.
\]

Neither interpretation reproduces the published 894 tokens/request. The unconditional interpretation leaves 9.2 tokens/request unexplained; the conditional interpretation leaves 11.86 unexplained. The source does not supply a further term that closes either gap, so 894 must not be retained as a reproduced value without new evidence.

### Tier II only and Tier I + II

Using the raw-RAG fallback mean for Tier II only:

\[
(1-0.62)\times2380=904.4\text{ tokens/request},
\]

which is approximately 904 tokens, not an exact reproduction of the table's 905.

Using the capsule-path fallback mean for Tier I + II:

\[
(1-0.62)\times2310=877.8\text{ tokens/request},
\]

which rounds to the reported 878.

### Tier I + III

Section 9.3 reports 9.6 interrupts per answer and Section 6.2 gives \(k=5\) Anchor tokens. If 9.6 is the mean number of billable Anchor calls per request and each call returns exactly five billable output tokens, the Anchor output subtotal is:

\[
9.6\times5=48\text{ tokens/request}.
\]

This does not reproduce the Table 2 value of 360 as Oracle-billed output. The original Out-tok column does not say whether 360 includes local-SLM output; if it does, that metric must be split by model before costing. If other Oracle output is included, the source must state those terms. The 48-token value is an Anchor subtotal under the stated assumption, not proof that all other Oracle output is zero.

### Naive JIT

Using \(\alpha_{\mathrm{eff}}=0.78\) and the raw-RAG mean produces a fallback-only component of:

\[
(1-0.78)\times2380=523.6\text{ tokens/request}.
\]

This is not a total-output reproduction unless the model establishes that no additional Oracle output (including any Anchor calls) is billed. The published value 690 remains unreproduced from the stated inputs.

## 5. API-only cost equation

For one explicit token-price scenario, with \(c_{\mathrm{in}}\) and \(c_{\mathrm{out}}\) in USD per one million billed tokens:

\[
C_{\mathrm{API},10k}
=10{,}000\left(
\frac{c_{\mathrm{in}}E[N^{\mathrm{in}}_{\mathrm{Or}}]}{10^6}
+\frac{c_{\mathrm{out}}E[N^{\mathrm{out}}_{\mathrm{Or}}]}{10^6}
\right).
\]

This expression excludes local-SLM hosting, storage, network charges, and other non-token charges. Any tool-call charges, cache discounts/write charges, provider service tier, and retry billing must be included when applicable to the actual deployment.

The supplied reconstruction workbook specifies a scenario of USD 2 / 1M input tokens and USD 10 / 1M output tokens for standard gpt-6.1-sol, with no cached-input discount. The official pricing page lists those standard rates as of 2026-10-22: https://developers.openai.com/api/docs/pricing. This is an explicit scenario for comparison, not a claim that the original provider-agnostic manuscript used this model.

## 6. Limits on cost claims

- Table 2's source cost totals are not reproducible from the published inputs because the amortised local-hosting allocation is not stated per configuration.
- The scenario costs in table2_recalculation.csv and figure3_cost_data.csv use the source In-tok counts as if they were total expected billable Oracle input tokens. If they omit repeated Anchor prompts or retries, API spend is understated.
- Rows whose output totals cannot be derived are explicitly marked provisional or not reproducible; a carried-forward manuscript value is not treated as validation.
- Consequently, the published all-in cost and 78.4% total-cost reduction are not supported by the available cost inputs. The API-only scenario must not be presented as an all-in cost result.
