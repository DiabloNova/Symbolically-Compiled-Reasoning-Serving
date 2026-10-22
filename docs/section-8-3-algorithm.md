# Replacement draft — Section 8.3: Execution pipeline

The request path has four conceptual stages: (1) evaluate admission and retrieve a compatible compiled reasoning artifact; (2) execute the deterministic local reasoning path; (3) render the answer locally, recording each logical Anchor interrupt and its remote work; and (4) either complete the fast path or enter full Oracle fallback after a miss or halt. The algorithm must not infer transport-level events from a logical method call.

## Counter contract

The following counters have distinct units and scopes. They are request-scoped and initialized to zero before the first stage:

- `anchor_interrupt_count`: number of logical interrupt events raised by the local runtime. Increment exactly once when an interrupt condition is accepted and the runtime commits to requesting Anchor support. Do not increment for every token considered or every retry.
- `anchor_transport_attempt_count`: number of transport attempts initiated for Anchor requests, including retries. Increment at the transport boundary for each attempt.
- `anchor_provider_generation_count`: number of provider generations confirmed by provider response or billing evidence. A timed-out attempt with unknown provider outcome must be recorded as unknown, not silently counted as zero.
- `anchor_tokens_returned`: tokens present in successful Anchor responses, using the declared tokenizer and counting rule.
- `anchor_tokens_billed`: tokens the provider reports as billable. Keep this separate from returned tokens because retries, failed responses, minimum billing, or provider accounting may make them differ.
- `full_oracle_fallback_count`: number of full-reasoning fallback operations initiated for the request. A fallback is caused by a miss or a halted execution; it is not an Anchor interrupt.
- `full_oracle_transport_attempt_count` and `full_oracle_provider_generation_count`: transport attempts and confirmed provider generations for full-reasoning fallback, tracked separately from Anchor support.

A logical interrupt, transport attempt, provider generation, and token are different units. Their counts are not assumed to be equal. The algorithm can define and increment logical events exactly; actual provider generations and billed tokens require provider-side evidence and must be marked unknown when that evidence is unavailable.

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
                    record provider generation evidence, returned tokens,
                    and provider-billed tokens separately
                    append returned Anchor text to the answer
                on error:
                    record error and whether provider outcome is known;
                    apply the declared retry/fallback policy
                update cooldown state
            else:
                append the local token

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

This is a counter contract, not a claim that a reference implementation or production trace already exists. The client instrumentation must be implemented at the actual transport boundary to count retries accurately.

## Replacement for `oracleCallsAvoided`

Remove `oracleCallsAvoided = (n_int == 0)`. It is invalid because the source pseudocode never increments `n_int`, and because zero Anchor interrupts does not rule out full Oracle fallback. Also, Anchor support itself may call the Oracle, so the unqualified phrase “Oracle calls avoided” is ambiguous.

For requests that terminate successfully on the fast path, report `full_oracle_fallback_avoided = true` only when `full_oracle_fallback_count == 0`. Report the actual Anchor transport attempts and provider generations separately. For fallback requests, set `full_oracle_fallback_avoided = false`. If the terminal regime or fallback outcome is unknown, report the metric as unknown rather than coercing it to a boolean. This metric means only that full-reasoning fallback was avoided; it does not mean that all Oracle traffic was avoided.

## Required validation cases

1. Fast path with no interrupts: interrupt and Anchor-attempt counts are zero; full fallback count is zero; fallback avoided is true.
2. Fast path with one interrupt and one successful attempt: one logical interrupt, one transport attempt, and provider/token counts taken from the response and billing evidence.
3. Fast path with multiple interrupts: each accepted interrupt increments the logical counter once; attempts and tokens accumulate independently.
4. Retry after transport failure: one logical interrupt but multiple transport attempts; provider generation count follows evidence, not attempt count.
5. Timeout with unknown provider outcome: attempt is counted; provider generation/billing is unknown until evidence resolves it.
6. Miss without any Anchor interrupt: full fallback is counted and fallback-avoided is false.
7. Halt after one or more Anchor events: Anchor counters retain their accumulated values and full fallback is also counted.
8. Empty or failed Anchor response: interrupt and attempt events remain visible; returned and billed token counts follow observed evidence and may differ.
9. Duplicate delivery or callback: event identifiers prevent a single logical event from being counted twice.
10. All request paths: every emitted counter has a documented unit, scope, and source of evidence; no unknown value is silently represented as zero.

The pseudocode in the original manuscript used `n_int` for an interrupt counter but did not increment it. The replacement uses explicit names and a documented event boundary to remove that ambiguity.
