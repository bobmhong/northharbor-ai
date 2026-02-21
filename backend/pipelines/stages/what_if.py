"""What-if scenario analysis stage.

Runs named scenarios with modified assumptions and compares outcomes
to baseline. Adapted from retire-ai what_if_runner.py.
"""

from __future__ import annotations

from typing import Any

from backend.pipelines.stages.monte_carlo import run_monte_carlo


DEFAULT_SCENARIOS: list[dict[str, Any]] = [
    {
        "name": "Higher Spending",
        "assumptions": {"retirement_spending_monthly_real_delta": 500},
    },
    {
        "name": "Lower Spending",
        "assumptions": {"retirement_spending_monthly_real_delta": -500},
    },
    {
        "name": "Higher Savings Rate",
        "assumptions": {"savings_rate_percent_delta": 3},
    },
    {
        "name": "Delay Retirement 2 Years",
        "assumptions": {"retirement_age_shift": 2},
    },
]


def run_what_if(
    inputs: dict[str, Any],
    derived: dict[str, Any],
    mc_results: dict[str, Any],
    seed: int = 42,
    scenarios: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run what-if scenarios and compare to baseline."""
    if scenarios is None:
        scenarios = DEFAULT_SCENARIOS

    assessment = mc_results.get("assessment", {})
    baseline_age = int(assessment.get("recommended_retirement_age", 67))
    base_results = mc_results.get("base_results", [])
    baseline_row = next(
        (r for r in base_results if r["retirement_age"] == baseline_age),
        None,
    )
    baseline_success = float(baseline_row["success_probability"]) if baseline_row else 0.0
    baseline_p50 = float(
        baseline_row.get("terminal_balance_percentiles_real", {}).get("p50", 0)
    ) if baseline_row else 0.0

    comparisons: list[dict[str, Any]] = []
    for idx, scenario in enumerate(scenarios, start=1):
        name = scenario["name"]
        assumptions = scenario["assumptions"]
        mod_inputs = dict(inputs)

        spending_delta = assumptions.get("retirement_spending_monthly_real_delta", 0)
        mod_inputs["retirement_spending_monthly_real"] = (
            inputs["retirement_spending_monthly_real"] + spending_delta
        )

        savings_delta = assumptions.get("savings_rate_percent_delta", 0)
        mod_inputs["savings_rate_percent"] = (
            inputs["savings_rate_percent"] + savings_delta
        )

        age_shift = assumptions.get("retirement_age_shift", 0)
        if age_shift != 0:
            mod_inputs["retirement_ages"] = [
                a + age_shift for a in inputs["retirement_ages"]
            ]

        from backend.pipelines.stages.derive import compute_derived_fields

        mod_derived = compute_derived_fields(mod_inputs)
        scenario_mc = run_monte_carlo(
            mod_inputs, mod_derived, seed=seed + (idx * 100)
        )

        scenario_assessment = scenario_mc.get("assessment", {})
        scenario_age = int(scenario_assessment.get("recommended_retirement_age", 67))
        scenario_base = scenario_mc.get("base_results", [])

        scenario_row_at_baseline = next(
            (r for r in scenario_base if r["retirement_age"] == baseline_age),
            next(iter(scenario_base), None),
        )

        if scenario_row_at_baseline:
            sc_success = float(scenario_row_at_baseline["success_probability"])
            sc_p50 = float(
                scenario_row_at_baseline.get("terminal_balance_percentiles_real", {}).get("p50", 0)
            )
        else:
            sc_success = 0.0
            sc_p50 = 0.0

        comparisons.append({
            "name": name,
            "assumptions": assumptions,
            "recommended_retirement_age": scenario_age,
            "success_probability_at_baseline_age": round(sc_success, 4),
            "delta_success_vs_baseline": round(sc_success - baseline_success, 4),
            "terminal_p50_at_baseline_age": round(sc_p50, 2),
            "delta_terminal_p50_vs_baseline": round(sc_p50 - baseline_p50, 2),
        })

    return {
        "baseline": {
            "recommended_retirement_age": baseline_age,
            "success_probability": baseline_success,
            "terminal_p50": baseline_p50,
        },
        "scenario_comparisons": comparisons,
    }
