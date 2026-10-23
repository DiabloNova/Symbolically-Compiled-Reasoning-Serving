# LegalBench — Abercrombie task (test split)

**Licence:** CC BY 4.0.  
**Official task page:** https://hazyresearch.stanford.edu/legalbench/tasks/abercrombie.html  
**Dataset project:** https://github.com/HazyResearch/legalbench  
**Research paper:** Guha et al. (2023), *LegalBench: A Collaboratively Built Benchmark for Measuring Legal Reasoning in Large Language Models*, https://arxiv.org/abs/2308.11462

## Attribution

LegalBench task `abercrombie`, source: Neel Guha / LegalBench, licensed under the Creative Commons Attribution 4.0 International licence. Please cite the LegalBench paper and linked task page. See https://creativecommons.org/licenses/by/4.0/.

## Provenance

The files in this directory were retrieved from the official Hugging Face LegalBench dataset at the immutable revision recorded in `test.run-manifest.json`. The manifest records the original TSV URL, SHA-256 hashes, row count, revision, timestamp, and attribution.

- `test.tsv`: upstream TSV copy.
- `test.jsonl`: deterministic normalized representation. The upstream TSV parser converts `index` to an integer and otherwise preserves the `answer` and `text` fields; this is a format transformation, not a new annotation.
- `test.run-manifest.json`: acquisition metadata and integrity hashes.

Observed test split: 95 rows. The actual observed count, rather than a hard-coded expected count, is recorded. This directory contains source benchmark data only; it includes no SCRS predictions and no empirical SCRS performance claim.

To reproduce the download and generate a fresh run manifest from the current upstream revision:

```bash
python scripts/data/acquire_public_evidence.py --task abercrombie --split test
```

The generated revision and hashes may change if the upstream dataset head changes. For exact reproduction of this checked-in snapshot, use `upstream_revision` and `upstream_source_url` in the checked-in run manifest.
