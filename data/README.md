# Data and evaluation assets

This directory stores dataset provenance, approved retrieval manifests, small original fixtures, and scripts/instructions for repeatable evaluation.

## Data policy

- Do not commit third-party data until task-level licence and redistribution conditions have been reviewed.
- Follow source attribution requirements, preserve the upstream record fields, and include a run manifest and SHA-256 for every downloaded artifact.
- Prefer canonical upstream retrieval and hashes over manually reconstructed copies.
- Keep train/development/test splits separate; never tune on the final test split.
- Keep public-benchmark results, synthetic simulations, and real deployment measurements separate and label them clearly.
- Do not store API keys, user data, private prompts, or sensitive request logs.

## Current assets

- `fixtures/scrs_adversarial_cases.jsonl` — 12 original hand-authored examples for invariants such as deadline, exception, threshold, jurisdiction, tenant scope, negation, and evidence admissibility. These are test fixtures, not empirical results.
- `manifests/legalbench.json` — fail-closed allowlist for the single reviewed LegalBench pilot task `abercrombie`.
- `manifests/legalbenchrag.json` — LegalBench-RAG provenance and a blocked data-ingestion decision pending source-specific licence review.
- `scripts/data/acquire_public_evidence.py` — standard-library retrieval, revision pinning, JSONL export, and checksum/provenance generation.

## Run the approved pilot

From the repository root:

```bash
python scripts/data/acquire_public_evidence.py --task abercrombie --split test
python -m unittest discover -s tests -p 'test_public_data_acquisition.py' -v
```

The downloader queries the public Hugging Face dataset-server API and does not need a model/API key. It records the actual row count; no fixed expected count is assumed because public source metadata has an inconsistency.

## What is not yet present

No third-party benchmark data or benchmark result is currently committed in this PR. The script must be run to produce a revision-pinned artifact; inspect its generated manifest and the resulting file before deciding to track the data. Do not ingest LegalBench-RAG's bundled corpus until its underlying data terms have been individually checked.
