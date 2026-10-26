#!/usr/bin/env python3
"""Exact finite-distribution sanity checks for the decision-semantics note.

This is a mathematical toy checker only. It is not an SCRS encoder, model, or
empirical evaluation. Probabilities are enumerated exactly at the table level;
floating-point arithmetic is used only for logarithms and comparisons.
"""
from __future__ import annotations

import itertools
import json
import math
from collections import Counter
from typing import Hashable, Literal, Sequence

Observation = tuple[float, Hashable, Hashable, Hashable, Hashable]
Features = Literal["full_context", "capsule"]


def _validate(observations: Sequence[Observation]) -> list[Observation]:
    if not observations:
        raise ValueError("At least one observation is required.")
    normalized: list[Observation] = []
    mass = 0.0
    for row in observations:
        if len(row) != 5:
            raise ValueError("Each observation must be (probability, query, context, outcome, capsule).")
        probability, query, context, outcome, capsule = row
        try:
            probability = float(probability)
        except (TypeError, ValueError) as exc:
            raise ValueError("Probabilities must be finite positive numbers.") from exc
        if not math.isfinite(probability) or probability <= 0.0:
            raise ValueError("Probabilities must be finite and strictly positive.")
        normalized.append((probability, query, context, outcome, capsule))
        mass += probability
    if not math.isclose(mass, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"Observation probabilities must sum to 1 (got {mass:.16g}).")
    return normalized


def conditional_information_loss(observations: Sequence[Observation]) -> float:
    """Compute I(Y;D | Q,K) in nats from an explicit finite joint distribution."""
    rows = _validate(observations)
    qdk_y = Counter()
    qdk_total = Counter()
    qk_y = Counter()
    qk_total = Counter()

    for probability, query, context, outcome, capsule in rows:
        qdk_y[(query, context, capsule, outcome)] += probability
        qdk_total[(query, context, capsule)] += probability
        qk_y[(query, capsule, outcome)] += probability
        qk_total[(query, capsule)] += probability

    result = 0.0
    for (query, context, capsule, outcome), mass in qdk_y.items():
        p_y_given_qdk = mass / qdk_total[(query, context, capsule)]
        p_y_given_qk = qk_y[(query, capsule, outcome)] / qk_total[(query, capsule)]
        result += mass * math.log(p_y_given_qdk / p_y_given_qk)
    # Remove only tiny negative round-off around the theoretical lower bound 0.
    if result < 0.0 and result > -1e-12:
        result = 0.0
    if result < 0.0:
        raise ArithmeticError(f"Computed conditional mutual information was negative: {result}")
    return result


def bayes_zero_one_risk(observations: Sequence[Observation], features: Features) -> float:
    """Exact finite-table Bayes 0-1 risk given (Q,D) or (Q,K)."""
    rows = _validate(observations)
    masses_by_group_and_y = Counter()
    group_totals = Counter()
    for probability, query, context, outcome, capsule in rows:
        group = (query, context) if features == "full_context" else (query, capsule)
        masses_by_group_and_y[(group, outcome)] += probability
        group_totals[group] += probability
    risk = 0.0
    for group, total in group_totals.items():
        largest_label_mass = max(
            mass for (candidate_group, _), mass in masses_by_group_and_y.items()
            if candidate_group == group
        )
        risk += total - largest_label_mass
    return risk


def example_discarding_irrelevant_nuisance() -> list[Observation]:
    """Y=C and K=C; D=(C,N), with independent fair bits C,N."""
    return [(0.25, "q", (c, n), c, c) for c, n in itertools.product((0, 1), repeat=2)]


def example_discarding_decisive_fact() -> list[Observation]:
    """Y=C and K=N; D=(C,N), with independent fair bits C,N."""
    return [(0.25, "q", (c, n), c, n) for c, n in itertools.product((0, 1), repeat=2)]


def exact_example_report() -> dict:
    irrelevant = example_discarding_irrelevant_nuisance()
    decisive = example_discarding_decisive_fact()
    delta_irrelevant = conditional_information_loss(irrelevant)
    delta_decisive = conditional_information_loss(decisive)
    full_risk_decisive = bayes_zero_one_risk(decisive, "full_context")
    capsule_risk_decisive = bayes_zero_one_risk(decisive, "capsule")
    pinsker_bound = math.sqrt(delta_decisive / 2.0)
    return {
        "status": "PASS" if (
            abs(delta_irrelevant) < 1e-12
            and abs(bayes_zero_one_risk(irrelevant, "full_context")
                    - bayes_zero_one_risk(irrelevant, "capsule")) < 1e-12
            and math.isclose(delta_decisive, math.log(2.0), abs_tol=1e-12)
            and math.isclose(full_risk_decisive, 0.0, abs_tol=1e-12)
            and math.isclose(capsule_risk_decisive, 0.5, abs_tol=1e-12)
            and capsule_risk_decisive - full_risk_decisive <= pinsker_bound + 1e-12
        ) else "FAIL",
        "evidence_status": "exact finite-distribution sanity check; not SCRS empirical evidence",
        "irrelevant_nuisance": {
            "conditional_information_loss_nats": delta_irrelevant,
            "full_context_bayes_risk": bayes_zero_one_risk(irrelevant, "full_context"),
            "capsule_bayes_risk": bayes_zero_one_risk(irrelevant, "capsule"),
        },
        "decisive_fact_discarded": {
            "conditional_information_loss_nats": delta_decisive,
            "expected_nats": math.log(2.0),
            "full_context_bayes_risk": full_risk_decisive,
            "capsule_bayes_risk": capsule_risk_decisive,
            "risk_gap": capsule_risk_decisive - full_risk_decisive,
            "pinsker_upper_bound": pinsker_bound,
            "bound_holds": capsule_risk_decisive - full_risk_decisive <= pinsker_bound + 1e-12,
        },
    }


if __name__ == "__main__":
    report = exact_example_report()
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report["status"] == "PASS" else 1)
