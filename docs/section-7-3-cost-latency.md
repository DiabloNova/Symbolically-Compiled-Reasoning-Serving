# Replacement draft — Section 7.3: Expected usage, cost, and latency (recalculation-v1)

Define three mutually exclusive execution regimes: successful fast-path completion (\(R_1\)), bailout after partial local execution (\(R_2\)), and admission miss (\(R_3\)). Let \(p_{hit}\) be the probability of admission and \(p_{halt}\) the conditional probability of a halt after admission. Then

\[
P(R_1)=p_{hit}(1-p_{halt}),\quad
P(R_2)=p_{hit}p_{halt},\quad
P(R_3)=1-p_{hit}.
\]

With the scenario assumptions \(p_{hit}=0.78\) and \(p_{halt}=0.205\), these give \(P(R_1)=0.6201\), \(P(R_2)=0.1599\), and \(P(R_3)=0.22\), which sum to one. These are assumptions, not measured hit/halt rates.

## Oracle-billed output tokens

The general expected output-token accounting follows the law of total expectation:

\[
E[N_{Or,out}]=P(R_1)E[N_{anchor,out}\mid R_1]
+P(R_2)E[N_{full,out}\mid R_2]
+P(R_3)E[N_{full,out}\mid R_3].
\]

The simplified full-fallback component \((P(R_2)+P(R_3))\bar N_{CoT}\) requires equal conditional fallback output means for bailout and miss. That equality is an explicit scenario assumption in recalculation-v1, not a measured property. For unified SCRS, \(n_{anchor}=1.4\) is the mean number of Anchor calls conditional on a successful fast-path request and \(k=5\) output tokens are assumed per call. Thus the expected Anchor output per all requests is \(0.6201\times1.4\times5=4.3407\) tokens. Using the capsule-context full-fallback mean of 2,310 tokens:

\[
E[N_{Or,out}]=0.3799\times2310+0.6201\times1.4\times5
=881.9097\approx881.9.
\]

For the similarity-only/no-gate ablation, with \(P(\text{hit})=0.78\) and no bailout regime in that ablation:

\[
E[N_{Or,out}]=0.22\times2310+0.78\times1.4\times5
=513.66\approx513.7.
\]

For Tier II with Oracle rendering on the successful path, the 900-token fast-path output is an explicit assumption. Using raw/capsule fallback means of 2,380/2,310 respectively:

\[
E[N_{Or,out}^{raw}]=0.6201\times900+0.3799\times2380=1462.252,
\]
\[
E[N_{Or,out}^{capsule}]=0.6201\times900+0.3799\times2310=1435.659.
\]

Tier III-only output is \(11.5\times5=57.5\) Anchor tokens/request for raw context and \(9.6\times5=48.0\) for Tier I + III. The Anchor counts and fallback means above are scenario assumptions until validated using runtime/provider logs.

## Costs that are currently reproducible

Under the declared tariffs of USD 2.50 per million input tokens and USD 10.00 per million output tokens, per 10,000 requests:

- Baseline: \(6420\times0.025+2380\times0.10=\$398.50\).
- Tier I only: \(1180\times0.025+2310\times0.10=\$260.50\), 34.6% lower than baseline.

Total costs and deltas for configurations 3–8 are marked NR. The manuscript provides total Anchor prompt lengths but not the stable-prefix/uncached-suffix token split needed to apply the provider's \(\beta=0.10\) cached-input factor. Route-specific billed Oracle input lengths are also incomplete for several rows. Reverse-engineering those missing inputs from the legacy dollar values is not valid.

## Latency evidence

The recalculation-v1 script simulates 100,000 requests/configuration with seed 20261025, lognormal marginal distributions, queue/TTFT latent-factor correlation 0.5, Oracle TPOT/request-load latent-factor loading 0.5, and SLM TTFT/TPOT correlation 0.5, using independent residual terms. Oracle service TTFT scales with context length under an assumed 0.30-second floor. The first recalculation attempt imposed accidental perfect correlation and was discarded; the current CSV and manifest come from the corrected correlation model.

P50/P95 are synthetic scenario percentiles, not values derivable from expected-value equations and not measured production latency. The simulation assumes one serial Oracle round trip per logical Anchor call; the actual client path, retries, batching and provider billing remain unverified. If request-level traces become available, the distributions must be fit/validated and the same configurations rerun against measured baselines.
