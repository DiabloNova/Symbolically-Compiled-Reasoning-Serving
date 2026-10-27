# Decision-Relevant Semantic-Preservation Evaluation Protocol v1

**Status:** protocol preregistration; no human annotation results are implied by this document.

## 1. Research question and estimand

Does a generated SCRS evidence capsule retain the information needed to make the same task-relevant decision as the original input? This is distinct from whether a downstream classifier happens to output the correct label.

The primary estimand is the proportion of independently annotated test cases whose capsule preserves decision-relevant meaning under the task contract. Results must be reported separately for each task and may be macro-averaged only as a secondary descriptive summary. Do not infer general semantic equivalence from classification accuracy alone.

## 2. Unit of analysis and blinding

The unit is one source test row paired with the capsule generated from that row by the capsule-extraction model. The compiled-graph route currently reuses that same capsule; it is not an independent extraction sample.

For each selected row, present annotators with:
- the task description and allowed label inventory;
- the original source fields, without the gold label;
- the generated capsule JSON, without model/provider identity, method name, downstream predictions, token/latency/cost data, or gold label;
- a random blind item ID unrelated to source row index or condition.

Randomize item order per annotator. Annotators must not see the gold label until their annotations are locked. Keep the blind-ID mapping in a separate restricted file. The source row, selected test index, archive revision, capsule hash, and blind ID must be recorded for auditability.

## 3. Annotation rubric

Two annotators independently label every item. Use the task instructions to identify facts that can change a permitted decision; do not reward fluent wording or length.

### Primary binary outcome: decision-relevant meaning preserved

Set ds_preserved = 1 only when all of the following hold:
1. Every source proposition needed for the task decision is represented in the capsule, either directly or by a defensible equivalent.
2. Scope, negation, parties, temporal order, causal relations, thresholds, and other decision-changing qualifiers are preserved wherever present.
3. Material exceptions, contraindications, and ambiguity/unknown status are not silently removed.
4. The capsule does not add unsupported facts or introduce a material contradiction.
5. No material compression changes the set of task labels that a careful reader could defensibly select from the supplied evidence.

Otherwise set ds_preserved = 0. Annotators must cite the source span and capsule field supporting each material omission, distortion, or unsupported addition. Do not treat schema validity, provenance checks, or a graph gate passing as evidence that meaning is preserved.

### Severity and error tags

Assign the highest applicable severity:
- M0: no decision-relevant loss or distortion.
- M1: minor omission or wording change, with no plausible effect on a task decision.
- M2: material information lost or altered; a task decision could plausibly change.
- M3: direct contradiction, invented decisive fact, lost negation/exception, or other severe distortion.

Record zero or more error tags:
- OMISSION_CORE_FACT
- QUALIFIER_SCOPE_OR_NEGATION
- EXCEPTION_OR_CONTRAINDICATION
- ENTITY_OR_ROLE_SWAP
- TEMPORAL_OR_CAUSAL_RELATION
- AMBIGUITY_COLLAPSED
- UNSUPPORTED_ADDITION
- CONTRADICTION
- OTHER

M0 and M1 map to ds_preserved = 1 only if the primary criteria above are met. M2 and M3 always map to ds_preserved = 0.

### Annotation fields

Each annotation row must include:
- blind_item_id, annotator_id, task_id;
- ds_preserved (0/1), severity (M0–M3);
- error tags;
- source propositions judged decision-relevant;
- omitted/distorted/unsupported proposition descriptions;
- exact source and capsule evidence spans/fields;
- could_change_task_decision (yes/no/uncertain);
- free-text rationale.

Do not include the gold label in the annotator-facing sheet.

## 4. Adjudication and quality control

- Train annotators on a separate calibration set excluded from the reported test sample.
- Double-annotate all test capsules independently.
- Lock both initial annotation files before revealing disagreements or gold labels.
- A third adjudicator resolves disagreements with access to the two rationales but still without seeing downstream predictions.
- Report initial agreement before adjudication: raw agreement and Cohen's kappa for ds_preserved; use weighted kappa or an ordinal agreement statistic for severity. If class prevalence makes kappa unstable, report raw agreement and the contingency table rather than relying on kappa alone.
- Report adjudication rate and reasons. Preserve both initial annotations and the adjudicated value.

An LLM judge may be used only as a separately labeled exploratory analysis; it must not replace independent human annotations or be presented as ground truth.

## 5. Analysis plan

Primary results, task by task:
- count and rate of ds_preserved = 1, with Wilson 95% interval;
- M2/M3 material-loss rate;
- frequency of each error tag;
- agreement metrics before adjudication.

Secondary analysis:
- compare capsule preservation with downstream correctness after the annotations are locked;
- estimate the fraction of materially corrupted capsules that yield a different downstream label;
- report baseline/capsule/compiled-path accuracy separately and paired differences on the identical selected test rows.

Use paired row-level comparisons. For a final inferential claim, predeclare a sufficiently powered sample size and method (e.g., paired bootstrap stratified by task or McNemar test where appropriate); do not treat the initial small pilot as inferential. Do not pool task accuracies into an unqualified headline score.

## 6. Reproducibility and exclusions

Record the dataset archive SHA-256 and upstream revision, sample seed and exact row indices, model/provider ID, request-option hash and documented values, prompt/code revision, every capsule hash, parser failures, retries, fallback events, usage, and per-stage timing.

Invalid capsule output is a preservation failure for the capsule route and must remain in the denominator. Do not silently drop invalids or replace them with a fabricated capsule. Report provider failures separately; if a test row cannot complete all required conditions, preserve the partial trace and explain whether the paired row is excluded from accuracy comparison.

## 7. Annotation worksheet schema

Use these columns for the blinded annotation file:

blind_item_id,task_description,allowed_labels_json,source_fields_json,capsule_payload_json,capsule_available,annotator_id,ds_preserved,severity,error_tags,decision_relevant_propositions,omitted_or_distorted_propositions,source_evidence,capsule_evidence,could_change_task_decision,rationale

Do not include task ID, source row index, gold label, predictions, condition ranking, provider identity, performance metrics, or run ID in the annotator-facing worksheet. Store those fields in a separate restricted mapping with the blind ID, task ID, source row index, gold label, source hash, capsule hash/status, sample seed, run ID, model ID, and eventual predictions. Keep the mapping away from annotators until their initial annotations are locked.

## 8. Evidence boundary

This protocol defines how semantic-preservation evidence should be collected; it does not itself provide annotation results. Until independent annotations are completed and agreement is reported, decision-relevant semantic preservation remains **unmeasured**.
