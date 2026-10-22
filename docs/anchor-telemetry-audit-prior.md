# SCRS Anchor / telemetry audit — source-level findings

## Evidence examined
- The supplied manuscript §6.2 states that when an interrupt fires, local generation pauses and the prefix, capsules, and verified trace are sent to the Oracle, which produces up to (k=5) Anchor tokens.
- Algorithm 1, §8.3, invokes `Oracle.generateAnchors(prompt + Y, max_tokens=k)` once inside each interrupt condition and increments `n_anchor` by the returned token count.
- Algorithm 1 initializes `n_int = 0` but does not increment it in the supplied pseudocode before evaluating `oracleCallsAvoided = (n_int == 0)`.
- §8.4 describes request telemetry at a high level but does not specify per-call queue wait, Oracle TTFT/TPOT, Anchor API attempt count, stop timestamp, active SLM rendering duration excluding pauses, or fallback span timestamps.

## Findings
1. One logical `generateAnchors` method invocation is shown per interrupt in the pseudocode.
2. The actual HTTP/API round-trip count cannot be established from pseudocode alone. Retries, batching, caching, and transport abstractions require implementation and trace inspection.
3. Anchor token count is not call count. Record logical interrupt events, API attempts, provider-billed generations, and tokens independently.
4. The supplied `n_int` metric is defective because it is never incremented in the shown pseudocode.
5. End-to-end elapsed time alone cannot reconstruct queue, TTFT, TPOT, call count, or timing overlap.
6. Scenario v2 assumes serial API round trips and is synthetic, not production telemetry.

## Required next step
Instrument the implementation or provide its repository and anonymized event logs. Record request-linked events with provider request IDs (redacted), queue start/end, first-token time, token count, completion time, retry/cancellation status, SLM active-generation spans, halt time, and fallback spans.
