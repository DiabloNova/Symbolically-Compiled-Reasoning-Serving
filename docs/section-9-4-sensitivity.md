# Replacement draft — Section 9.4: Sensitivity interpretation

Sensitivity results should be interpreted against the variables that determine the fast-path share and the cost of fallback: (p_{hit}), conditional (p_{halt}), Anchor tokens per successful request, Oracle input/output prices, local execution time, queue delay, and the number of Anchor API attempts per logical interrupt. These variables should be varied separately before interaction effects are interpreted.

A higher fast-path admission rate does not necessarily improve tail latency: a high halt rate can create a large bailout cohort, and serial Anchor round trips can add latency even when token output is reduced. Mean latency and P50 can improve while P95 remains dominated by fallback requests. Therefore report regime proportions and conditional latency distributions alongside aggregate percentiles.

Do not treat synthetic Monte Carlo output as empirical evidence. Publish the random seed, sample size, distribution families and parameters, correlations, call/retry assumptions, and code version. When telemetry becomes available, calibrate the distributions from measured traces and compare scenario predictions against held-out observations.

Any sensitivity statement must specify which variables were held constant. Cost conclusions also require explicit provider prices, cached-token policy, retry billing, and local-compute accounting.
