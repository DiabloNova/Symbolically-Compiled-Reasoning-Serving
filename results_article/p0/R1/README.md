# P0 / R1 — Expected Oracle output-token and cost accounting

## Disposition

**The published Table 2 output/cost values are not all reproducible from the supplied manuscript and workbook inputs.** The R1 artifacts separate calculated components from carried-forward source values and missing inputs rather than guessing a single replacement for each unsupported number.

## Confirmed arithmetic

- Tier II only: `(1 - 0.62) × 2,380 = 904.4` fallback-output tokens/request, not exactly the reported 905.
- Tier I + II: `(1 - 0.62) × 2,310 = 877.8`, consistent with 878 after rounding.
- Tier I + III: `9.6 interrupts/request × 5 tokens/interrupt = 48` billable Anchor output tokens/request. It does not explain the source's 360 as Oracle output; the source column may mix Oracle and local-SLM tokens and must be split by model before costing.
- Naive JIT: `(1 - 0.78) × 2,380 = 523.6` is only a fallback-output component; the reported 690 is unreproduced unless other Oracle outputs are specified.
- Unified SCRS: `(1 - 0.62) × 2,310 + 1.4 × 5 = 884.8` if 1.4 is an unconditional request-level mean. If 1.4 is conditional on the completed fast path, the result is `877.8 + 0.62 × 1.4 × 5 = 882.14`. Neither gives the reported 894.

## Files in this finding

- [`cost_model.md`](cost_model.md) — regime definitions, expected-output equation, API-cost equation, and worked arithmetic.
- [`assumptions.md`](assumptions.md) — source provenance, all published inputs used, pricing-scenario source, and missing data required for a publishable cost table.
- [`rewritten_sections.md`](rewritten_sections.md) — proposed replacement text for the cost-related parts of §7.3, §§9.1–9.4, Table 2 interpretation, and Appendix A.3.
- [`table2_recalculation.csv`](table2_recalculation.csv) — all eight configurations, original and recalculated output values, API-only spend scenarios, and unresolved statuses.
- [`figure3_cost_data.csv`](figure3_cost_data.csv) — cost-panel reconstruction data with publication-readiness flags.
- [`recalculate_costs.py`](recalculate_costs.py) — standard-library-only script that regenerates both CSV files and asserts key R1 arithmetic.
- [`validation_report.md`](validation_report.md) — scope, arithmetic checks, artifact QA, unresolved inputs, and R1 disposition.

## Reproducing the audit CSVs

From this directory in a clean checkout, run:

```sh
python3 recalculate_costs.py
```

The script regenerates `table2_recalculation.csv` and `figure3_cost_data.csv`. It keeps unsupported output totals blank and labels component-only values rather than silently promoting them to full totals.

## API-only price scenario

The reconstruction workbook's standard gpt-6.1-sol scenario uses USD 2 per million input tokens and USD 10 per million output tokens, with no cached-input discount. Those rates are listed on the [official pricing page](https://developers.openai.com/api/docs/pricing) checked on 2026-10-22. The source manuscript itself is provider-agnostic. The scenario totals assume Table 2 input-token counts include every billed Oracle prompt, including Anchor prompts; that assumption still needs confirmation.

Under that explicit scenario, the baseline reference is USD 366.40 per 10,000 requests and the Unified SCRS scenario is USD 98.72 using 884.8 output tokens/request. The arithmetic implies a conditional 73.1% API-only spend reduction. This is **not** a validated total-serving-cost reduction: hosting is unpriced, some token inputs/outputs are unverified, and the API-input aggregation assumption remains open. The source's 78.4% all-in reduction cannot be reproduced from the published cost inputs.

## Scope and limitations

R1 does not change or validate TTFT/P50/P95, accuracy, false-transfer exposure, or other audit findings. The latency panel of Figure 3 is not recalculated here. Figure 3(a) must not be presented as a publication-ready eight-point all-in cost chart until missing token means and per-configuration hosting costs are supplied. The branch remains unmerged; subsequent findings should not start until R1 is reviewed and approved.
