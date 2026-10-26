# Decision-semantic preservation: conditional sufficiency and a risk bound

**Status:** formal replacement specification for the Tier I information-preservation claim. This document defines a task-relative mathematical property and a validation protocol. It is not evidence that a particular extractor, capsule, or SCRS implementation satisfies the property, and it does not replace the historical manuscript binary.

## 1. Problem with an unqualified information-preservation claim

An expression such as
\[
I(A(Q);D_{\mathrm{raw}})-I(A(Q);K(D_{\mathrm{raw}}))\leq\varepsilon
\]
is not yet an operational invariant. It leaves the reference answer/decision variable, the query-conditioned population, the target task, and the estimation procedure underspecified. In particular, unconditional mutual information can mix information about which queries occur with information needed to decide correctly for a fixed query.

The relevant question is not whether a capsule preserves all information in a source document. Any useful compression usually discards information. The question is whether it discards information needed for a **declared target decision, under a declared query distribution and loss function**.

## 2. Probability model and notation

Let \((Q,D,Y)\sim P\) be a joint distribution over:

- \(Q\): a query or task instance;
- \(D\): the original context available to the full-context procedure;
- \(Y\): an authoritative target outcome, such as a gold decision label or a structured decision state containing the facts, conditions, and exceptions relevant to that task.

Let \(K=E_v(D)\) be the capsule emitted by a fixed, versioned encoder \(E_v\). For a query-conditioned encoder, the same results apply to \(K=E_v(Q,D)\). In either case, \(K\) is generated from the available input and does not receive privileged access to \(Y\). The target distribution \(P\), the encoder version \(v\), the support of \(Q\), and the schema for \(Y\) are part of the claim. Changing any of them changes the property being evaluated.

For clarity, assume \(Y\) has a finite outcome space \(\mathcal Y\), and use natural logarithms so information is measured in nats. Define the two posterior distributions
\[
p_D(y\mid q,d)=P(Y=y\mid Q=q,D=d)
\]
and
\[
p_K(y\mid q,k)=P(Y=y\mid Q=q,K=k).
\]

The second posterior averages over any original contexts that map to the same capsule under the same query. Thus it makes explicit what a capsule leaves uncertain about the target outcome.

## 3. Decision-relevant information loss

Define the **conditional decision-information loss** of the encoder on \(P\) as
\[
\Delta_{\mathrm{DS}}(P,E_v)
:= I(Y;D\mid Q,K).
\]

Because \(K\) is a function of \(D\) (or of \((Q,D)\)), the chain rule for mutual information gives
\[
\begin{aligned}
I(Y;D\mid Q)
&= I(Y;K\mid Q)+I(Y;D\mid Q,K),\\
\therefore\quad
\Delta_{\mathrm{DS}}
&= I(Y;D\mid Q)-I(Y;K\mid Q)\\
&= \mathbb E_{Q,D}\!\left[
D_{\mathrm{KL}}\!\left(
p_D(\cdot\mid Q,D)\,\Vert\,
p_K(\cdot\mid Q,K)
\right)\right]\geq 0.
\end{aligned}
\]

The last equality is the standard conditional-mutual-information / expected-conditional-KL identity. The non-negativity follows from the non-negativity of KL divergence. It is an exact identity under the stated model, not an empirical result about SCRS.

The zero-loss condition is
\[
\Delta_{\mathrm{DS}}=0
\quad\Longleftrightarrow\quad
Y\perp D\mid(Q,K)
\quad\Longleftrightarrow\quad
p_D(\cdot\mid Q,D)=p_K(\cdot\mid Q,K)\ \ P\text{-almost surely}.
\]

This defines **target-specific statistical sufficiency**: after the query and capsule are known, the discarded remainder of the original context provides no additional information about the declared outcome \(Y\).

### Deterministic gold outcomes

If the reference outcome is deterministic given the full query-context pair, \(Y=g(Q,D)\), then \(H(Y\mid Q,D)=0\). For finite \(Y\),
\[
\Delta_{\mathrm{DS}}=H(Y\mid Q,K).
\]
In this special case, exact preservation is equivalent to \(H(Y\mid Q,K)=0\): the target outcome is reconstructible from the query and capsule almost surely.

