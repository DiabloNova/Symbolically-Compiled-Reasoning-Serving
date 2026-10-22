# Replacement draft — Appendix A.3

## A.3 Derivation of expected usage and latency

Define successful fast-path completion (R_1), bailout after partial local execution (R_2), and miss (R_3). Their probabilities are

\[
P(R_1)=p_{hit}(1-p_{halt}),\quad P(R_2)=p_{hit}p_{halt},\quad P(R_3)=1-p_{hit},
\]

where (p_{halt}) is conditional on admission. These mutually exclusive probabilities sum to one.

By the law of total expectation,
\[
E[N_{Or,out}]=P(R_1)E[N_{anchor}|R_1]+P(R_2)E[N_{CoT}|R_2]+P(R_3)E[N_{CoT}|R_3].
\]
If the two fallback conditional means are equal, this reduces to
\[
E[N_{Or,out}]=(1-\alpha_{eff})\bar N_{CoT}+\alpha_{eff}\bar N_{anchor},
\quad \alpha_{eff}=P(R_1).
\]
Do not use this simplified form when bailout and miss requests have materially different conditional output lengths.

The same decomposition applies to input tokens, API attempts, and monetary cost. A logical Anchor event, an HTTP attempt, and a provider-billed generation are distinct observables.

Expected latency is the regime-weighted sum of conditional end-to-end latency, with each conditional duration defined over the actual critical path. When operations overlap, calculate elapsed time from event timestamps rather than adding all component durations. Expectations do not determine P50/P95; percentiles require trace data or a fully specified simulation.
