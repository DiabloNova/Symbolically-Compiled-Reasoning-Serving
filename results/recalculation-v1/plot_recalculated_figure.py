#!/usr/bin/env python3
"""Regenerate Figure 3 from the recalculation-v1 CSV. Percentiles are synthetic, not measured."""
from pathlib import Path
import csv
import numpy as np
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
with (HERE / "recalculated_table2.csv").open(encoding="utf-8", newline="") as f:
    rows = list(csv.DictReader(f))
labels = ["Baseline", "Tier I", "Tier II", "Tier III", "Tier I + III", "Tier I + II", "No gate", "Unified"]
p50 = [float(row["P50_E2E_s"]) for row in rows]
p95 = [float(row["P95_E2E_s"]) for row in rows]
fig, ax = plt.subplots(figsize=(13.2, 6.6))
x = np.arange(len(labels)); width = 0.36
ax.bar(x - width/2, p50, width, label="P50 end-to-end latency")
ax.bar(x + width/2, p95, width, label="P95 end-to-end latency")
ax.set_xticks(x); ax.set_xticklabels(labels, rotation=25, ha="right")
ax.set_ylabel("Latency (seconds)")
ax.set_title("SCRS recalculation — synthetic Monte Carlo latency (not measured)")
ax.grid(axis="y", alpha=0.25); ax.legend(frameon=False)
fig.tight_layout()
fig.savefig(HERE / "Figure3_synthetic_latency_recalculated.png", dpi=220)
plt.close(fig)
print("Wrote Figure3_synthetic_latency_recalculated.png")
