# LegalBench — selected public snapshot with task-level licence evidence

Every included task's official task page explicitly states Creative Commons Attribution 4.0 International (CC BY 4.0). Cite Guha et al. (2023), “LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning in Large Language Models,” https://arxiv.org/abs/2308.11462, and the task-specific page. CC BY 4.0 text: https://creativecommons.org/licenses/by/4.0/.

## Source and exact version

- Dataset: https://huggingface.co/datasets/nguha/legalbench
- Upstream commit: `daec8237410aa23e3faf4bc41ad8b3a7e1696826`
- Archive: `extra-licensed-snapshots-v1.tar.gz`
- Archive SHA-256: `f2eed6bdf3bf08d5837c33c04634e1fbb32544ac1d0e1eeacd20e034ce0ade0a`
- Archive files: 6 task configurations × 2 splits × 3 artifacts = 36 files (raw TSV, normalized JSONL, run-manifest JSON).
- Observed counts: 32 training rows, 799 test rows, 831 in total. The counts are from the actual TSVs at the pinned revision, not copied from the task catalog.
- Extract from repository root: `tar -xzf data/public/legalbench/extra-licensed-snapshots-v1.tar.gz -C .`

| Task | Train | Test | Official task page |
|---|---:|---:|---|
| `abercrombie` | 5 | 95 | [Task page](https://hazyresearch.stanford.edu/legalbench/tasks/abercrombie.html) |
| `contract_qa` | 8 | 80 | [Task page](https://hazyresearch.stanford.edu/legalbench/tasks/contract_qa.html) |
| `ucc_v_common_law` | 6 | 94 | [Task page](https://hazyresearch.stanford.edu/legalbench/tasks/ucc_v_common_law.html) |
| `function_of_decision_section` | 7 | 367 | [Task page](https://hazyresearch.stanford.edu/legalbench/tasks/function_of_decision_section.html) |
| `legal_reasoning_causality` | 4 | 55 | [Task page](https://hazyresearch.stanford.edu/legalbench/tasks/legal_reasoning_causality.html) |
| `citation_prediction_classification` | 2 | 108 | [Task page](https://hazyresearch.stanford.edu/legalbench/tasks/citation_prediction_classification.html) |

Each `*.run-manifest.json` records source URL and revision, licence/attribution, actual row count, labels, byte counts, and raw/normalized SHA-256 hashes. Normalization removes TSV quoting and converts the `index` field to an integer; other task-specific values and columns are preserved.

This snapshot contains benchmark source data and gold labels only. It does **not** contain model predictions or establish SCRS accuracy, semantic preservation, cost, or latency claims. Report metrics per task; do not combine these unlike task types into an unqualified accuracy. Several train splits are extremely small and are only the official upstream train split.

The LegalBench-RAG linked corpus is deliberately excluded pending separate licence checks for every underlying source dataset.
