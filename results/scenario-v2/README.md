# Scenario v2 — synthetic, not measured

This directory records a 100,000-request Monte Carlo scenario used to illustrate how assumed regime shares and timing distributions can affect latency percentiles. These numbers are not production telemetry and should not be presented as measured system performance.

The result table is retained as a scenario snapshot. In particular, Unified SCRS has a synthetic P50 of about 8.84 s and P95 of about 53.65 s under the assumptions used for this scenario. These values are assumption-dependent and are not validated against implementation traces.

The earlier local scaffold also contains a fuller simulation script, JSON snapshot, spreadsheet, and plot. Those binary/source artifacts have not all been uploaded to GitHub in this initial pass; see the ZIP linked in the conversation for the full local scaffold. Do not treat this directory as complete reproduction package until the script and its environment/dependency versions are committed.
