# Cross-domain safety reference tests

## Purpose and limitation

This folder provides an executable, standard-library Python reference model for the **abstract acceptance contract** in `docs/section-5-cross-domain-safety.md`. It makes the fail-closed rule concrete and supplies deterministic conformance/adversarial tests.

It is **not** the SCRS production implementation and does not validate real domain extraction, canonicalization, compatibility-policy completeness, signatures, or bypass resistance in a deployed pipeline. The booleans `request_validated`, `capsule_validated`, and `provenance_valid` are trusted inputs to this reference model; production code must connect them to real verification mechanisms.

## Requirements

- Python 3.10 or newer
- No third-party dependencies

## Run

From this directory:

```sh
python -m unittest -v
```

Expected outcome: 13 tests pass. The suite includes a compatible control case and incompatible/missing/unknown metadata cases. A passing suite means only that this reference implementation conforms to its own stated predicate; it is not an empirical estimate of the end-to-end SCRS error rate.

## Mapping to production

Before claiming implementation conformance, map each field to the production schema and validation function, then run equivalent tests against the actual gate and record:
- source commit and dependency/runtime versions;
- fixture manifest and expected decision/reason;
- raw per-case outputs;
- counts of incompatible cases, incorrect acceptances, and compatible cases incorrectly rejected;
- an appropriate binomial confidence interval.

Do not report an empirical zero error rate from this reference suite.
