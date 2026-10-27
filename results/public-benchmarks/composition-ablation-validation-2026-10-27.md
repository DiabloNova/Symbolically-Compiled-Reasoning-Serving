# SCRS composed-layer pilot — implementation and validation status

**Date:** 2026-10-27  
**Branch:** `experiments/scrs-seeded-semantic-pilot-2026-10-27`  
**Validated branch head:** `0b34acc0d1647fb4547ec75ea80cd87e1282e86f`  
**Status:** five-arm reference runner implemented and offline-validated; confirmatory/live-model interaction experiment not completed.

## What was changed

The benchmark runner now has five named conditions: (B) original-context baseline, (C) capsule-only, (CG) capsule plus graph/gates with no Anchor hint, (CA) capsule plus Anchor with graph/gates bypassed, and (CGA) capsule plus graph/gates plus Anchor. The two intermediate arms isolate the graph and Anchor treatments conditionally on a valid capsule. Shared capsule extraction is counted once in run-wide usage and attributed transparently to each compressed counterfactual path.

A paired analysis utility computes task-level accuracy and Wilson intervals, exact two-sided McNemar comparisons against the composed path, and the row-level graph–Anchor difference-in-differences contrast:
`mean(CGA correctness - CG correctness - CA correctness + C correctness)`.
The operational contrast retains invalid-capsule/fallback outcomes; a separate valid-capsule subset is explicitly marked post-treatment and descriptive. No cross-task accuracy pooling is done.

The publication protocol and human annotation protocol remain separate: graph acceptance and prediction agreement do not establish decision-relevant semantic preservation. The new interaction protocol also specifies fault-injection tests for gate false acceptance/rejection, paired analysis, power/sample-size selection, and careful separation of pilot from future held-out confirmatory data. This is a reference implementation, not yet a demonstrated full implementation of every manuscript tier.

## Validation actually executed

From a fresh archive downloaded from the branch head:

- Python compile check: passed.
- Unit tests:
  - live runtime/client: 20 passed
  - runner metrics: 3 passed
  - seeded sampling/provider options: 6 passed
  - factorial analysis: 6 passed
  - five-arm composition runner: 2 passed
  - mock API: 4 passed
  - **Total: 41 passed across 6 test groups; 0 failed.**
- LegalBench validation-only run: passed for 8 deterministically sampled test rows each across six allowlisted tasks (48 rows checked for data/prompt/gate construction); it generated **no model predictions**.
- Mock integration smoke run: passed across six tasks and two rows per task; 12 cases, 5 arms, 60 synthetic condition predictions, 96 mock API requests, 0 mock request errors, 0 external provider calls. No accuracy/F1 metrics were produced. This demonstrates integration wiring only, not quality.

Pinned dataset archive SHA-256: `f2eed6bdf3bf08d5837c33c04634e1fbb32544ac1d0e1eeacd20e034ce0ade0a`.

## Live model and publication evidence still missing

The previously observed anonymous free-provider route returned HTTP 429 `PROMOTION_MODEL_LIMIT_REACHED` and required signup. No account or paid key was created. The older exploratory pilot reported one task with eight rows and three conditions, with baseline 0.375, capsule-only 0.875, and the then-combined route 0.875. That small, incompletely preserved pilot is **exploratory only**: it predates the five-arm design and cannot establish interaction, generalization, or confirmatory significance. Do not silently reuse its scores as five-arm results.

Still unmeasured: results from the new five-arm live experiment; a sufficiently powered held-out comparison; independent human decision-semantic annotations and inter-annotator agreement; gate false-accept/false-reject rates on a challenge suite; actual provider-billed cost; and production end-to-end latency. The theoretical propositions remain analytical under their declared assumptions and are not empirical proof of implementation correctness.

## Reproduction commands

Offline validation (no provider calls):

```bash
python -m py_compile experiments/scrs_runtime/anchor_client.py experiments/scrs_runtime/scrs_runtime.py experiments/scrs_runtime/run_legalbench.py experiments/scrs_runtime/analyze_factorial.py
python -m unittest discover -s tests -p "test_scrs_live_runtime.py" -v
python -m unittest discover -s tests -p "test_scrs_runner_metrics.py" -v
python -m unittest discover -s tests -p "test_scrs_sampling_and_provider_options.py" -v
python -m unittest discover -s tests -p "test_scrs_factorial_analysis.py" -v
python -m unittest discover -s tests -p "test_scrs_composition_arms.py" -v
python -m unittest discover -s tests -p "test_scrs_mock_api.py" -v
python experiments/scrs_runtime/run_legalbench.py --tasks all --max-examples 8 --sample-seed 20261027 --validate-only --output-root /tmp/scrs-validation --run-id validate-interaction
```

No PR was created or merged as part of this work.
