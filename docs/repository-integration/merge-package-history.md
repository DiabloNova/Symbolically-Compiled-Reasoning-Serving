# SCRS merge-package archive and current repository state

This document replaces the obsolete `zip/README_MERGE_INSTRUCTIONS.md` package note. The package has been decomposed into canonical paths; the `zip/` directory is no longer the working location for these artifacts.

## Relocated files

- `patches/0001-*.patch` through `patches/0019-*.patch` preserve the ordered historical patch series, including the R2 and R3 review-fix patches.
- `patches/SCRS_merged_main_vs_origin.patch` is a concatenated historical patch retained for auditability. Do not apply it to current `main`.
- `artifacts/repository-bundles/SCRS_repo_merged.bundle` is a historical Git bundle created before the final GitHub merge sequence. It is not a canonical representation of current `main` and must not be pushed over `main`.
- `manuscripts/SCRS_Manuscript.docx` and `manuscripts/SCRS_Manuscript_Farsi.docx` are the English and Persian manuscript artifacts from the package.
- `experiments/cross_domain_safety/evidence/gate_test_evidence.txt` preserves the supplied historical test log.
- `experiments/cross_domain_safety/gate.py`, `test_gate.py`, and `fixtures.json` remain the canonical executable safety gate and manifest. The duplicate copies formerly in `zip/` were byte-for-byte identical and have been removed rather than maintaining two sources of truth.

## Merge record

- PR #2 (R2 counter and telemetry contract) was merged first. Review follow-up commit: `f2b8d07733b12abc0c61df0deeeda84711da288e`; merge commit: `5c5e6cacd9515d94a202f281b7d974b9d7dcdbd1`.
- PR #3 (R3 cross-domain safety contract) was merged second after synchronizing its branch with the updated `main`. Review follow-up commit: `637c9e8bf40e1ebd35477cd36c0e00e6ef2c0b93`; merge commit: `f721efd6f9ff91e32f1d701ed11872c1602ff0c6`.
- PR #4 (free public evidence acquisition pipeline) was merged before this sequence.

## Validation and evidence boundary

The executable reference-model suite passed 26/26 tests after the R3 branch was synchronized. The safety fixture manifest and telemetry schema parsed as valid JSON, and `git diff --check` passed for the R3 changes. These tests validate the reference model and manifest conformance; they are not production SCRS integration tests and do not establish an empirical end-to-end cross-domain error rate. Synthetic latency/cost outputs must not be described as production measurements.

## Reproduce the safety-gate checks

```bash
python3 -m unittest discover -s experiments/cross_domain_safety -p 'test_gate.py' -v
python3 -m json.tool experiments/cross_domain_safety/fixtures.json
python3 -m json.tool telemetry/telemetry-schema.json
```
