# Data and evaluation assets

This directory stores dataset provenance, approved retrieval manifests, original SCRS fixtures, and the inputs/results needed for repeatable evaluation.

## Data policy

- Do not commit third-party data until task-level licence and redistribution conditions have been reviewed.
- Follow source attribution requirements, preserve upstream fields, and include a run manifest and SHA-256 for every downloaded artifact.
- Prefer canonical upstream retrieval and hashes over manually reconstructed copies.
- Keep train/development/test splits separate; never tune on the final test split.
- Keep public-benchmark results, synthetic simulations, and real deployment measurements separate and label them clearly.
- Do not store API keys, user data, private prompts, or sensitive request logs.

## Current assets

- `fixtures/scrs_adversarial_cases.jsonl` — 12 original hand-authored examples for invariants such as deadline, exception, threshold, jurisdiction, tenant scope, negation, and evidence admissibility. These are software test fixtures, not empirical results.
- `manifests/legalbench.json` — fail-closed allowlist for the single reviewed LegalBench pilot task `abercrombie`.
- `manifests/legalbenchrag.json` — LegalBench-RAG provenance and a blocked data-ingestion decision pending source-specific licence review.
- `public/legalbench/abercrombie/` — attributed CC BY 4.0 test split, upstream TSV, normalized JSONL, and run manifest. The snapshot is pinned to upstream revision `daec8237410aa23e3faf4bc41ad8b3a7e1696826`.
- `scripts/data/acquire_public_evidence.py` — standard-library retrieval from an immutable upstream revision, TSV-to-JSONL normalization, and checksum/provenance generation.
- `scripts/evaluation/score_legalbench.py` — strict offline scoring for prediction JSONL. It does not run models or generate predictions.

## Reproduce acquisition and tests

From the repository root:

```bash
python scripts/data/acquire_public_evidence.py --task abercrombie --split test
python -m unittest discover -s tests -p 'test_public_data_acquisition.py' -v
python -m unittest discover -s tests -p 'test_legalbench_scoring.py' -v
```

The downloader pins a full source commit SHA and retrieves `data/abercrombie/{split}.tsv`. The committed test snapshot has 95 rows, balanced across five labels (19 each). The raw and normalized checksums are in `public/legalbench/abercrombie/test.run-manifest.json`.

## Produce and score predictions

Write a JSONL prediction file, one line per test row: `{"index": 0, "prediction": "generic"}`. Run `python scripts/evaluation/score_legalbench.py --help` for the required parameters. Do not generate placeholder predictions and present their scores as model evidence.

## Important limitation

The approved `abercrombie` task is a small five-way trademark-classification task. It validates data and scoring infrastructure but is not sufficient evidence for SCRS semantic-capsule correctness, legal reasoning performance, retrieval quality, latency, or cost. The repository currently contains no model predictions for this task and no measured SCRS comparison.
