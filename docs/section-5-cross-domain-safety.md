# Finding 3 — Cross-domain transfer safety: formal contract and reproducible validation protocol

**Scope.** This document addresses only the audit finding that the manuscript's claim of structurally impossible cross-domain transfer / zero incorrect-transfer rate exceeds the evidence currently documented. It is a replacement specification for manuscript sections 5.2–5.3 and the corresponding evaluation protocol; it does not claim that a reference implementation or experiments already exist.

## 1. Corrected claim and terminology

The manuscript must distinguish three statements:

1. **Specification-level rejection property (formal, conditional):** a candidate capsule is rejected when its validated domain identity, compatibility version, required preconditions, or exception policy fails the acceptance predicate.
2. **Implementation conformance (testable):** a particular implementation rejects every test input that violates that predicate and accepts only inputs that satisfy it, subject to the completeness of the test suite.
3. **End-to-end empirical error rate (measured):** the observed rate of incorrect cross-domain acceptance over a specified dataset and protocol.

The first statement does not entail the second or third. A zero observed error count in a finite test set is not proof of a zero population error rate. Until implementation and tests exist, use “designed to reject incompatible cross-domain transfers under the stated assumptions,” not “structurally impossible” or “zero error rate.”

## 2. Acceptance contract

Let a candidate transfer be represented by
\[
x=(d_q,v_q,d_c,v_c,p_q,p_c,e_q,e_c,s_q,s_c),
\]
where:

- \(d_q,d_c\): canonical domain identifiers for the request and capsule;
- \(v_q,v_c\): versions of the domain/compatibility contract;
- \(p_q,p_c\): required preconditions and capsule preconditions;
- \(e_q,e_c\): exception-policy identifiers and versions;
- \(s_q,s_c\): provenance/status metadata, including validation status.

Define the predicate
\[
\operatorname{Accept}(x) =
V_q \land V_c \land
(d_q=d_c) \land (v_q=v_c) \land
\operatorname{PreconditionsCompatible}(p_q,p_c) \land
\operatorname{ExceptionsCompatible}(e_q,e_c) \land
\operatorname{ProvenanceValid}(s_q,s_c).
\]
Here \(V_q\) and \(V_c\) mean that the request-side and capsule-side identifiers and metadata have been successfully validated, not merely parsed or supplied by an untrusted caller. The compatibility functions must be defined by a versioned, deterministic policy; undefined, missing, stale, or unparseable values fail closed.

**Decision rule:** accept only when every required check returns an explicit valid result. Reject on mismatch, missing data, stale contract versions, failed validation, unknown policy result, or exception-policy mismatch. Log the reason code without storing sensitive request content.

This contract is intentionally conservative. It is not a claim that the current manuscript already defines every field or that domain extraction is always correct. The implementation must bind these abstract fields to concrete schemas and canonicalization rules before the theorem can be claimed for the full system.

## 3. Conditional safety proposition

**Proposition (incompatible-transfer rejection).** For any candidate \(x\), if (i) the domain and version identifiers supplied to the gate are correct and canonical, (ii) all required preconditions, exceptions, and provenance checks are complete and sound, (iii) the gate evaluates the acceptance predicate above correctly, and (iv) no later component bypasses or overrides the gate, then any candidate for which at least one required compatibility condition is false is not accepted.

**Proof sketch.** By definition, acceptance requires the conjunction of all checks in \(\operatorname{Accept}(x)\). If any required condition is false or unknown, the conjunction is false; the fail-closed decision rule therefore rejects the candidate. This establishes a property of the gate under assumptions (i)–(iv), not a guarantee that upstream extraction, policy completeness, software deployment, or the complete application always satisfies those assumptions.

The proposition is intentionally narrow. It does not prove that the request's true legal, financial, medical, or other semantic domain is always extracted correctly; that the domain taxonomy captures every relevant distinction; that the compatibility policy is complete; or that the system's empirical error rate is zero.

## 4. Required threat and failure model

The conformance suite must include at least these classes:

