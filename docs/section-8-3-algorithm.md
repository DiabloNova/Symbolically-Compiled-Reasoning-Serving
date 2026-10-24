# Replacement draft — Section 8.3: Execution pipeline

The request path has four conceptual stages: (1) evaluate admission and retrieve a compatible compiled reasoning artifact; (2) execute the deterministic local reasoning path; (3) render the answer locally, recording each logical Anchor interrupt and its remote work; and (4) either complete the fast path or enter full Oracle fallback after a miss or halt. The algorithm must not infer transport-level events from a logical method call.

## Counter contract

The following counters have distinct units and scopes. They are request-scoped and initialized to zero before the first stage:

- `anchor_interrupt_count`: number of logical interrupt events raised by the local runtime. Increment exactly once when an interrupt condition is accepted and the runtime commits to requesting Anchor support. Do not increment for every token considered or every retry.
- `anchor_transport_attempt_count`: number of transport attempts initiated for Anchor requests, including retries. Increment at the transport boundary for each attempt.
- `anchor_provider_generation_count` and `anchor_provider_generation_evidence`: a **tri-state** observation. `anchor_provider_generation_evidence` is one of `CONFIRMED`, `UNKNOWN` (with a mandatory reason code such as `TIMEOUT_OUTCOME_UNKNOWN`, `TRANSPORT_ERROR`, or `PROVIDER_RESPONSE_MALFORMED`), or `UNAVAILABLE` (with a mandatory reason code such as `BILLING_FEED_MISSING`). `anchor_provider_generation_count` is incremented **only** in the `CONFIRMED` state; it is never advanced when the state is `UNKNOWN` or `UNAVAILABLE`. A timed-out attempt with unknown provider outcome must leave the evidence state `UNKNOWN`, not silently advance or reset the count to zero. The request summary must report the evidence state alongside the count, so a zero can never stand in for an unresolved or unavailable observation.
- `anchor_tokens_returned`: tokens present in successful Anchor responses, using the declared tokenizer and counting rule.
- `anchor_tokens_billed`: tokens the provider reports as billable. Keep this separate from returned tokens because retries, failed responses, minimum billing, or provider accounting may make them differ. When no billing feed is available for a confirmed generation, record `anchor_tokens_billed` as `UNAVAILABLE` (reason `BILLING_FEED_MISSING`) for that generation rather than as zero.
- `full_oracle_fallback_count`: number of full-reasoning fallback operations initiated for the request. A fallback is caused by a miss or a halted execution; it is not an Anchor interrupt.
- `full_oracle_transport_attempt_count` and `full_oracle_provider_generation_count`: transport attempts and confirmed provider generations for full-reasoning fallback, tracked separately from Anchor support.

A logical interrupt, transport attempt, provider generation, and token are different units. Their counts are not assumed to be equal. The algorithm can define and increment logical events exactly; actual provider generations and billed tokens require provider-side evidence and must be marked unknown when that evidence is unavailable.

### Counter boundaries

Two distinct instrumentation boundaries are involved, and every counter belongs to exactly one of them:

- **Runtime-event boundary (inside the local runtime):** `anchor_interrupt_count`, `full_oracle_fallback_count`. These are logical events the runtime raises; they are incremented exactly once per accepted event, independently of transport behavior.
- **Transport boundary (inside the instrumented client):** `anchor_transport_attempt_count`, `anchor_provider_generation_count`/`anchor_provider_generation_evidence`, `anchor_tokens_returned`, `anchor_tokens_billed`, `full_oracle_transport_attempt_count`, `full_oracle_provider_generation_count`. These are incremented only where HTTP/API requests are actually issued or provider responses/billing evidence is reconciled.

### Event identity and deduplication

An event identifier alone does not prevent duplicate counting: a replayed callback or at-least-once delivery would otherwise duplicate records. The following deduplication rule is mandatory:

1. Every event carries a stable `event_id` derived from `(request_id_hash, causal_interrupt_seq, attempt_number, event_type)`.
2. The ingestion layer deduplicates by `event_id` **before** any aggregation: the first occurrence is stored, later occurrences with an identical payload are recorded as replay marks and never re-counted.
3. If a later occurrence carries a conflicting payload, it is retained with a `conflict` flag and surfaced in the missing-data/conflict report; it does not update counters.
4. Counters in Algorithm 1 are advanced by the runtime state machine at the increment points defined below; ingestion replay therefore cannot inflate them.

## Corrected Algorithm 1 counter semantics

