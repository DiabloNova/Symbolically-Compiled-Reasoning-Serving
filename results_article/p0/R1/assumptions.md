# R1 assumptions, provenance, and unresolved inputs

## Source evidence inspected

- Article source: supplied 35-page `SCRS_Manuscript.pdf`, extracted to text and visually checked at the Table 2 page. The PDF is intact and readable. The supplied DOCX archive has a CRC failure in one media asset, so the PDF is the canonical transcription source for this R1 work.
- Audit report: `exc_plan/details.md`, Finding 1 (P0), “Numerical inconsistency in the cost model and expected Oracle output.”
- Reconstruction workbook: `SCRS_Table2_Figure3_Reconstruction.xlsx`, inspected through the workbook API. Sheets: Start Here, Inputs, Recalculation, and Latency Audit. The workbook explicitly describes itself as a calculation/audit workbook and flags several copied source numbers as unreproduced.
- Current branch source: Table 2 / Sections 7.3, 9.1–9.4, and Appendix A.3 from the PDF.

## Published values used for the audit

| Parameter | Value | Manuscript location | Status |
|---|---:|---|---|
| Baseline raw-RAG Oracle input | 6,420 tokens/request | Table 2 | Source projection; input aggregation across calls is not defined |
| Baseline Oracle output | 2,380 tokens/request | Table 2 | Source projection |
| Capsule-path Oracle input | 1,180 tokens/request | Table 2 | Source projection; not derived from the stated \(\rho=0.85\) |
| Capsule-path full-Oracle output | 2,310 tokens/request | Table 2, Tier I only | Source projection reused for the capsule fallback calculation |
| Effective fast-path probability, gated Tier II | 0.62 | §§7.3, 9.1 | Assumed projection, not measured |
| Effective fast-path probability, naive JIT | 0.78 | Table 2, row 7 | Assumed projection, not measured |
| Mean anchor interrupts, Tier I + III | 9.6/request | §9.3 | Reported mean; denominator and billable call aggregation should be explicit |
| Mean anchor interrupts, Unified SCRS | 1.4/request | §9.3 | Ambiguous: unconditional per request or conditional on a successful fast path |
| Anchor maximum length | \(k=5\) tokens | §6.2 and Table 1 | Source configuration; exact billable output per call is not stated as a measured mean |
| Unified SCRS Oracle output | 894 tokens/request | Table 2, row 8 | Not reproducible from the stated inputs |
| Tier I + III Oracle output | 360 tokens/request | Table 2, row 5 | Not reproduced as Oracle-billed output by 9.6 × 5 = 48 Anchor tokens/request; the source column does not clarify whether 360 includes local-SLM output |
| Naive JIT Oracle output | 690 tokens/request | Table 2, row 7 | Not reproduced by the fallback-only calculation 0.22 × 2,380 = 523.6 |

## Explicit API pricing scenario

The reconstruction workbook uses the standard gpt-6.1-sol price scenario:

- Input: USD 2.00 / 1,000,000 tokens.
- Output: USD 10.00 / 1,000,000 tokens.
- Cached-input discount: not applied.
- Usage: 10,000 requests per scenario cost total.
- Source URL: https://developers.openai.com/api/docs/pricing
- Retrieval/check date: 2026-10-22.

The official pricing page lists these standard rates on the checked date. However, the manuscript itself deliberately describes a provider-agnostic “frontier-class API model.” The pricing scenario is therefore a transparent comparative assumption for the reconstruction workbook, not evidence about the original manuscript's hidden price inputs or actual deployment.

## Assumptions used only to calculate the API-only scenario

1. Table 2's In-tok count is treated as mean total billed Oracle input tokens per request. This must be verified; if anchor prompts or retries are omitted, the reconstructed API-input cost is understated.
2. Table 2's fallback full-Oracle output mean is carried forward as 2,380 tokens for raw-RAG paths and 2,310 tokens for capsule paths, solely to expose the implications of the published model.
3. Where used, the simplified fallback-only formula is \((1-\alpha_{\mathrm{eff}})\bar N_{\mathrm{CoT}}\). It is not treated as the general expected total when Oracle Anchor output is also billed.
4. For Unified SCRS, the primary arithmetic scenario treats 1.4 as an unconditional mean number of Anchor interrupts per request and each interrupt as exactly five billable output tokens. This gives 884.8 tokens/request. The alternate conditional interpretation gives 882.14. Neither equals 894.
5. For Tier I + III, 9.6 × 5 = 48 is treated only as the Anchor output subtotal. It is not silently substituted for a total output metric if additional Oracle output exists.
6. For the naive JIT row, 523.6 is the fallback-only component; it is not asserted as total Oracle output without evidence that no other Oracle output is billed.
7. Hosting allocation is deliberately left at zero only in the calculation column for API-only spend. This is a bookkeeping convention, not an assertion that the local SLM is free.

## Inputs still required for a publishable all-in Table 2

- \(p_{\mathrm{hit}}\) and \(p_{\mathrm{halt}}\) separately, or the mutually exclusive measured/projection probabilities for fast completion, bail-out, and miss.
- Conditional mean Oracle output tokens for completed fast-path Anchor calls, bail-out requests, and miss requests, without double counting tokens.
- Definition of whether Table 2 Out-tok counts Oracle-billed outputs only, all model outputs, or full reasoning plus final answer across both model classes.
- Conditional Anchor count distribution and mean billable output tokens per Anchor call; mean prompt/input tokens for each Anchor call.
- Whether In-tok counts the sum of input tokens across all Oracle calls in a request, including retries, bail-outs, and Anchor prompts.
- Per-configuration local-SLM hosting amortisation (or underlying GPU/hour, utilisation, serving throughput, and allocation method).
- Explicit treatment of cache reads/writes, retry billing, tool-call charges, provider service tier, and any extra API charges.
- The derivation for the Tier III-only output 480, Tier I + III output 360, naive-JIT output 690, and Unified output 894.
- A row-by-row cost workbook or script whose inputs match the published Table 2 and which can regenerate both the table and Figure 3.

## Boundary of this R1 work

No attempt is made here to infer missing inputs from accuracy, TTFT, P50/P95, false-transfer exposure, or qualitative statements. Those quantities are not substitutes for the required token and cost accounting. Latency percentiles and cross-domain safety claims remain out of scope.
