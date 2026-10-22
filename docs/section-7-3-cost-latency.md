# Replacement draft — Section 7.3: Expected usage, cost, and latency

Define three mutually exclusive execution regimes: successful fast-path completion (R_1), bailout after partial local execution (R_2), and a cache/admission miss (R_3). Let (p_{hit}) be the probability of admission to the fast path and (p_{halt}) the conditional probability of a halt after admission. Then

\[
P(R_1)=p_{hit}(1-p_{halt}),\quad P(R_2)=p_{hit}p_{halt},\quad P(R_3)=1-p_{hit}.
\]

These probabilities sum to one; no independence assumption is needed because (p_{halt}) is conditional on admission. Define (alpha_{eff}=P(R_1)).

Let (N_{anchor}) denote billable Anchor output tokens on successful fast-path requests and (N_{CoT}) full-oracle output tokens on fallback requests. The general expected output-token accounting is

\[
E[N_{Or,out}]=P(R_1)E[N_{anchor}|R_1]+P(R_2)E[N_{CoT}|R_2]+P(R_3)E[N_{CoT}|R_3].
\]

Only if the conditional fallback means are equal may this be simplified to
\[
E[N_{Or,out}]=(1-\alpha_{eff})\bar N_{CoT}+\alpha_{eff}\bar N_{anchor}.
\]
The same regime-wise accounting applies to input tokens and API attempts. A logical Anchor event, an HTTP/API attempt, a provider-billed generation, and returned Anchor tokens are distinct quantities and must not share one counter.

Expected monetary cost can be written as
\[
E[C]=c_{in}E[N_{Or,in}]+c_{out}E[N_{Or,out}]+E[C_{local}],
\]
where prices, cached-token treatment, retries, and local-compute amortization must be declared. Without those inputs, published dollar values cannot be independently reproduced.

Expected end-to-end latency is the regime-weighted expectation of conditional end-to-end latency. Each duration must be defined on a non-overlapping critical path; overlapping work must be calculated from timestamps, not by summing component durations. An expected latency does not determine P50 or P95. Percentiles require request-level traces or a fully specified simulation, labelled as such.

**Consistency check:** using the manuscript's baseline Oracle output mean of 2,380 tokens and (alpha_{eff}=0.62), the fallback contribution alone is (0.38\times2380=904.4) tokens before adding any positive Anchor output. A Unified SCRS table value of 894 therefore needs a different explicitly documented conditional fallback mean, a changed (alpha_{eff}), or correction. It is not explained by the simplified equation as currently stated.