```text
Initialize all request counters to 0.
Initialize terminal_regime = UNSET.

On an admitted, validated candidate:
    Execute deterministic reasoning.
    If execution halts:
        terminal_regime = FALLBACK
        increment full_oracle_fallback_count when full fallback is initiated
        invoke full Oracle fallback through the instrumented client
        record each transport attempt, confirmed generation, token result,
        and unknown provider outcome separately
        emit request and event telemetry
        return fallback answer and telemetry

    Otherwise:
        while local rendering has not reached EOS:
            obtain the next local token and compute the interrupt predicate
            if interrupt predicate is true and cooldown permits:
                increment anchor_interrupt_count exactly once
                call the instrumented Anchor client
                for each actual transport attempt:
                    increment anchor_transport_attempt_count
                    emit an attempt event with outcome and retry metadata
                on confirmed provider response:
                    increment anchor_provider_generation_count by 1
                    set anchor_provider_generation_evidence = CONFIRMED
                    add returned tokens to anchor_tokens_returned
                    add provider-billed tokens to anchor_tokens_billed;
                        if no billing feed covers this generation,
                        mark that generation's billing as UNAVAILABLE
                        (reason BILLING_FEED_MISSING) instead of zero
                    append returned Anchor text to the answer
                on timeout or error:
                    do NOT increment anchor_provider_generation_count;
                    set anchor_provider_generation_evidence = UNKNOWN with the
                        reason code (TIMEOUT_OUTCOME_UNKNOWN or TRANSPORT_ERROR);
                    leave billing for this attempt UNKNOWN pending reconciliation;
                    record the error and whether the provider outcome is known;
                    apply the declared retry/fallback policy
                update cooldown state

                if the retry/fallback policy now declares a mid-render halt
                or fallback (for example: Anchor unrecoverable, render
                mismatch, or max-token cap reached):
                    terminal_regime = FALLBACK
                    increment full_oracle_fallback_count when full fallback
                        is initiated
                    invoke full Oracle fallback through the instrumented
                        client; record attempts, confirmed generations,
                        token counts, and unknown outcomes as above
                    retain all accumulated Anchor counter values
                    emit request and event telemetry
                    return the fallback answer and telemetry
            else:
                append the local token

        # reached EOS without any declared mid-render fallback
        terminal_regime = FAST_PATH
        emit request and event telemetry
        return answer and telemetry

On retrieval/admission miss:
    terminal_regime = FALLBACK
    increment full_oracle_fallback_count when full fallback is initiated
    invoke the instrumented full Oracle client and record attempts,
    confirmed generations, token counts, and unknown outcomes
    emit request and event telemetry
    return fallback answer and telemetry
```

This is a counter contract, not a claim that a reference implementation or production trace already exists. The client instrumentation must be implemented at the actual transport boundary to count retries accurately. `terminal_regime = FAST_PATH` is assigned **only** when rendering reaches EOS without a declared mid-render halt or fallback; every other exit path from the rendering loop must pass through the mid-render fallback branch above, so a request that fell back after one or more Anchor interrupts is always reported as `FALLBACK` with a non-zero `full_oracle_fallback_count` and is never summarized as a fast-path success.

## Replacement for `oracleCallsAvoided`

Remove `oracleCallsAvoided = (n_int == 0)`. It is invalid because the source pseudocode never increments `n_int`, and because zero Anchor interrupts does not rule out full Oracle fallback. Also, Anchor support itself may call the Oracle, so the unqualified phrase “Oracle calls avoided” is ambiguous.

For requests that terminate successfully on the fast path, report `full_oracle_fallback_avoided = true` only when `full_oracle_fallback_count == 0`. Report the actual Anchor transport attempts and provider generations separately. For fallback requests, set `full_oracle_fallback_avoided = false`. If the terminal regime or fallback outcome is unknown, report the metric as unknown rather than coercing it to a boolean. This metric means only that full-reasoning fallback was avoided; it does not mean that all Oracle traffic was avoided.

## Required validation cases

1. Fast path with no interrupts: interrupt and Anchor-attempt counts are zero; full fallback count is zero; fallback avoided is true.
2. Fast path with one interrupt and one successful attempt: one logical interrupt, one transport attempt, and provider/token counts taken from the response and billing evidence.
3. Fast path with multiple interrupts: each accepted interrupt increments the logical counter once; attempts and tokens accumulate independently.
4. Retry after transport failure: one logical interrupt but multiple transport attempts; provider generation count follows evidence, not attempt count.
5. Timeout with unknown provider outcome: attempt is counted; provider generation count is NOT incremented and the evidence state is `UNKNOWN` (reason `TIMEOUT_OUTCOME_UNKNOWN`) until evidence resolves it; billing for the attempt is `UNKNOWN`, not zero.
6. Miss without any Anchor interrupt: full fallback is counted and fallback-avoided is false.
7. Halt after one or more Anchor events: Anchor counters retain their accumulated values and full fallback is also counted.
7a. Mid-render policy fallback (Anchor unrecoverable, render mismatch, or max-token cap after one or more interrupts): `terminal_regime = FALLBACK`, `full_oracle_fallback_count >= 1`, accumulated Anchor counters retained, and the request is never summarized as fast-path success.
8. Empty or failed Anchor response: interrupt and attempt events remain visible; returned and billed token counts follow observed evidence and may differ.
9. Duplicate delivery or callback: ingestion deduplicates by the stable `event_id`; identical replays are marked and never re-counted; conflicting payloads are flagged and surfaced. The request-level counters are unchanged by replay.
10. All request paths: every emitted counter has a documented unit, scope, and source of evidence; no unknown value is silently represented as zero.
11. Missing billing feed: provider generation is `CONFIRMED` but billing is `UNAVAILABLE` (reason `BILLING_FEED_MISSING`); the returned-token count is still reported, and the billed-token summary carries the unavailable marker rather than a zero.

The pseudocode in the original manuscript used `n_int` for an interrupt counter but did not increment it. The replacement uses explicit names and a documented event boundary to remove that ambiguity.
