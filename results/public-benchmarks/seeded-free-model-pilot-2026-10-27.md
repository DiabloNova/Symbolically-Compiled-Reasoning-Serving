# Seeded free-model pilot: partial execution report

Date: 2026-10-27
Branch: `experiments/scrs-seeded-semantic-pilot-2026-10-27`
Sample seed: `20261027`
Rows per task: 8, sampled from the pinned LegalBench test split
Model: `dots-studio/dots-3-note-preview:free`
Gateway: `https://ai-gateway.kilo.ai/api/v1`
Request extension: `{"reasoning":{"effort":"none"}}`
Temperature: 0

## Status: partial; not a completed six-task benchmark

The seeded pilot completed all three conditions for three of six tasks. Three other tasks did not complete because the free gateway returned HTTP 429 rate-limit responses. Those tasks have no accuracy result and must not be counted as method failures.

| Task | n per condition | Baseline | Capsule-only | Compiled-graph | Status |
|---|---:|---:|---:|---:|---|
| Abercrombie | 8 | 37.5% | 87.5% | 87.5% | Completed |
| Citation prediction classification | 8 | 87.5% | 50.0% | 50.0% | Completed |
| Contract QA | 8 | 100.0% | 75.0% | 75.0% | Completed |
| Function of decision section | 8 intended | — | — | — | HTTP 429 from oracle provider |
| Legal reasoning causality | 8 intended | — | — | — | HTTP 429 from renderer |
| UCC v. common law | 8 intended | — | — | — | HTTP 429 from renderer |

Completed sample counts: 24 paired source rows. The runner makes multiple model calls per condition, so row/condition counts are not provider-request counts.

## Interpretation

Results are inconsistent across tasks: compression helped the observed Abercrombie sample, but hurt citation prediction and contract QA. With only eight examples per task, no claim of overall superiority, statistical significance, or generalization is warranted. The compiled-graph condition matched capsule-only in the three completed tasks; this is not evidence of added value from the graph gates.

The free endpoint rate-limited subsequent tasks. The six-task run is **not complete**. Do not fill missing results with mock predictions or treat rate-limit failures as incorrect predictions.

## Reproducibility changes on this branch

- Added SHA-256-derived, task-specific seeded random sampling.
- Run manifest records seed, selection strategy, selected test row indices, available test rows, and request-extension keys/hash.
- Added explicit `SCRS_PROVIDER_EXTRA_BODY_JSON` support with JSON validation and safeguards against overriding core request fields.
- Added regression tests for seeded selection and provider request settings.
- Added a blinded, two-annotator decision-semantic preservation protocol.
- Added documentation for the tested free-provider configuration.

## Still incomplete or unmeasured

- Full six-task accuracy run in a consistent rate-limit window.
- Independent human annotation of decision-relevant semantic preservation.
- Actual billed cost; the runner records token usage but no verified dollar invoice.
- Production latency, scalability, and inferential evidence of superiority.
- Whether graph gates add value beyond the shared capsule.

## Next step

Repeat the remaining three tasks after the free gateway quota/rate window resets, using the same seed and provider configuration. Preserve successful run directories. Analyze all six tasks separately, then prepare a blinded annotation worksheet from the exact generated capsules. Do not merge the branch until CI is green and the user explicitly approves.