This special case must not be silently assumed when the gold outcome is genuinely ambiguous or is itself generated under a stochastic adjudication process. In those settings, use the posterior/KL definition.

## 4. Proposition: exact preservation of Bayes decisions

Let \(\mathcal A\) be an action set and let \(\ell:\mathcal A\times\mathcal Y\to[0,1]\) be a declared bounded loss. Define the optimal risks with access to the full context and the capsule as
\[
R_D^*=\inf_{\delta_D}
\mathbb E[\ell(\delta_D(Q,D),Y)]
\]
and
\[
R_K^*=\inf_{\delta_K}
\mathbb E[\ell(\delta_K(Q,K),Y)],
\]
where the infima are over measurable decision rules with the indicated information.

**Proposition 1 (decision sufficiency).** If \(\Delta_{\mathrm{DS}}=0\), then
\[
R_K^*=R_D^*
\]
for every loss function of the stated form.

**Proof.** Since \(K\) is computed from the available input, a rule that observes \((Q,K)\) can be implemented by a rule that observes \((Q,D)\). Therefore \(R_D^*\leq R_K^*\). If \(\Delta_{\mathrm{DS}}=0\), the conditional distributions \(p_D\) and \(p_K\) are equal almost surely. Consequently, for every action \(a\), its conditional expected loss given \((Q,D)\) equals its conditional expected loss given \((Q,K)\) almost surely. Their infima over \(a\), and hence their expectations, are equal. Thus \(R_D^*=R_K^*\). \(\square\)

**Scope.** Proposition 1 applies to decision rules and losses that use the declared target \(Y\). It does not prove preservation of every fact, every possible future task, or every unstated interpretation of \(D\). If multiple downstream decisions matter, \(Y\) must represent the relevant structured state or each target must be assessed separately. A gate's transfer-safety property is a separate claim and is not implied by this proposition.

## 5. Proposition: an approximate information-loss bound

**Proposition 2 (Bayes-risk degradation bound).** Under the same finite-outcome assumptions and any loss \(\ell\in[0,1]\),
\[
0\leq R_K^*-R_D^*
\leq
\mathbb E[\operatorname{TV}(p_D,p_K)]
\leq
\sqrt{\frac{\Delta_{\mathrm{DS}}}{2}},
\]
where \(\operatorname{TV}(p,q)=\tfrac12\sum_y|p(y)-q(y)|\), KL divergence and mutual information use natural logarithms, and the expectation is over the declared population \(P\).

**Proof.** For probability vectors \(p,q\) on \(\mathcal Y\), boundedness of the loss implies that the difference between the minimum expected losses under \(p\) and under \(q\) is at most \(\operatorname{TV}(p,q)\). Apply this pointwise to \(p_D\) and \(p_K\), then average over \((Q,D)\). Since \(K\) is a function of the available input, full-context access cannot have greater Bayes risk, giving the lower bound. Pinsker's inequality, with KL measured in nats, gives
\[
\operatorname{TV}(p_D,p_K)
\leq
\sqrt{\tfrac12D_{\mathrm{KL}}(p_D\Vert p_K)}.
\]
Taking expectations and applying Jensen's inequality to the square root yields the upper bound because the expected KL term is \(\Delta_{\mathrm{DS}}\). \(\square\)

The bound is a theoretical relation, not a claim that \(\Delta_{\mathrm{DS}}\) has been measured for SCRS. It can be loose. It also only holds relative to the specified \(P\), target variable \(Y\), and loss range. It does not give a distribution-free guarantee for arbitrary unseen queries or domains.

## 6. Small exact examples

These examples illustrate the scope of the criterion; they are not experiments on SCRS.

**Discarding irrelevant detail.** Let \(Q\) be constant, \(D=(C,N)\), \(Y=C\), and let \(C,N\) be independent. If \(K=C\), then \(Y\) is completely determined by \(K\), so \(\Delta_{\mathrm{DS}}=0\). The capsule may discard \(N\) without harming any Bayes decision whose outcome depends only on \(Y=C\).

