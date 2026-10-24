# Research validation ledger

| Claim or artifact | Current status | Evidence / limitation | Required action |
|---|---|---|---|
| Regime probability decomposition | Analytical | Conditional halt probability is defined after admission | Preserve definition and test probabilities sum to one |
| Simplified expected Oracle output formula | Conditional | Requires equal conditional full-Oracle output means for bailout and miss | Use separate conditional means unless justified |
| Unified SCRS output-token value in Table 2 | Inconsistent under stated simplified assumptions | Baseline 2,380; alpha_eff 0.62 implies fallback contribution 904.4 before positive Anchor output; reported 894 | Reconcile source values or correct table/equation |
| Anchor call count | Unverified at transport layer | Logical interrupt, transport attempts, provider generations, and billed tokens are distinct; transport implementation and traces are not supplied | Instrument actual transport boundary and reconcile provider evidence |
| Algorithm 1 interrupt counter | Corrected in replacement draft | Original `n_int` was initialized but never incremented; `oracleCallsAvoided` incorrectly depended on it | Use Section 8.3 counter contract; validate all required scenarios before claiming implementation correctness |
| Full Oracle fallback avoidance | Defined, not measured | A fast-path completion can avoid full-reasoning fallback while still making Anchor/Oracle calls | Report only from known terminal regime and fallback events; never describe as zero total Oracle traffic |
| Telemetry schema | Specification updated; implementation unverified | Replacement drafts define event/request fields and missing-evidence handling | Implement instrumentation and validate against real traces before making measured claims |
| P50/P95 values | Synthetic scenario only | Scenario assumptions are not production measurements | Obtain traces and reproduce percentiles |
| Dollar cost table | Not independently reproducible | Exact prices, cache treatment, retries, and local amortization not fully specified | Publish cost assumptions and calculation |
| Original DOCX integrity | Issue observed | CRC error in word/media/image1.png; original was left unchanged | Recover a clean source copy before full-document editing |
