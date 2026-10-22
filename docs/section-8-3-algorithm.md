# Replacement draft — Section 8.3: Execution pipeline

The request path has four conceptual stages: (1) evaluate admission and retrieve a compatible compiled reasoning artifact; (2) execute the local reasoning path while recording the active-generation interval; (3) if a halt/interrupt condition fires, record the event and request Anchor support; and (4) either resume the local path or enter the declared Oracle fallback path.

Implementation and evaluation must distinguish the following counters:
- `anchor_interrupt_count`: logical interrupt events raised by the local runtime;
- `anchor_api_attempt_count`: transport attempts, including retries;
- `anchor_provider_generation_count`: provider-billed generations, where observable;
- `anchor_tokens_total`: returned or billed Anchor tokens, with the token definition stated;
- `oracle_fallback_count`: requests that invoke full reasoning after bailout or miss.

The supplied Algorithm 1 initializes `n_int = 0` but does not increment it on interrupt. Consequently, `oracleCallsAvoided = (n_int == 0)` is always true in the pseudocode as provided. Increment the counter at the event boundary or compute the metric from independently recorded call events.

The pseudocode's single `Oracle.generateAnchors(...)` invocation per interrupt establishes one logical method invocation in the algorithm. It does not establish exactly one HTTP/API round trip: retries, batching, caching, and transport-layer behavior must be verified in the implementation and traces.

A reproducible evaluation should record start/end timestamps for local generation, halt decision, queueing, Oracle time-to-first-token, per-token generation time, Anchor response, and fallback. Do not infer these intervals from total latency alone.