**Discarding the decisive fact.** Let \(C\) be a fair binary variable, let \(N\) be independent, let \(D=(C,N)\), \(Y=C\), but let \(K=N\). Then \(\Delta_{\mathrm{DS}}=H(C)=\ln 2\) nats. Under zero-one loss, full-context Bayes risk is \(0\), while the capsule-only Bayes risk is \(1/2\). The bound gives \(1/2\leq\sqrt{\ln 2/2}\), as required. Retaining text volume or surface similarity is not sufficient if the decisive variable has been discarded.

## 7. What the theorem does—and does not—establish

1. **It formalizes a task-relative invariant.** The target \(Y\), query population \(P\), encoder version, and loss must be declared before the claim can be evaluated.
2. **It is not a compression-ratio guarantee.** Token reduction \(\rho\), embedding similarity, and \(\Delta_{\mathrm{DS}}\) are different quantities. Neither a high compression ratio nor a high similarity score implies zero decision-information loss.
3. **It is not an extraction-correctness theorem.** The target schema may itself omit an important exception or condition. If \(Y\) is underspecified, the theorem can hold for an inadequate target.
4. **It is not an end-to-end SCRS guarantee.** It says nothing by itself about domain extraction, compatibility-gate correctness, execution correctness, rendering fidelity, model hallucination, or transport failures.
5. **It is population-relative.** A guarantee for one declared task/query distribution does not automatically generalize to new domains, changed policies, or future task families.
6. **An empirical zero is not a proof of population zero.** A finite test set can establish only the recorded results under its sampling and labeling protocol.

## 8. Operational validation protocol

A future evaluation should be preregistered for each task separately.

1. **Specify the target.** Define \(Y\) as an authoritative label or structured decision state, including the decision-relevant facts, conditions, and exceptions. Publish the annotation/adjudication rules and identify ambiguities before inspecting model results.
2. **Specify the population.** Pin the query set, source-context version, domain scope, inclusion/exclusion rules, and encoder/compiler versions. Do not pool unlike tasks into an unqualified average.
3. **Run paired conditions.** For the same \((Q,D)\), compare the original-context path with the capsule path using the same declared model version and compatible decoding/scoring settings. Report gold-label accuracy/loss for each path and paired outcome disagreement separately. Matching two model outputs is not itself proof that either output is correct.
4. **Measure critical content separately.** For domains where exceptions or prerequisites alter a decision, score their retention explicitly instead of relying on generic semantic similarity.
5. **Estimate information loss only with a defensible estimator.** Estimating \(I(Y;D\mid Q,K)\) requires support to estimate conditional outcome distributions. When each query-context pair occurs only once, do not claim a direct empirical estimate from the gold label alone. If using a probabilistic estimator, document its training/held-out split, calibration, estimator bias, confidence procedure, and failure modes. A paired test-set agreement rate is a useful proxy, but is not the same quantity as conditional mutual information.
6. **Report uncertainty and scope.** Give task-level numerators/denominators, confidence intervals appropriate to the sampling design, missing-label counts, extraction errors, and false-reject/false-accept cases where applicable. Label fixed adversarial suites as finite-set tests rather than population estimates.

Until the registered protocol is run with the required labels and a pinned execution path, \(\Delta_{\mathrm{DS}}\), decision-risk degradation, and semantic-preservation accuracy must remain **unmeasured**. The theorem establishes what would follow if the stated conditions hold; it does not establish that they hold for current SCRS artifacts.

## References

- Blackwell, D. (1953). “Equivalent Comparisons of Experiments.” *The Annals of Mathematical Statistics*, 24(2), 265–272. https://doi.org/10.1214/aoms/1177729032
- Cover, T. M., & Thomas, J. A. (2006). *Elements of Information Theory* (2nd ed.). Wiley. https://doi.org/10.1002/047174882X

Blackwell provides the classical decision-theoretic context for comparing information-bearing experiments. The conditional mutual-information identity and Pinsker inequality used above are standard information-theoretic results. The SCRS-specific contribution here is the explicit task-relative contract and its evidence boundary, not a claim to have invented these inequalities.
