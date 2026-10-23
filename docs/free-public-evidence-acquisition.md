# Free public evidence acquisition and evaluation plan for SCRS

**Status:** licence-reviewed datasets and reproducible tooling are available in the research branch. This is evidence preparation, not an SCRS model evaluation. **No baseline or SCRS predictions have been generated.**

## Evidence classes and decision rule

Every claim must be labeled one of: **theoretical/proved**, **public-benchmark evaluation**, **synthetic/simulated**, **measured deployment**, **literature-supported**, or **unresolved**. A passing software test over original fixtures is not a benchmark score. A public benchmark can test task-level label preservation or evidence retrieval; it cannot establish provider billing, production network latency, or the paper's projected savings by itself.

## Dataset sources and licensing decisions

The LegalBench upstream project says licences vary by task. Only the six task pages below explicitly state **CC BY 4.0** and have been allowlisted in `data/manifests/legalbench.json`. Unlisted tasks are denied by default. The task-level permissions and attribution text are preserved in the manifest and per-split run metadata.

| Task | Test examples in pinned snapshot | Intended probe | Official task page |
|---|---:|---|---|
| `abercrombie` | 95 | Five-way trademark classification | https://hazyresearch.stanford.edu/legalbench/tasks/abercrombie.html |
| `contract_qa` | 80 | Clause/question issue identification | https://hazyresearch.stanford.edu/legalbench/tasks/contract_qa.html |
| `ucc_v_common_law` | 94 | Distinguish UCC from common-law contract treatment | https://hazyresearch.stanford.edu/legalbench/tasks/ucc_v_common_law.html |
| `function_of_decision_section` | 367 | Legal opinion section function classification | https://hazyresearch.stanford.edu/legalbench/tasks/function_of_decision_section.html |
| `legal_reasoning_causality` | 55 | Whether reasoning invokes statistical evidence | https://hazyresearch.stanford.edu/legalbench/tasks/legal_reasoning_causality.html |
| `citation_prediction_classification` | 108 | Whether a cited case supports a statement | https://hazyresearch.stanford.edu/legalbench/tasks/citation_prediction_classification.html |

The public snapshot is pinned to Hugging Face dataset revision `daec8237410aa23e3faf4bc41ad8b3a7e1696826`. The pinned source file, not a potentially inconsistent overview-page sample count, is the source of observed split counts. There are 32 train examples and 799 test examples (831 total rows) across six task configurations. The train splits are very small for several tasks; they should not be described as robust training datasets or pooled into a single unqualified accuracy figure.

- Dataset home: https://huggingface.co/datasets/nguha/legalbench
- LegalBench paper: Guha et al. (2023), https://arxiv.org/abs/2308.11462
- CC BY 4.0 legal code: https://creativecommons.org/licenses/by/4.0/
- LegalBench task-by-task licensing policy: https://hazyresearch.stanford.edu/legalbench/tasks/

### LegalBench-RAG remains blocked

The canonical repository is https://github.com/ZeroEntropy-AI/legalbenchrag and the paper is https://arxiv.org/abs/2408.10343. Its code licence does not establish a single redistribution licence for the linked corpus, which refers to ContractNLI, CUAD, MAUD, and PrivacyQA. Therefore `data/manifests/legalbenchrag.json` records a **blocked pending source-specific licence review** decision. No LegalBench-RAG corpus is included in this branch. Similarly, FRAMES remains a discovery lead only until the canonical dataset source and licence are checked: https://rag-repo.org/datasets/.

## Retrieval and data integrity

`scripts/data/acquire_public_evidence.py` is standard-library-only and requires no API/model key. It fails closed unless the task is allowlisted, task-level reuse is recorded, and the task's label inventory is declared. It pins a full upstream commit SHA (or accepts `--revision` for exact reproduction), downloads the original TSV, preserves task-specific columns (for example `contract`, `Citation`, and `Paragraph` rather than assuming `text`), and writes:

- raw TSV copy;
- normalized JSONL representation;
- `*.run-manifest.json` with source URL/revision, task licence and attribution, row count, source/output bytes and SHA-256, label inventory, and retrieval timestamp.

A ready-to-extract snapshot is stored at `data/public/legalbench/extra-licensed-snapshots-v1.tar.gz`. Its SHA-256 and contents are documented in `data/public/legalbench/README.md`. Extract from the repository root:

```bash
tar -xzf data/public/legalbench/extra-licensed-snapshots-v1.tar.gz -C .
```

Re-acquire one task split from the exact same source revision:

```bash
python scripts/data/acquire_public_evidence.py --task function_of_decision_section --split test --revision daec8237410aa23e3faf4bc41ad8b3a7e1696826
```

The downloader should also be tested without a network connection for parsing, task allowlist failure, revision format, normalization determinism, and checksum metadata.

## Evaluation protocol required before paper claims

For each selected task separately, compare at least: (1) original-context baseline, (2) capsule-only condition, and (3) capsule plus compiled graph and compatibility gates. Where the goal is to isolate the representation change, hold the model/version, input examples, decoding settings, and scoring rules constant. Add predeclared ablations for individual decision-relevant fields and compatibility gates. Keep all model tuning on a development split, not test. Preserve source gold labels, and document any human grading.

`scripts/evaluation/score_legalbench.py` scores **supplied prediction files only**; it does not invoke a model. One prediction per test index is required, with the shape `{"index": 0, "prediction": "generic"}`. It rejects missing/duplicate/extra indices and labels outside the task inventory, normalizes labels only by whitespace trimming and case-folding, and reports accuracy with Wilson 95% interval, macro precision/recall/F1, per-class metrics, and a confusion matrix. Example:

```bash
python scripts/evaluation/score_legalbench.py \
  --predictions results/public-benchmarks/abercrombie/original-context/predictions.jsonl \
  --condition original-context \
  --model-id "record-the-exact-model-id" \
  --method-description "Record prompt, adapter, and environment here" \
  --output results/public-benchmarks/abercrombie/original-context/metrics.json
```

Use the same gold split when evaluating each condition. Report task-specific metrics and confidence intervals separately rather than treating unlike legal tasks as interchangeable. A data acquisition run or a scorer test is not evidence that SCRS outperforms a baseline.

## Runtime and cost evidence policy

Do not label expectations from equations or Monte Carlo projections as measured P50/P95. Real latency/cost claims require a runnable implementation commit, environment/hardware, dated provider pricing and model revision, logical Anchor count, actual HTTP attempts and retries, batch/cache hits, input/output token counts, stage timestamps, fallback status, errors/timeouts, and provider-billed usage when available. Public benchmarks cannot independently establish actual provider billing or production latency. vLLM benchmark tooling (https://docs.vllm.ai/en/latest/cli/bench/) may be used as a serving instrument but does not itself validate SCRS.

## Reproduction checks performed

- Acquisition tests: 9 passed.
- Scorer tests: 7 passed.
- Python compile check: `python3 -m compileall -q scripts tests` passed.
- Local data validation: all 12 train/test split triples (TSV, JSONL, manifest) matched their recorded row counts and both SHA-256 hashes.
- These checks validate tooling and data integrity only; they do not score a model. Existing latency/cost scenarios remain synthetic until actual implementation traces are captured.
