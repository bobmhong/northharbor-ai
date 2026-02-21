"""Recommendation engine stage.

Deterministic, rule-based recommendations with traceable evidence.
Adapted from retire-ai recommendations.py.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class Recommendation(BaseModel):
    """A single actionable recommendation with evidence."""

    rule_id: str
    message: str
    evidence: dict[str, Any]


def _pct(value: float) -> str:
    return f"{value * 100:.2f}%"


def _friendly_scenario_name(name: str) -> str:
    mapping = {
        "poor_sequence_first_3_years": "Poor market returns in first 3 years",
        "higher_healthcare_costs": "Higher healthcare costs",
        "delayed_market_recovery": "Delayed market recovery",
    }
    return mapping.get(name, name.replace("_", " "))


def build_recommendations(
    inputs: dict[str, Any],
    mc_results: dict[str, Any],
    *,
    max_items: int = 6,
) -> list[dict[str, Any]]:
    """Build deterministic recommendations from pipeline results."""
    recs: list[Recommendation] = []

    assessment = mc_results.get("assessment", {})
    target = float(assessment.get("minimum_success_probability_target", 0.95))
    recommended_age = int(assessment.get("recommended_retirement_age", 67))
    base_results = mc_results.get("base_results", [])

    retirement_ages = [int(r["retirement_age"]) for r in base_results]
    min_age = min(retirement_ages) if retirement_ages else recommended_age

    if recommended_age > min_age:
        recs.append(Recommendation(
            rule_id="REC_RETIREMENT_AGE_BUFFER",
            message=(
                f"If possible, target retirement closer to age {recommended_age} "
                f"rather than {min_age} to add more financial cushion."
            ),
            evidence={
                "recommended_age": recommended_age,
                "earliest_modeled_age": min_age,
                "target_success_probability": target,
            },
        ))
    else:
        recs.append(Recommendation(
            rule_id="REC_EARLIEST_AGE_MEETS_TARGET",
            message=(
                f"The earliest modeled retirement age ({min_age}) already meets "
                f"the success target of {_pct(target)}."
            ),
            evidence={
                "earliest_modeled_age": min_age,
                "target_success_probability": target,
            },
        ))

    sensitivity = mc_results.get("sensitivity_results", {})
    scenario_probs: list[tuple[str, float]] = []
    for name, results in sensitivity.items():
        for r in results:
            if r["retirement_age"] == recommended_age:
                scenario_probs.append((name, float(r["success_probability"])))
                break

    if scenario_probs:
        worst_name, worst_prob = min(scenario_probs, key=lambda x: x[1])
        if worst_prob < target:
            recs.append(Recommendation(
                rule_id="REC_STRESS_CONTINGENCY_REQUIRED",
                message=(
                    f"Create a backup plan for {_friendly_scenario_name(worst_name).lower()} "
                    f"because modeled success ({_pct(worst_prob)}) is below target."
                ),
                evidence={
                    "worst_stress_scenario": worst_name,
                    "worst_stress_success_probability": worst_prob,
                    "target_success_probability": target,
                },
            ))
        else:
            recs.append(Recommendation(
                rule_id="REC_STRESS_GUARDRAILS_MAINTAIN",
                message=(
                    "Keep spending guardrails active; even the weakest stress "
                    f"scenario stays above target at {_pct(worst_prob)}."
                ),
                evidence={
                    "worst_stress_scenario": worst_name,
                    "worst_stress_success_probability": worst_prob,
                    "target_success_probability": target,
                },
            ))

    savings_rate = inputs.get("savings_rate_percent", 0)
    if savings_rate < 10:
        recs.append(Recommendation(
            rule_id="REC_INCREASE_SAVINGS_RATE",
            message=(
                f"Your savings rate ({savings_rate:.1f}%) is below 10%. "
                "Consider increasing contributions to improve your retirement outlook."
            ),
            evidence={"current_savings_rate": savings_rate},
        ))

    return [r.model_dump() for r in recs[:max_items]]
