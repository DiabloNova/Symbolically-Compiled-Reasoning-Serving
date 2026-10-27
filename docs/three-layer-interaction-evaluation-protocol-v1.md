# SCRS composed-layer interaction evaluation protocol v1

**Status:** protocol amendment after an exploratory pilot; not a report of completed model experiments. Because a small pilot has already been inspected, this amendment must be frozen before new confirmatory data collection, and exposed pilot rows must not be relabeled as confirmatory evidence. It makes the primary hypothesis about *composition* testable rather than assuming that individual-layer performance predicts composed-system performance.

## 1. Primary hypothesis

The primary hypothesis is that the composed SCRS path provides a measurable end-to-end benefit relative to the original-context baseline and relative to relevant leave-one-layer-out ablations. Individual components are not required to improve the primary endpoint in isolation. A component may contribute only through interactions with other components, or may trade off accuracy against latency, token usage, cost, or failure containment.

The primary claim must be phrased as a hypothesis until evaluated on held-out, paired test cases. The theoretical statements in the manuscript do not establish that the deployed encoder, graph, gate, Anchor, or renderer satisfies their assumptions.

## 2. The current benchmark is not yet an interaction experiment

The current reference runner emits three conditions: `baseline`, `capsule_only`, and `compiled_graph_gates`. The last condition includes the capsule extraction, graph/compatibility gates, Anchor hint, and compiled-path renderer. Those three arms can support a preliminary paired comparison, but they do **not** identify the separate conditional effect of graph gates, the effect of Anchor, or their interaction. A difference between the full path and the baseline must not be presented as a measured interaction or as causal proof of every layer's contribution.

## 3. Required paired conditions

For the same selected source rows, add the following arms. Keep model IDs/revisions, source rows, task contract, label inventory, decoding settings, and scoring rules fixed wherever the architecture permits; record unavoidable differences.

| Arm | Capsule extraction | Graph / compatibility gates | Anchor hint | Final decision context |
|---|---|---|---|---|
| B — baseline | No | No | No | Original source context |
| C — capsule-only | Yes | No | No | Capsule |
| CG — capsule + graph | Yes | Yes | No | Capsule plus graph/gate trace; renderer receives no Anchor hint |
| CA — capsule + Anchor | Yes | No | Yes | Capsule plus Anchor hint; graph is not consulted for admission |
| CGA — composed SCRS | Yes | Yes | Yes | Capsule, accepted gate trace, Anchor hint, compiled renderer |

CA and CG are *component ablations conditioned on having a capsule*; they are not claims that Anchor or graph gates are meaningful with no capsule. This is a constrained 2×2 design for the graph and Anchor factors conditional on capsule availability, plus baseline and capsule-only anchors. If the implementation cannot run an arm faithfully, mark it unavailable and do not calculate a contrast that needs it.

**Primary composition contrast:** CGA versus B on identical test rows.

**Layer-removal contrasts:** CGA versus C, CGA versus CG, and CGA versus CA. These ask whether adding the remaining layers changes performance from the relevant partial path; they do not alone prove super-additivity.

**Conditional graph–Anchor interaction on the capsule path:** let (Y_{ga,i}in{0,1}) indicate correct prediction for row (i) under CG when (g=1,a=0), CA when (g=0,a=1), CGA when (g=1,a=1), and C when (g=0,a=0). Define
[
\widehat{\Delta}_{GA}=\frac{1}{n}\sum_{i=1}^n
(Y_{11,i}-Y_{10,i}-Y_{01,i}+Y_{00,i}).
]
A positive value indicates a positive additive interaction in correctness probability **conditional on the capsule path and the tested sample**. Report two summaries: (i) the operational contrast on all attempted rows, retaining fail-closed fallback outcomes; and (ii) a secondary mechanistic contrast among rows with schema-valid capsules. The latter conditions on a post-extraction outcome and must not be treated as an unbiased policy estimand. Neither is proof of a universal interaction. Report paired uncertainty intervals and task-wise results. If this contrast is not implemented and run, say that interaction remains unmeasured.

## 4. The gate's primary role also requires fault-injection evaluation

On valid, unmodified capsules, deterministic provenance/schema gates may simply pass; clean-case accuracy alone cannot show that they provide safety value. Evaluate gates on a separately specified challenge suite containing controlled single-fault and multi-fault capsules, including wrong task ID, stale contract/revision, mismatched source hash, label inventory mismatch, malformed schema, missing decision-relevant fact, and corrupted qualifiers/exceptions. Do not mix these challenge examples into the ordinary LegalBench accuracy denominator.

