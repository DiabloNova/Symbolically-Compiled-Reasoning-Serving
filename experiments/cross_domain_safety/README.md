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

Expected outcome: 26 tests pass (24 hand-written unit tests + 2 manifest-driven conformance tests). The suite covers:

- a compatible control case;
- request-side **and** capsule-side missing domain / contract-version values;
- equal-but-stale contract versions (version-currency rejection);
- truthy non-boolean status values (e.g. the string `"unknown"`) failing closed for every boolean status;
- canonicalization collision, uncertified, and unsupported mapping versions;
- necessity of every required condition; and
- the checked-in `fixtures.json` manifest, which is loaded by the tests and drives the expected decision/reason for each case.

A passing suite means only that this reference implementation conforms to its own stated predicate; it is not an empirical estimate of the end-to-end SCRS error rate. Policy-derived fixture labels make these conformance results, not end-to-end rates.

## Mapping to production

Before claiming implementation conformance, map each field to the production schema and validation function, then run equivalent tests against the actual gate and record:
- source commit and dependency/runtime versions;
- fixture manifest and expected decision/reason;
- raw per-case outputs;
- counts of incompatible cases, incorrect acceptances, and compatible cases incorrectly rejected;
- an appropriate binomial confidence interval.

Do not report an empirical zero error rate from this reference suite.
