# Seeded free-model pilot — 2026-10-27

## Status and scope

This report records the completed portion of a real-model paired pilot after adding deterministic sample selection and provider-option recording to the SCRS reference runner. It is **exploratory evidence only**, not a complete benchmark or proof of SCRS superiority.

- Branch: `experiments/scrs-seeded-semantic-pilot-2026-10-27`
- Parent experiment prototype: `experiments/scrs-anchor-live-benchmark-2026-10-26`, commit `c627e9e92c6c6a4a703864aa36bb22c2764fc17a`
- Dataset: LegalBench pinned archive, SHA-256 `f2eed6bdf3bf08d5837c33c04634e1fbb32544ac1d0e1eeacd20e034ce0ade0a`
- Upstream revision: `daec8237410aa23e3faf4bc41ad8b3a7e1696826`
- Test-only split, no training rows in the scoring denominator
- Selection: 8 rows per task, using deterministic SHA-256-seeded sampling, seed `20261027`
- Completed tasks: 2 of 6; 16 paired source rows
- Model: `dots-studio/dots-3-note-preview:free`
- Endpoint: Kilo AI Gateway OpenAI-compatible API; no API key was supplied
- Temperature: 0; provider request extension `{"reasoning":{"effort":"none"}}`
- Request extension fingerprint: `826fa4e6d20464130a7af648c719976b6a00067d224ca5ce6b092ecdc5f1fcaf`
- All three conditions used the same model ID within each task: baseline, capsule-only, and compiled-graph gates plus Anchor.

The code records the sampling seed, exact selected row indices, source archive identity, and provider-option key/hash in the run manifest. The optional provider request body is validated to prevent it overriding the core model, message, temperature, token-budget, or streaming fields.

## Accuracy results

The two tasks are reported separately, as specified in the experiment plan. Invalid labels remain incorrect rather than being discarded.

| Task | Selected test indices | Baseline | Capsule-only | Compiled-graph gates |
|---|---|---:|---:|---:|
| Abercrombie | 22, 32, 38, 57, 68, 72, 86, 87 | 3/8 (37.5%) | 7/8 (87.5%) | 7/8 (87.5%) |
| Citation prediction classification | 27, 32, 37, 58, 86, 87, 99, 101 | 6/8 (75.0%) | 5/8 (62.5%) | 4/8 (50.0%) |

Wilson 95% intervals are wide:
- Abercrombie: 3/8, 13.7%–69.4%; 7/8, 52.9%–97.8%.
- Citation prediction classification: 6/8, 40.9%–92.9%; 5/8, 30.6%–86.3%; 4/8, 21.5%–78.5%.

Paired row-level correctness changes relative to baseline:
- Abercrombie: capsule-only gained 4 correct rows, lost 0, and tied in correctness on 4; compiled-graph gained 4, lost 0, and tied on 4.
- Citation prediction classification: capsule-only gained 1, lost 2, and tied on 5; compiled-graph gained 1, lost 3, and tied on 4.

This is mixed evidence: compression improved the scores for the sampled Abercrombie rows but reduced scores on citation prediction. With eight samples per task and wide confidence intervals, these differences do not establish a general effect or statistical superiority.

## Latency and token usage

The runner's latency metric is the sum of sequential provider-call durations allocated to a path. It excludes local CPU/queue time and is not a production latency statistic.

| Task | Condition | Mean allocated provider latency per example | Allocated input tokens | Allocated output tokens |
|---|---|---:|---:|---:|
| Abercrombie | Baseline | 1.473 s | 1,328 | 24 |
| Abercrombie | Capsule-only | 4.244 s | 3,899 | 869 |
| Abercrombie | Compiled-graph gates | 6.340 s | 11,949 | 897 |
| Citation prediction classification | Baseline | 1.292 s | 1,196 | 16 |
| Citation prediction classification | Capsule-only | 3.770 s | 3,144 | 800 |
| Citation prediction classification | Compiled-graph gates | 5.872 s | 9,927 | 816 |

For the completed 16-row run, the gateway confirmed 78 generations and reported 27,415 input tokens plus 1,793 output tokens. Wall time measured around the two completed commands totaled approximately 141.95 seconds.

Token counts for capsule-only and compiled-graph paths include counterfactual allocation of the shared capsule-extraction request to each compressed path. They must not be added together to estimate physical run usage. The citation-prediction compiled path used one full-context fallback. The capsule-only condition had one invalid capsule output, counted as incorrect.

**Cost:** the selected model ID is labeled free and direct gateway responses for that model reported zero request cost, but the SCRS report currently records provider-billed dollar cost as not recorded (NR). No billing invoice or independent billing record was captured, so this report does not claim a measured dollar saving.

## Provider quota blocker

The next task, Contract QA, did not complete and is excluded from scored results. The gateway returned HTTP 429. A direct follow-up request then returned `PROMOTION_MODEL_LIMIT_REACHED`, explicitly asking for free signup to continue; switching the model ID did not bypass that gate. No signup or account creation was performed. The remaining four tasks were not run.

The provider documents describe anonymous free-model access and IP-based rate limits, while also warning that free models and availability can change:
- https://kilo.ai/docs/gateway/authentication
- https://kilo.ai/docs/gateway/models-and-providers
- https://kilo.ai/docs/gateway/usage-and-billing

To finish the six-task seeded pilot, the next legitimate options are a quota reset or a user-authorized free account/key. The runner must not synthesize missing predictions or merge partial rows into completed metrics.

## Semantic preservation

Decision-relevant semantic preservation remains **unmeasured**. Schema-valid capsules and accepted graph gates do not establish preservation of meaning. The preregistered independent annotation protocol is in `docs/semantic-preservation-evaluation-protocol-v1.md`. It specifies blinded source/capsule review, a binary decision-preservation outcome, M0–M3 severity, error tags, double annotation, agreement reporting, and adjudication.

No model-judged semantic scores are substituted for human annotations in this report.

## Verification performed

On the available isolated runner environment (Python 3.11.2):
- py_compile passed for the live client, runtime, runner, and new tests;
- 20 runtime contract tests passed;
- 3 runner metric regression tests passed;
- 6 new tests for seeded selection and provider request options passed;
- validation-only execution confirmed the pinned dataset and selected eight rows for each of the six approved tasks.

The actual scored live runs completed only for the two tasks listed above. The rate-limited and partial Contract QA runs are preserved as failures and not counted as results.
