# Scenario v2 — historical synthetic scenario (superseded)

This directory is retained for provenance only. It is **not** the current calculation behind the revised SCRS manuscript.

Scenario v2 used seed `20261022` and assumed `p_hit = 0.72`, `P(R2) = 0.10`, and `P(R3) = 0.28`. Those values conflict with the manuscript's stated assumptions `p_hit = 0.78` and `p_halt = 0.205) conditional on admission, which imply (P(R1)=0.6201), (P(R2)=0.1599), and (P(R3)=0.22). It also did not consistently apply the manuscript's distinction between conditional and unconditional Anchor-call intensity.

Use [recalculation-v1](../recalculation-v1/README.md) for the corrected current scenario, CSV, manifest, and Figure 3 generator. Recalculation-v1 also corrects an initial implementation error that accidentally imposed perfect correlation between latency marginals. Its latency outputs are still synthetic Monte Carlo values, not production measurements.

Do not cite the v2 Unified SCRS P50/P95 values of approximately 8.84/53.65 seconds as the current manuscript results. Actual Anchor transport round trips, retries, billing, and empirical latency remain unverified.
