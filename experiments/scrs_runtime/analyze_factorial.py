#!/usr/bin/env python3
"""Analyze paired SCRS conditional graph/Anchor interaction from case-results JSONL.

The analyzer deliberately fails closed when any row lacks one of the four
capsule-conditioned arms. It does not fabricate predictions or treat gate
acceptance as semantic preservation.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ARMS = (
    "capsule_only",                 # G=0, A=0
    "capsule_graph_no_anchor",      # G=1, A=0
    "capsule_anchor_no_graph",      # G=0, A=1
    "compiled_graph_gates",         # G=1, A=1
)
BASELINE = "baseline"


class AnalysisError(ValueError):
    """Input records do not satisfy the paired analysis contract."""


def _is_correct(case: dict[str, Any], arm: str) -> int:
    pred = case.get("predictions", {}).get(arm)
    if not isinstance(pred, dict):
        raise AnalysisError(f"case {case.get('task_id')}/{case.get('index')}: missing arm {arm!r}")
    label = pred.get("label")
    valid = pred.get("valid")
    if not isinstance(valid, bool):
        raise AnalysisError(f"case {case.get('task_id')}/{case.get('index')}: arm {arm!r} lacks boolean valid flag")
    gold = case.get("gold_label")
    if not isinstance(gold, str):
        raise AnalysisError(f"case {case.get('task_id')}/{case.get('index')}: missing string gold_label")
    if not valid or not isinstance(label, str) or label == "__INVALID__":
        return 0
    return int(label.strip().casefold() == gold.strip().casefold())


def _wilson(successes: int, n: int, z: float = 1.959963984540054) -> list[float] | None:
    if n <= 0:
        return None
    p = successes / n
    z2 = z * z
    denom = 1 + z2 / n
    center = (p + z2 / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z2 / (4 * n)) / n) / denom
    return [max(0.0, center - margin), min(1.0, center + margin)]


def _percentile(values: list[float], q: float) -> float:
    if not values:
        raise AnalysisError("Cannot calculate percentile of an empty bootstrap distribution.")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - pos) + ordered[hi] * (pos - lo)


def read_cases(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise AnalysisError(f"line {line_no}: invalid JSON: {exc}") from exc
            if not isinstance(case, dict):
                raise AnalysisError(f"line {line_no}: expected JSON object")
            if not isinstance(case.get("task_id"), str) or not isinstance(case.get("index"), int):
                raise AnalysisError(f"line {line_no}: task_id/index missing or invalid")
            cases.append(case)
    if not cases:
        raise AnalysisError("Input has no case records.")
    seen: set[tuple[str, int]] = set()
    for case in cases:
        key = (case["task_id"], case["index"])
        if key in seen:
            raise AnalysisError(f"Duplicate case row {key[0]}/{key[1]}.")
        seen.add(key)
        for arm in (BASELINE, *ARMS):
            _is_correct(case, arm)
    return cases


def analyze_task(cases: list[dict[str, Any]], *, bootstrap_replicates: int, seed: int) -> dict[str, Any]:
    if not cases:
        raise AnalysisError("Task has no cases.")
    task_ids = {case["task_id"] for case in cases}
    if len(task_ids) != 1:
        raise AnalysisError("analyze_task expects records for exactly one task.")
    n = len(cases)
    correctness = {
        arm: [_is_correct(case, arm) for case in cases]
        for arm in (BASELINE, *ARMS)
    }
    accuracies = {}
    for arm, outcomes in correctness.items():
        successes = sum(outcomes)
        accuracies[arm] = {
            "correct": successes,
            "n": n,
            "accuracy": successes / n,
            "wilson_95_ci": _wilson(successes, n),
            "invalid_outputs": sum(
                not case["predictions"][arm].get("valid", False) for case in cases
            ),
        }

    pairwise = {}
    full = correctness["compiled_graph_gates"]
    for arm in (BASELINE, "capsule_only", "capsule_graph_no_anchor", "capsule_anchor_no_graph"):
        other = correctness[arm]
        full_only = sum(a == 1 and b == 0 for a, b in zip(full, other))
        other_only = sum(a == 0 and b == 1 for a, b in zip(full, other))
        pairwise[arm] = {
            "full_correct_partial_wrong": full_only,
            "partial_correct_full_wrong": other_only,
            "net_accuracy_difference_full_minus_comparator": sum(a - b for a, b in zip(full, other)) / n,
            "mcnemar_discordant_pairs": full_only + other_only,
            "mcnemar_exact_two_sided_p": exact_mcnemar_two_sided(full_only, other_only),
        }

    # Per-row difference-in-differences on correctness:
    # (G=1,A=1) - (G=1,A=0) - (G=0,A=1) + (G=0,A=0).
    interaction_values = [
        y11 - y10 - y01 + y00
        for y11, y10, y01, y00 in zip(
            correctness["compiled_graph_gates"],
            correctness["capsule_graph_no_anchor"],
            correctness["capsule_anchor_no_graph"],
            correctness["capsule_only"],
        )
    ]
    estimate = sum(interaction_values) / n
    rng = random.Random(seed)
    bootstrap_means: list[float] = []
    for _ in range(bootstrap_replicates):
        bootstrap_means.append(
            sum(interaction_values[rng.randrange(n)] for _ in range(n)) / n
        )
    return {
        "task_id": next(iter(task_ids)),
        "n_paired_rows": n,
        "arms": accuracies,
        "full_path_paired_comparisons": pairwise,
        "conditional_graph_anchor_interaction": {
            "estimand": "mean[(CGA correct) - (CG correct) - (CA correct) + (C correct)]",
            "estimate": estimate,
            "bootstrap_percentile_95_ci": [
                _percentile(bootstrap_means, 0.025),
                _percentile(bootstrap_means, 0.975),
            ],
            "bootstrap_replicates": bootstrap_replicates,
            "bootstrap_seed": seed,
            "interpretation": (
                "positive estimates indicate positive additive interaction in correctness "
                "conditional on the capsule path and these paired rows; this is not a "
                "distribution-free or universal synergy claim"
            ),
        },
        "analysis_boundary": (
            "Classification correctness is not semantic-preservation annotation. "
            "Gate acceptance is not proof of capsule meaning preservation."
        ),
    }


def exact_mcnemar_two_sided(a: int, b: int) -> float | None:
    """Two-sided exact binomial McNemar p-value based on discordant pairs."""
    n = a + b
    if n == 0:
        return None
    k = min(a, b)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def analyze(cases: list[dict[str, Any]], *, bootstrap_replicates: int, seed: int) -> dict[str, Any]:
    if bootstrap_replicates < 100:
        raise AnalysisError("Use at least 100 bootstrap replicates; 5,000+ is recommended.")
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[case["task_id"]].append(case)
    reports = {
        task: analyze_task(rows, bootstrap_replicates=bootstrap_replicates, seed=seed)
        for task, rows in sorted(grouped.items())
    }
    return {
        "schema_version": 1,
        "analysis": "paired_layer_interaction_v1",
        "task_count": len(reports),
        "tasks": reports,
        "cross_task_pooling": "not performed; tasks have different populations",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="case-results JSONL with all five arms")
    parser.add_argument("--output", type=Path, required=True, help="output JSON report path")
    parser.add_argument("--bootstrap-replicates", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20261027)
    args = parser.parse_args(argv)
    try:
        cases = read_cases(args.input)
        report = analyze(cases, bootstrap_replicates=args.bootstrap_replicates, seed=args.seed)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({
            "status": "ANALYSIS_COMPLETED",
            "input_rows": len(cases),
            "tasks": {
                task_id: {
                    "n": item["n_paired_rows"],
                    "full_accuracy": item["arms"]["compiled_graph_gates"]["accuracy"],
                    "interaction": item["conditional_graph_anchor_interaction"]["estimate"],
                    "interaction_ci": item["conditional_graph_anchor_interaction"]["bootstrap_percentile_95_ci"],
                }
                for task_id, item in report["tasks"].items()
            },
            "output": str(args.output),
        }, indent=2))
        return 0
    except (OSError, AnalysisError, json.JSONDecodeError) as exc:
        print(f"Analysis failed closed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
