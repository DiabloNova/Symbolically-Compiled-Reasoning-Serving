# Data and evaluation assets

This directory holds dataset manifests, small original fixtures, and instructions for reproducible retrieval of public benchmarks.

## Data policy

- Do not commit third-party datasets until their source and redistribution licence have been checked.
- Prefer canonical upstream retrieval scripts plus SHA-256 manifests for large or non-redistributable sources.
- Keep train/development/test splits separate; never tune prompts or thresholds on the final test split.
- Keep public-benchmark results, synthetic simulations, and real deployment measurements in separate locations and label them clearly.
- Do not store API keys, user data, private prompts, or sensitive request logs.

## Current assets

- fixtures/scrs_adversarial_cases.jsonl — original, hand-authored schema examples for testing whether decision-relevant conditions survive representation changes. These are software test fixtures, not public benchmark results.
- Public benchmark candidates and inclusion rules: docs/free-public-evidence-acquisition.md.

## Next steps

1. Verify licence and exact version for each chosen upstream dataset.
2. Add a manifest with canonical URL, revision, split, licence, retrieval date, file hashes, and preprocessing version.
3. Implement deterministic download/validation and benchmark adapters.
4. Run baseline and SCRS variants without test-set tuning; publish machine-readable results and exact commands.
