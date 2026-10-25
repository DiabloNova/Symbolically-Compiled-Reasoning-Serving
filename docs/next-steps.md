# Next steps, ordered by evidence dependency

## 1. Runtime/client source audit — blocked by missing source

The repository inventory on 2026-10-25 confirmed that the default branch contains the manuscript, analytical scripts, public-data tooling, telemetry templates/schema, and an abstract cross-domain gate reference model, but no SCRS runtime implementation or Anchor transport-client source. Consequently, retries, batching, cancellation, provider-generation counts, and provider billing cannot be established from this repository. This is a source-availability blocker, not evidence that those features do or do not occur. Obtain the actual implementation repository/path and anonymized request-linked provider traces before making transport-level claims.

## 2. Offline telemetry contract validation — added, locally tested

Added telemetry/validate_telemetry.py, a standard-library CSV validator for request/event consistency, and tests/test_telemetry_validation.py. Its reference suite has 17 passing tests for no-interrupt fast path, multiple interrupts, retry/attempt separation, unknown timeout outcomes, admission miss with fallback, halt followed by fallback, replay deduplication, conflicting event IDs, unavailable billing, counter mismatches, unknown-state reason codes, orphan events, full schema-header checks, and terminal-regime/fallback invariants. These are contract fixtures, not production traces or measured SCRS results. The repository has no checked-in GitHub Actions workflow, so this pass is local rather than CI evidence.

## 3. Instrument the actual runtime and transport boundaries

Once the implementation source is available, instrument (a) the runtime boundary for accepted logical interrupts and initiated full fallbacks, and (b) the transport/provider boundary for actual attempts, retries, confirmed generations, returned tokens, and provider-billed tokens. Keep attempt outcomes unknown when a timeout does not establish provider completion; do not convert unavailable billing or generation evidence to zero.

## 4. Validate real, request-linked telemetry

Run the offline validator against captured request-level and event-level CSV exports. Independently reconcile provider-request IDs and billing exports. Preserve missingness/conflict rates, exclude conflicting event IDs from aggregation, and publish the exact request denominator plus configuration/software versions. Do not fit the latency model or report cost projections from synthetic fixtures.

## 5. Bind the cross-domain gate contract to implementation

Map each abstract gate field to the actual schema/validator, then run the adversarial and independently labelled cross-domain/stale-evidence tests through the real execution path. The existing 26-test suite validates only the abstract reference model; it does not estimate production false-transfer rates.

## 6. Finish cost and performance validation

Only baseline and Tier I-only token-based costs are currently reproducible under declared prices. Rows 3–8 remain NR until route-wise billed Oracle input means and stable-prefix/uncached-suffix counts are specified. The P50/P95 latency values are synthetic Monte Carlo output, not observations; fit and validate assumptions against request-level traces before using them as evidence.

## 7. Run the preregistered evaluation

The checked-in data assets provide evaluation inputs/gold data, but the repository has no verified SCRS execution path and no predictions from a completed benchmark run. After an implementation is made available, execute baseline and SCRS with pinned model versions; measure answer quality, request-level latency/cost, retries, cache hit rate, fallback, and confidence intervals. Keep synthetic scenario results separate.

## 8. Synchronize the manuscript artifact

The corrected DOCX produced from a clean user-supplied copy was supplied separately. The older tracked manuscript DOCX remains historical; it needs a binary-capable replacement workflow before becoming canonical in the repository.

## 9. Update claims only when evidence arrives

Do not reintroduce the former 631/369 output-token values, unsupported 69.9%/78.3% savings, or 70%/93% headline claims without a valid formula and sufficient measured/model inputs. Table 3 remains design hypotheses until validated.