- **Domain mismatch:** same-looking capsule with a different canonical domain identifier.
- **Version mismatch:** compatible-looking identifiers but stale or unsupported contract versions.
- **Missing/unknown metadata:** absent domain, precondition, exception, provenance, or validation status.
- **Extraction error:** a deliberately wrong request-domain label supplied to the gate, to demonstrate that the gate cannot repair an upstream misclassification.
- **Ambiguity / multiple domains:** request contains more than one plausible domain or a cross-domain dependency; the expected outcome must be explicitly defined (reject or route to a separately specified composition path).
- **Exception mismatch:** exception policy absent, stale, or inconsistent.
- **Canonicalization collision:** two distinct domains map to the same normalized identifier, or visually similar identifiers differ after canonicalization.
- **Tampering / provenance failure:** altered capsule metadata, invalid signature/hash, or untrusted validation status.
- **Bypass / ordering error:** execution path attempts to consume the capsule before or without the gate.
- **Unknown runtime result:** validation service unavailable, timeout, or an unrecognized policy version; expected result is fail-closed, not implicit acceptance.

A test case is not sufficient merely because the input string differs. The fixture must state the expected domain identity, contract version, preconditions, exception policy, provenance status, expected decision, and expected reason code.

## 5. Reproducible protocol

Before running tests, publish a machine-readable manifest containing:

- source commit and implementation version;
- domain taxonomy and compatibility-policy version/hash;
- canonicalization rules;
- fixture-generation script and fixed seed, where randomness is used;
- test-case counts by failure class;
- expected outcomes and reason codes;
- test command, runtime/dependency versions, and environment;
- raw per-case results and a summary script.

Report separate quantities:
\[
N_{\mathrm{tested}},\quad N_{\mathrm{rejected\_incompatible}},\quad
N_{\mathrm{incorrect\_accept}},\quad
N_{\mathrm{false\_reject}}.
\]
Define the empirical incorrect-acceptance rate as
\[
\hat p_{\mathrm{IA}} =
\frac{N_{\mathrm{incorrect\_accept}}}
{N_{\mathrm{known\_incompatible\_cases}}}.
\]
Do not use a denominator that mixes compatible and incompatible cases. Report the numerator, denominator, dataset construction, and an appropriate binomial confidence interval. If zero incorrect acceptances are observed, report “0 observed in n tested incompatible cases” with the interval; do not report a proven population rate of zero.

The test suite should also report compatible-case rejection separately, since a gate that rejects everything would trivially avoid incorrect acceptance but would not be useful.

## 6. Manuscript replacement text

> **Cross-domain transfer safety.** SCRS specifies a fail-closed compatibility gate for reuse of a reasoning capsule. A capsule is eligible for reuse only when validated domain identifiers and contract versions match and the required preconditions, exception policy, and provenance checks pass. Missing, stale, unknown, or inconsistent metadata causes rejection. Under the assumptions that domain identifiers are correctly extracted and canonicalized, the compatibility contract is complete, the gate conforms to its specification, and no execution path bypasses it, an incompatible candidate cannot be accepted by the gate. This is a conditional property of the specified decision procedure; it does not establish that upstream domain extraction is error-free or that the end-to-end system has a zero empirical error rate. The latter requires a separately reported conformance and adversarial evaluation. Until such evaluation is run, zero incorrect transfers should be treated as a design objective, not an observed result.

## 7. Acceptance criteria for this finding

- [ ] Manuscript language no longer states or implies unconditional structural impossibility or a measured zero rate without evidence.
- [ ] The gate's inputs, canonicalization, compatibility predicate, unknown-state behavior, and fail-closed rule are defined.
- [ ] The proposition states its assumptions and does not extend the gate-level result to upstream extraction or the full system.
- [ ] A conformance protocol covers the threat classes above and includes compatible cases as well as incompatible cases.
- [ ] Results are reported with explicit numerator/denominator and uncertainty; unrun tests are labelled pending.
- [ ] Claim/evidence ledger marks the guarantee as **conditional specification**, and end-to-end performance as **not yet measured**.

## 8. Current evidence status

This change supplies a rigorous manuscript-level contract and a reproducible test protocol. It does **not** establish that code implements the gate, that the test suite has run, or that any empirical error rate has been measured. Those remain unverified until implementation and raw test outputs are available.
