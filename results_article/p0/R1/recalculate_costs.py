#!/usr/bin/env python3
"""Rebuild the R1 Table 2 and Figure 3(a) cost-audit CSVs using stdlib only.

Run from any directory with Python 3:
    python recalculate_costs.py
The two CSVs are written beside this script. Values labelled as carry-forward,
partial, or unreproduced are not silently treated as validated totals.
"""
from __future__ import annotations

import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REQUESTS = Decimal("10000")
PRICE_IN_PER_MILLION = Decimal("2")
PRICE_OUT_PER_MILLION = Decimal("10")
MILLION = Decimal("1000000")
CENT = Decimal("0.01")

CONFIGS = [
    {
        "name": "Baseline (raw RAG + full oracle)", "in": 6420, "source_out": 2380,
        "alpha": Decimal("0"), "full_mean": 2380, "interrupts": Decimal("0"),
        "k": 5, "out": Decimal("2380"), "alt_out": None,
        "derivation": "Source output carried forward as baseline reference; input/output aggregation across calls not independently verified",
        "status": "Reference scenario; source token means carried forward", "api_complete": True,
        "source_cost": Decimal("549.60"), "figure_reason": "API-only value excludes unspecified hosting and assumes Table 2 input tokens cover every billed Oracle call",
    },
    {
        "name": "Tier I only (capsules)", "in": 1180, "source_out": 2310,
        "alpha": Decimal("0"), "full_mean": 2310, "interrupts": Decimal("0"),
        "k": 5, "out": Decimal("2310"), "alt_out": None,
        "derivation": "Source output carried forward; capsule-path mean not independently derived",
        "status": "Source output carried forward; not independently derived", "api_complete": True,
        "source_cost": Decimal("381.90"), "figure_reason": "API-only value excludes unspecified hosting and may omit Anchor prompts/retries if In-tok is not aggregated",
    },
    {
        "name": "Tier II only (hardened JIT)", "in": 2440, "source_out": 905,
        "alpha": Decimal("0.62"), "full_mean": 2380, "interrupts": Decimal("0"),
        "k": 5, "out": Decimal("904.4"), "alt_out": None,
        "derivation": "Fallback-only estimate: (1 - 0.62) × 2,380 = 904.4; excludes Anchor output by configuration assumption; source 905 is not reproduced exactly",
        "status": "Fallback-only calculation; 904.4 derived under shared-mean assumption", "api_complete": True,
        "source_cost": Decimal("234.15"), "figure_reason": "Source output 905 is not reproduced exactly; full input billing semantics and host cost remain unresolved",
    },
    {
        "name": "Tier III only (entropy interrupt)", "in": 6420, "source_out": 480,
        "alpha": Decimal("0"), "full_mean": 2380, "interrupts": None,
        "k": 5, "out": None, "alt_out": None,
        "derivation": "Not reproducible from supplied inputs: interrupt distribution / mean billable output by regime is not supplied",
        "status": "Not reproducible", "api_complete": False,
        "source_cost": Decimal("341.20"), "figure_reason": "Published 480-token output cannot be derived from the supplied interrupt/output assumptions; source-cost bar must not be treated as validated",
    },
    {
        "name": "Tier I + III (no JIT)", "in": 1180, "source_out": 360,
        "alpha": Decimal("0"), "full_mean": 2310, "interrupts": Decimal("9.6"),
        "k": 5, "out": Decimal("48"), "alt_out": None,
        "derivation": "Anchor-token subtotal only: 9.6 × 5 = 48; source 360 may combine model outputs or use another denominator; split Oracle-billed and local-SLM output before costing",
        "status": "Anchor-output subtotal only, using 9.6 × 5", "api_complete": False,
        "source_cost": Decimal("98.40"), "figure_reason": "Source output 360 is unexplained; the spend shown is not a complete cost unless no further Oracle output/input is billed",
    },
    {
        "name": "Tier I + II (no entropy interrupt)", "in": 448, "source_out": 878,
        "alpha": Decimal("0.62"), "full_mean": 2310, "interrupts": Decimal("0"),
        "k": 5, "out": Decimal("877.8"), "alt_out": None,
        "derivation": "Fallback-only estimate: (1 - 0.62) × 2,310 = 877.8; rounds to source 878",
        "status": "Fallback-only calculation; 877.8 derived under shared-mean assumption", "api_complete": True,
        "source_cost": Decimal("168.10"), "figure_reason": "Recalculated output rounds to source 878; all-in cost still requires hosting and complete input accounting",
    },
    {
        "name": "Naive unhardened JIT (no gate)", "in": 380, "source_out": 690,
        "alpha": Decimal("0.78"), "full_mean": 2380, "interrupts": None,
        "k": 5, "out": Decimal("523.6"), "alt_out": None,
        "derivation": "Fallback-only component: (1 - 0.78) × 2,380 = 523.6; not the total unless other Oracle output/Anchor calls are absent",
        "status": "Fallback-only component under α_eff = 0.78", "api_complete": False,
        "source_cost": Decimal("139.50"), "figure_reason": "Source output 690 is unexplained; spend omits any Anchor/additional Oracle output and cannot replace source cost",
    },
    {
        "name": "Unified SCRS (I + II + III)", "in": 512, "source_out": 894,
        "alpha": Decimal("0.62"), "full_mean": 2310, "interrupts": Decimal("1.4"),
        "k": 5, "out": Decimal("884.8"), "alt_out": Decimal("882.14"),
        "derivation": "Primary: (1 - 0.62) × 2,310 + 1.4 × 5 = 884.8, treating 1.4 as unconditional; alternate 882.14 treats 1.4 as conditional on fast-path completion",
        "status": "Explicit API-only scenario; 884.8 assumes 1.4 interrupts/request is unconditional", "api_complete": True,
        "source_cost": Decimal("118.70"), "figure_reason": "Alternate interpretation gives 882.14; source 894 and source all-in costs are not reproduced, and hosting is unpriced",
    },
]


