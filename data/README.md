# Data and evaluation assets

This directory stores source-provenance manifests, an attributed public benchmark snapshot, original SCRS adversarial fixtures, and reproducible acquisition/scoring tools.

## Data policy

- Include third-party source data only when the specific task's licence permits the intended redistribution and attribution is supplied.
- Keep train/development/test splits separate; never tune using the final test split.
- Preserve source labels and all relevant input columns. Store SHA-256 and versioned provenance for source and normalized artifacts.
- Clearly separate public benchmark measurements, original unit tests, simulations, and deployment measurements.
- Do not store API keys, private prompts, user data, or sensitive traces.

## Assets

- `fixtures/scrs_adversarial_cases.jsonl` — 12 original examples testing deadlines, thresholds, exceptions, jurisdiction, tenant scope, negation, and admissibility. They are software fixtures, not empirical results.
- `manifests/legalbench.json` — task-level fail-closed allowlist for six task pages explicitly identifying CC BY 4.0.
- `manifests/legalbenchrag.json` — LegalBench-RAG data ingestion remains blocked pending underlying source-level licence review.
- `public/legalbench/extra-licensed-snapshots-v1.tar.gz` — complete six-task snapshot: 12 splits × raw TSV, normalized JSONL, and run manifest (36 files). Pinned to source revision `daec8237410aa23e3faf4bc41ad8b3a7e1696826`. See `public/legalbench/README.md` for attribution, counts, and archive hash.
- `scripts/data/acquire_public_evidence.py` — standard-library, immutable-revision downloader with task-specific column preservation and SHA-256 provenance.
- `scripts/evaluation/score_legalbench.py` — strict scorer for externally generated prediction JSONL; does not call models or produce predictions.

## Tests and commands

```bash
python scripts/data/acquire_public_evidence.py --task abercrombie --split test --revision daec8237410aa23e3faf4bc41ad8b3a7e1696826
python -m unittest discover -s tests -p 'test_public_data_acquisition.py' -v
python -m unittest discover -s tests -p 'test_legalbench_scoring.py' -v
```

The data snapshot is input/gold data only. No baseline predictions, SCRS predictions, model accuracy comparison, or measured deployment performance are included in this data acquisition stage.
