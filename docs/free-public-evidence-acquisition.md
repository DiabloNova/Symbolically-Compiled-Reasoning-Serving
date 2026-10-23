# Free public evidence acquisition plan for SCRS

**Status:** source-discovery baseline; no result here is claimed as measured SCRS performance.  
**Goal:** establish a reproducible, zero-cost public-data pipeline for strengthening the SCRS manuscript.  
**Policy:** preserve provenance and licence terms. Do not commit third-party raw data until redistribution rights, file size, and source integrity are checked. Prefer manifests, deterministic retrieval scripts, checksums, and small derived fixtures.

## 1. Evidence classes

Label every artifact and claim as **theoretical**, **public-benchmark evaluation**, **synthetic/simulated**, **measured deployment**, **literature-supported**, or **unresolved**.

Public benchmarks can test semantic preservation, retrieval, decision correctness, transfer-gate behavior, and reproducibility. They cannot establish real production API costs, provider billing, network round trips, or deployment latency.

## 2. Candidate public resources

| Resource | Intended use | Cost/access | Limitations |
|---|---|---|---|
| [LegalBench](https://hazyresearch.stanford.edu/legalbench/) | Diverse legal reasoning tasks; decision-relevant fact preservation and downstream answer consistency | Public benchmark; task data via Hugging Face | Review each task's terms and evaluation requirements; some tasks need manual grading |
| [LegalBench download/evaluation guide](https://hazyresearch.stanford.edu/legalbench/getting-started/) | Canonical download instructions, prompts, and evaluation guidance | Public documentation | Follow task-level protocols rather than merging all tasks into one score |
| [LegalBench-RAG repository](https://github.com/zeroentropy-ai/legalbench) | Clause/span retrieval and evidence grounding; test whether a capsule preserves exact supporting evidence | Public repository; inspect current files and underlying dataset terms before redistribution | Packaging licence does not automatically cover every underlying document |
| [vLLM benchmark CLI](https://docs.vllm.ai/en/latest/cli/bench/) | Reusable local serving benchmark patterns and definitions for TTFT, TPOT, ITL, end-to-end latency, and throughput | Open-source tooling; local/synthetic workloads possible | Tooling does not itself provide SCRS evidence; real measurement needs a running system and documented environment |
| [vLLM benchmark harness](https://github.com/vllm-project/vllm-bench) | Reproducible benchmark harness and machine-readable result patterns | Public source repository | Record exact version and workload; prefix-cache reuse can distort comparisons |
| [FRAMES discovery listing](https://rag-repo.org/datasets/) | Candidate multi-hop retrieval/reasoning stress test | Public discovery listing | Verify canonical source, split, and licence before use |

**Initial priority:** start with a licence-reviewed subset of LegalBench and LegalBench-RAG. Add an original synthetic adversarial suite for SCRS-specific invariants: deadlines, thresholds, exceptions, exclusions, jurisdiction, evidence admissibility, tenant scope, adapter/version mismatch, and transfer denial. Expand to other domains only after the core protocol is stable.

## 3. Dataset inclusion gate

Before importing any dataset, record:

1. Canonical source, publisher, version/revision, retrieval date, and source commit/tag where available.
2. Licence for both benchmark packaging and underlying data; redistribution and attribution requirements.
3. Task/split, record count, fields used, filtering rules, and excluded records.
4. Raw-file SHA-256, byte size, extraction command, and preprocessing version.
5. Whether raw data may be committed. If not, commit the manifest, retrieval script, checksum, and local cache instructions only.
6. Any personal/sensitive data, copyright restrictions, or access conditions; never upload restricted content.
7. Evaluation mapping: input, gold evidence/answer, SCRS output, baseline output, scoring function, and human-review requirements.

## 4. Minimum evaluation protocol

For each task, compare at least:

- **Original-context baseline:** solve using the uncompressed source context.
- **Capsule-only:** solve using the SCRS-extracted representation.
- **Capsule + compiled graph/gates:** apply the declared decision graph and compatibility checks.
- **Ablations:** remove one critical field or gate at a time.
- **Adversarial counterexamples:** near-duplicate cases differing in exactly one decision-relevant condition.

Report task-level and aggregate metrics, uncertainty intervals where appropriate, failure taxonomy, sample size, split, seeds, model/version, and exact commands. Avoid leakage between prompt development and final evaluation. Declare the primary metric and decision rule before final evaluation.

## 5. SCRS-specific tests to build

The initial local fixture should cover:

- Preservation of obligations, deadlines, thresholds, exceptions, exclusions, negation, and other decision-relevant facts.
- Type-safe bindings, deterministic graph execution, termination, and cycle rejection.
- Compatibility gates for domain, jurisdiction, adapter version, tenant scope, transfer licence, preconditions, and evidence admissibility.
- Negative controls where a single gate mismatch must force a safe miss/bailout.
- Counterexample pairs differing in one decision-relevant feature.
- Algorithm-counter invariants, including n_int and oracleCallsAvoided.
- Probability normalization and consistency among equations, tables, and generated outputs.

These original fixtures are useful tests, but do not replace independent public-benchmark evaluation.

## 6. Runtime and cost evidence policy

Do not derive empirical P50/P95 from expected-value equations. For real latency/cost claims, capture implementation commit, environment/hardware, model/provider and pricing snapshot, request ID, logical anchor count, actual HTTP attempts, retries, batching/cache hits, input/output token counts, stage timestamps, fallback status, errors/timeouts, and billed usage when available. Redact request content and secrets.

Until real traces exist, keep current scenario outputs labelled **synthetic** and report sensitivity analyses over declared assumptions. Public benchmark runs may validate algorithms and local runtime behavior, but cannot prove provider billing or production network behavior.

## 7. Proposed repository layout

- data/README.md — dataset catalogue, licence decisions, retrieval instructions.
- data/manifests/*.json — source, licence, split, checksum, and preprocessing metadata.
- data/fixtures/scrs_adversarial_cases.jsonl — small original test fixtures.
- scripts/data/download_public_benchmarks.py — deterministic public-data retrieval and verification.
- scripts/evaluation/run_public_benchmarks.py — benchmark adapters and metrics.
- results/public-benchmarks/<run-id>/ — machine-readable results, configuration, logs, and manifest.
- docs/research-validation-ledger.md — claim-to-evidence status and links to generated artifacts.

Do not add large third-party data or change manuscript claims until the licence review, protocol, and reproducibility checks pass.

## 8. Sources

- Stanford LegalBench: https://hazyresearch.stanford.edu/legalbench/
- LegalBench getting started: https://hazyresearch.stanford.edu/legalbench/getting-started/
- LegalBench-RAG: https://github.com/zeroentropy-ai/legalbench
- vLLM benchmark CLI: https://docs.vllm.ai/en/latest/cli/bench/
- vLLM benchmark harness: https://github.com/vllm-project/vllm-bench
- FRAMES discovery listing: https://rag-repo.org/datasets/

**Current status:** discovery only. Dataset files have not yet been imported, licence-reviewed, or evaluated under this plan.