def money(value: Decimal | None) -> str:
    if value is None:
        return ""
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def pct_reduction(base: Decimal, value: Decimal | None) -> str:
    if value is None or base == 0:
        return ""
    return str((((base - value) / base) * Decimal("100")).quantize(CENT, rounding=ROUND_HALF_UP))


def api_input_spend(tokens: int) -> Decimal:
    return Decimal(tokens) * PRICE_IN_PER_MILLION * REQUESTS / MILLION


def api_output_spend(tokens: Decimal | None) -> Decimal | None:
    if tokens is None:
        return None
    return tokens * PRICE_OUT_PER_MILLION * REQUESTS / MILLION


def build_rows() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    table_rows: list[dict[str, str]] = []
    figure_rows: list[dict[str, str]] = []
    base_source = CONFIGS[0]["source_cost"]
    base_api = api_input_spend(CONFIGS[0]["in"]) + api_output_spend(CONFIGS[0]["out"])

    for c in CONFIGS:
        in_spend = api_input_spend(c["in"])
        out_spend = api_output_spend(c["out"])
        total_spend = None if out_spend is None else in_spend + out_spend
        alt_out = c["alt_out"]
        alt_spend = None if alt_out is None else in_spend + api_output_spend(alt_out)
        api_red = pct_reduction(base_api, total_spend) if c["api_complete"] else ""
        source_red = pct_reduction(base_source, c["source_cost"])
        table_rows.append({
            "configuration": c["name"],
            "source_in_tokens_per_request": str(c["in"]),
            "source_out_tokens_per_request": str(c["source_out"]),
            "alpha_eff": str(c["alpha"]),
            "full_oracle_output_mean_used": str(c["full_mean"]),
            "mean_anchor_interrupts_per_request": "" if c["interrupts"] is None else str(c["interrupts"]),
            "anchor_tokens_per_interrupt": str(c["k"]),
            "r1_output_estimate_or_subtotal": "" if c["out"] is None else str(c["out"]),
            "alternate_output_if_anchor_mean_conditional_on_fast_path": "" if alt_out is None else str(alt_out),
            "output_derivation_and_status": c["derivation"],
            "scenario_input_api_usd_per_10000": money(in_spend),
            "scenario_output_api_usd_per_10000": money(out_spend),
            "scenario_api_spend_usd_per_10000": money(total_spend),
            "alternate_api_spend_usd_per_10000": "" if alt_spend is None else str(alt_spend.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)),
            "source_all_in_cost_usd_per_10000": money(c["source_cost"]),
            "source_cost_reduction_vs_baseline_pct": source_red,
            "scenario_api_reduction_vs_baseline_pct": api_red,
            "hosting_and_billing_status": "API-only scenario; hosting allocation unspecified" if c["api_complete"] else c["status"],
        })
        figure_rows.append({
            "configuration": c["name"],
            "source_cost_usd_per_10000": money(c["source_cost"]),
            "source_cost_reduction_vs_baseline_pct": source_red,
            "source_out_tokens_per_request": str(c["source_out"]),
            "r1_output_tokens_or_subtotal": "" if c["out"] is None else str(c["out"]),
            "api_input_spend_usd_per_10000": money(in_spend),
            "api_output_spend_usd_per_10000": money(out_spend),
            "api_only_scenario_spend_usd_per_10000": money(total_spend),
            "scenario_status": c["status"],
            "publication_ready_for_figure3a": "no",
            "reason": c["figure_reason"],
        })
    return table_rows, figure_rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    table_rows, figure_rows = build_rows()
    write_csv(ROOT / "table2_recalculation.csv", table_rows)
    write_csv(ROOT / "figure3_cost_data.csv", figure_rows)
    assert len(table_rows) == 8 and len(figure_rows) == 8
    unified = next(row for row in table_rows if row["configuration"].startswith("Unified SCRS"))
    assert Decimal(unified["r1_output_estimate_or_subtotal"]) == Decimal("884.8")
    assert Decimal(unified["alternate_output_if_anchor_mean_conditional_on_fast_path"]) == Decimal("882.14")
    assert Decimal(next(row for row in table_rows if row["configuration"].startswith("Tier I + III"))["r1_output_estimate_or_subtotal"]) == Decimal("48")
    print("Wrote 8-row table2_recalculation.csv and figure3_cost_data.csv.")
    print("QA: Unified=884.8 unconditional / 882.14 conditional; Tier I + III Anchor subtotal=48; unreproduced rows stay blank/flagged.")


if __name__ == "__main__":
    main()
