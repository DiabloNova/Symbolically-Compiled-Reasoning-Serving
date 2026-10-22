# R1 validation report

## Decision

**Status: partially addressed; acceptance criterion not yet met.**

The branch now contains a transparent expected-output model, a bounded manuscript replacement proposal, a machine-readable eight-configuration calculation, and a regeneration script. The audit finding is not marked resolved because several source values still cannot be independently reproduced from the manuscript's published assumptions. Missing inputs are exposed rather than invented.

## Scope control

The changes are confined to the results_article source-preservation and P0/R1 artifacts. No source manuscript file, latency percentile, accuracy target, cross-domain safety claim, or non-R1 audit finding has been rewritten. Figure 3(a) cost data is marked not publication-ready; Figure 3 latency data is out of scope.

## Source integrity and transcription

- The supplied 35-page PDF was used to make **results_article/original.md**. It retains the text, reported numeric values, equations, headings, captions, and unresolved inconsistencies. Running headers and page numbers were removed and wrapped lines were reflowed; figures themselves are represented by captions rather than embedded image files.
- The supplied DOCX contains a CRC error in **word/media/image1.png**, so the PDF was used as the transcription source. The user-supplied source files remain unchanged.
- The Finding 1 evidence in **exc_plan/details.md** and the workbook **SCRS_Table2_Figure3_Reconstruction.xlsx** informed the variable definitions and reported-value comparisons.

## Independent arithmetic checks

| Configuration / check | Result from stated assumptions | Source value | R1 conclusion |
|---|---:|---:|---|
| Tier II only | (1 - 0.62) × 2,380 = 904.4 fallback-only tokens/request | 905 | Not exact; 905 is not independently reproduced |
| Tier I + II | (1 - 0.62) × 2,310 = 877.8 fallback-only tokens/request | 878 | Consistent after rounding |
| Tier III only | No unique result from supplied interrupt/output inputs | 480 | Not reproducible; output and total scenario spend left blank |
| Tier I + III | 9.6 × 5 = 48 Anchor-output tokens/request under stated fixed-k assumption | 360 | Only a component is derived; 360 may mix local-SLM and Oracle output, and must be split by model before billing |
| Naive JIT | (1 - 0.78) × 2,380 = 523.6 fallback-only tokens/request | 690 | Additional output terms are not stated; total remains unreproduced |
| Unified SCRS, unconditional anchor mean | 0.38 × 2,310 + 1.4 × 5 = 884.8 tokens/request | 894 | Not reproduced |
| Unified SCRS, anchor mean conditional on completed fast path | 0.38 × 2,310 + 0.62 × 1.4 × 5 = 882.14 tokens/request | 894 | Not reproduced |

The arithmetic assumes the 2,310 and 2,380 full-Oracle output means are valid for the corresponding fallback paths. The manuscript does not establish those conditional distributions, so derived numbers above are labelled as conditional projections, not measured results.

## API-only cost scenario

The artifacts use the price schedule supplied in the reconstruction workbook: USD 2 per million input tokens and USD 10 per million output tokens, without a cached-input discount. The official pricing page checked for this scenario is https://developers.openai.com/api/docs/pricing (check date: 2026-10-22).

Assuming the Table 2 input-token counts already aggregate every billable Oracle input token, the API-only reference for baseline is USD 366.40 per 10,000 requests. Unified SCRS is USD 98.72 using 884.8 output tokens/request (USD 98.454 using the alternate 882.14 output interpretation). The primary scenario implies a 73.06% API-only spend reduction from that baseline. This is not all-in cost: local serving and hosting are excluded, prompt/retry completeness is unconfirmed, and source costs cannot be reproduced from a stated hosting allocation because none is supplied.

## Artifact structure and reproducibility checks

- **table2_recalculation.csv**: header plus eight configuration rows; 18 fields per row.
- **figure3_cost_data.csv**: header plus eight configuration rows; 11 fields per row. Each row is marked not ready for a publication-ready Figure 3(a) all-in comparison until its cost basis is complete.
- **recalculate_costs.py**: Python standard-library script intended to regenerate both CSVs from explicit source inputs and assert the core arithmetic.
- The regeneration logic was exercised in the working environment; output row counts and field widths were checked. A clean-checkout run should be included in final publication-artifact validation before journal submission.

To regenerate the files from the R1 directory:

```sh
python3 recalculate_costs.py
```

## Inputs required to close R1

1. Conditional Oracle output-token means for the completed fast path, bail-out, and miss, with Anchor tokens included exactly once where billed.
2. Explicit resolution of whether the 1.4 Anchor-interrupt average is unconditional per request or conditional on fast-path completion.
3. Confirmation that Table 2 In-tok totals include every Oracle call's prompt input, Anchor calls, and retries.
4. Separate per-model output token metrics where local-SLM output and Oracle-billed output are both represented.
5. The derivation of source Out-tok values 480, 360, 690 and 894.
6. Per-configuration local-hosting allocation and its amortisation method, or a clearly labelled change from all-in cost to API-only cost.

**R1 should not be marked fully resolved until the remaining values are derived from supplied evidence or unsupported source claims are explicitly removed/narrowed.** No work on Finding 2 should begin before the user reviews and approves this R1 package.
