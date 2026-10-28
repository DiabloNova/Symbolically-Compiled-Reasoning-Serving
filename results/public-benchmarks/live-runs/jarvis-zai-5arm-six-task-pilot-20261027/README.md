# SCRS five-arm six-task live pilot — 2026-10-27

**Status: completed exploratory pilot; not confirmatory and not publication-ready evidence.**

Six live-model cases were completed from the pinned LegalBench test archive, one row per task, with deterministic seed `20261027`. Each case was evaluated on the same five arms. The requested route was `zai/glm-4-flash`; every successful response reported resolved model `glm-4-flash`. No API key was used. Provider attempts were paced by at least five seconds.

## Paired outcomes

| Task | Test row | Gold | Baseline | Capsule | Graph, no Anchor | Anchor, no graph | Full composition | Per-row interaction* |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| abercrombie | 87 | fanciful | 0 | 0 | 0 | 0 | 1 | +1 |
| citation_prediction_classification | 37 | Yes | 1 | 1 | 1 | 1 | 1 | 0 |
| contract_qa | 19 | Yes | 1 | 1 | 1 | 1 | 1 | 0 |
| function_of_decision_section | 323 | Issue | 0 | 0 | 0 | 0 | 0 | 0 |
| legal_reasoning_causality | 48 | No | 1 | 1 | 0 | 0 | 0 | +1 |
| ucc_v_common_law | 68 | Common Law | 0 | 0 | 0 | 0 | 0 | 0 |

The columns are task-level correctness indicators for **one paired row**, not accuracy estimates. The graph–Anchor interaction column is the per-row correctness difference-in-differences `CGA − CG − CA + C`; it is not a statistical estimate with n=1.

## Interpretation

- Abercrombie: the composed route was correct where all four other arms were wrong.
- Citation prediction and contract QA: all five arms were correct.
- Function of decision section: all five arms were wrong; capsule-only produced an invalid label, which was retained as incorrect.
- Legal reasoning causality: baseline and capsule-only were correct; graph-only, Anchor-only, and the composition were wrong.
- UCC vs common law: all five arms were wrong.

This heterogeneous pattern motivates a larger paired evaluation but does not prove that composition generally improves performance. It neither confirms nor refutes the theoretical hypothesis. Different tasks must not be pooled into a headline score or into a single inferential interaction estimate.

## Usage and reproducibility

Across the six completed rows: **48 provider transport attempts, 48 confirmed generations, 17,996 provider-reported input tokens, and 846 provider-reported output tokens**. Billed cost is NR. Request durations are not production latency evidence; wall-clock time includes deliberate request pacing.

- `case-results.jsonl`: concatenated original case records for all six tasks.
- `analysis.json`: output of `experiments/scrs_runtime/analyze_factorial.py` (5,000 seeded bootstrap draws; intervals are degenerate at n=1 and are flagged descriptive-only).
- `run-manifest.json`: dataset hashes, sample indices, provider identity/configuration, and physical usage totals.
- Each original run directory retains its own metrics, five prediction files, capsule/gate trace, and event log.

Dataset archive SHA-256: `f2eed6bdf3bf08d5837c33c04634e1fbb32544ac1d0e1eeacd20e034ce0ade0a`. Upstream revision: `daec8237410aa23e3faf4bc41ad8b3a7e1696826`.

## Remaining publication gates

1. Increase the number of independently selected, paired test rows per task using a predeclared protocol and appropriate prospective power analysis.
2. Keep every arm on identical row IDs and retain all invalid capsules, invalid predictions, and fallback outcomes.
3. Complete independent, blinded human annotation of decision-relevant semantic preservation; this remains unmeasured.
4. Measure gate false-accept and false-reject rates on a defined fault-injection challenge set.
5. Do not claim production latency, token savings, billed-cost reductions, or confirmatory statistical significance from this pilot.
6. Exclude these six exposed row indices from any confirmatory held-out sample.

**Evidence boundary:** this is a saved exploratory pilot, not a confirmatory result. The five-arm runner remains a reference prototype and is not yet demonstrated to implement every operation in the manuscript's full multi-tier architecture.
