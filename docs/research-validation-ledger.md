# Research validation ledger

| Claim or artifact | Current status | Evidence / limitation | Required action |
|---|---|---|---|
| Regime probability decomposition | Analytical | Conditional halt probability is defined after admission | Preserve definition and test probabilities sum to one |
| Simplified expected Oracle output formula | Conditional | Requires equal conditional full-Oracle output means for bailout and miss | Use separate conditional means unless justified |
| Unified SCRS output-token value in Table 2 | Inconsistent under stated simplified assumptions | Baseline 2,380; alpha_eff 0.62 implies fallback contribution 904.4 before positive Anchor output; reported 894 | Reconcile source values or correct table/equation |
| Anchor call count | Unverified at transport layer | Pseudocode has one method call per interrupt; implementation transport not inspected | Inspect reference implementation and event traces |
| Algorithm 1 n_int metric | Defect in supplied pseudocode | Initialized to zero but not incremented | Fix counter or derive from event log |
| P50/P95 values | Synthetic scenario only | Scenario assumptions are not production measurements | Obtain traces and reproduce percentiles |
| Dollar cost table | Not independently reproducible | Exact prices, cache treatment, retries, and local amortization not fully specified | Publish cost assumptions and calculation |
| Original DOCX integrity | Issue observed | CRC error in word/media/image1.png; original was left unchanged | Recover a clean source copy before full-document editing |