For each fault class, report:
- counts attempted, accepted, rejected, and sent to fallback;
- false acceptance rate (invalid capsules incorrectly admitted) with exact numerator/denominator and uncertainty;
- false rejection rate for valid capsules;
- resulting end-to-end decision error on paired faulted/unfaulted cases;
- gate decision, reason code, and fallback path for each case.

Keep provenance/schema validity distinct from semantic correctness. A gate passing is not evidence that the capsule preserves meaning.

## 5. Outcomes and inferential plan

### Primary end-to-end outcome
For every task and arm, report accuracy, macro-F1, invalid-output rate, selected row IDs, and Wilson 95% intervals for descriptive accuracy. The main paired comparison is correctness of CGA versus B on the same rows. Use McNemar's test for the paired binary correct/incorrect outcome where its assumptions are appropriate; report the 2×2 discordance table and effect size, not only a p-value.

### Interaction outcome
For \(\Delta_{GA}\), calculate the row-paired contrast above and obtain a confidence interval by resampling source rows within each task (and preserving all arm predictions for a sampled row). Tasks are different populations and must be reported separately. Any cross-task summary is secondary and must identify its weighting scheme. If confirmatory claims are made across multiple tasks or multiple primary contrasts, predeclare and apply an appropriate multiplicity procedure (for example, Holm adjustment).

### Sample size
Do not set the definitive sample size based on an observed score that is then reused as confirmatory evidence. Use a clearly labeled pilot to estimate paired discordance/variance, choose a smallest effect size of scientific interest, and run a prospective power calculation or simulation at a declared alpha and power target. Freeze sample size, row-selection method, analysis code, exclusions, and the primary contrast before running the confirmatory test split. If a full task split is affordable and licensing permits, prefer it; if using a sample, use deterministic seeded random sampling and report the exact indices.

### Secondary operational outcomes
Report provider-reported input/output tokens, transport attempts, confirmed generations, local orchestration time, sequential provider latency per path, fallback rate, malformed capsule rate, and cost only where a tariff and billing basis are defensibly known. Count shared physical calls once in run totals but attribute them transparently to each counterfactual path budget. Never infer invoice cost from token counts without the relevant pricing, caching, retries, and billing semantics.

### Semantic preservation
Keep the existing independent human annotation protocol as a separate outcome. Double-annotate capsules blind to condition, provider, prediction, metrics, and gold label; report initial agreement and adjudication. Classification accuracy, output agreement, schema validity, and graph acceptance are not substitutes for decision-relevant semantic-preservation annotations or an estimator of (I(Y;D\mid Q,K)).

## 6. Run integrity and exclusions

- Pin dataset archive hash/revision, source commit, model/provider IDs and revisions if exposed, provider request-option hash, all prompt hashes, sample seed/indices, and code versions.
- Run every arm on identical row IDs. Preserve partial traces and failed requests; do not fabricate outputs.
- Report both intent-to-evaluate coverage and complete-pair coverage. Do not silently drop rows whose capsule creation fails; that failure is an outcome for capsule-dependent arms. Provider/infrastructure failures should be enumerated separately, with sensitivity analysis where appropriate.
- Keep pilot, implementation tests, synthetic mock runs, challenge-suite results, and confirmatory model measurements in separate artifacts.
- Preserve raw case-level predictions and evidence hashes; generate tables from machine-readable output.
- Do not change prompts or thresholds after inspecting final test labels. Any tuning belongs on a declared development split.

## 7. Publication decision rule

A paper may claim measured composition benefit only if paired live-model predictions and the predeclared analysis support it. It may claim a measured graph–Anchor interaction only if all four conditional arms C, CG, CA, and CGA are implemented faithfully, run on the same rows, and analysed with the declared interaction contrast. If CGA improves over baseline but the interaction contrast is inconclusive, report the overall observed difference and the uncertainty without claiming synergy. If individual arms are weak but CGA is strong, describe that as an observed pattern; do not present it as a general law from a small pilot.

The current runner is a **reference prototype**, not a complete verified implementation of the manuscript's production architecture. Before making a claim about the full paper system, map each experimental arm to the manuscript-defined Tier I/II/III operations and document any omitted runtime, routing, cache, or transport behaviour. The theoretical results should remain labeled **analytical under stated assumptions**. Accuracy, decision-relevant semantic preservation, end-to-end latency, and billed cost remain empirical quantities and must be labeled unmeasured until their corresponding data are collected.
