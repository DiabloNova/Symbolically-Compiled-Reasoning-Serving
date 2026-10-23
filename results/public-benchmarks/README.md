# SCRS public-benchmark results

This directory starts with a **preregistered plan, not empirical results**.

- `experiment-plan.v1.json` pins six source-licensed LegalBench task configurations, their exact upstream dataset revision, task-specific test splits, proposed comparison conditions, required reporting metadata, and current run status.
- No prediction or metric file is present yet; placeholders are prohibited.
- Each task must be scored separately using `scripts/evaluation/score_legalbench.py` after a real model run produces one prediction per test index.
- Original-context, capsule-only, and capsule-plus-compiled-graph/gates conditions are blocked until a reproducible execution path exists for those conditions. Preserve this as a blocker rather than substituting synthetic data.
- For latency/cost claims, use real traces and dated provider/hardware details. The LegalBench task scores alone cannot verify deployment cost or latency.
