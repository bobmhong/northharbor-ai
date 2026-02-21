"""Historical backtest stage.

Runs deterministic historical-period backtests against baseline Monte
Carlo results. Adapted from retire-ai backtest_runner.py.
"""

from __future__ import annotations

from typing import Any


BUILT_IN_PERIODS: list[dict[str, Any]] = [
    {
        "name": "dot_com_crash",
        "label": "Dot-Com Crash (2000-2002)",
        "years": [2000, 2001, 2002],
        "annual_returns_real": [-0.091, -0.119, -0.221],
    },
    {
        "name": "great_financial_crisis",
        "label": "Great Financial Crisis (2007-2009)",
        "years": [2007, 2008, 2009],
        "annual_returns_real": [0.055, -0.370, 0.265],
    },
    {
        "name": "lost_decade",
        "label": "Lost Decade (2000-2009)",
        "years": list(range(2000, 2010)),
        "annual_returns_real": [
            -0.091, -0.119, -0.221, 0.287, 0.109,
            0.049, 0.158, 0.055, -0.370, 0.265,
        ],
    },
    {
        "name": "stagflation",
        "label": "Stagflation (1973-1974)",
        "years": [1973, 1974],
        "annual_returns_real": [-0.147, -0.264],
    },
]


def simulate_period_outcome(
    *,
    start_balance: float,
    annual_returns_real: list[float],
    longevity_age: int,
    retirement_age: int,
    monthly_spending: float,
    ss_annual: float,
    legacy_floor: float,
    return_mean: float,
) -> dict[str, Any]:
    """Simulate a single historical period outcome."""
    years_total = longevity_age - retirement_age
    if years_total <= 0:
        return {"success": False, "terminal_balance_real": 0.0}

    modeled_returns = list(annual_returns_real[:years_total])
    if len(modeled_returns) < years_total:
        modeled_returns.extend([return_mean] * (years_total - len(modeled_returns)))

    annual_spending = monthly_spending * 12.0
    balance = float(start_balance)
    depleted = False
    depletion_age: int | None = None

    for i, year_return in enumerate(modeled_returns):
        age = retirement_age + i
        withdrawal = max(annual_spending - (ss_annual if age >= retirement_age else 0.0), 0.0)
        balance = (balance - withdrawal) * (1.0 + float(year_return))
        if balance <= 0.0 and not depleted:
            depleted = True
            depletion_age = age
        if balance < 0.0:
            balance = 0.0

    success = (not depleted) and balance >= legacy_floor
    return {
        "years_applied": min(len(annual_returns_real), years_total),
        "terminal_balance_real": round(balance, 2),
        "success": success,
        "depletion_age": depletion_age,
    }


def run_backtest(
    inputs: dict[str, Any],
    derived: dict[str, Any],
    mc_results: dict[str, Any],
) -> dict[str, Any]:
    """Run historical backtests at the recommended retirement age."""
    assessment = mc_results.get("assessment", {})
    recommended_age = int(assessment.get("recommended_retirement_age", 67))
    balances = derived.get("projected_balances_base_case_real", {})
    start_balance = float(balances.get(f"age_{recommended_age}", inputs["current_balance"]))

    base_results = mc_results.get("base_results", [])
    baseline_row = next(
        (r for r in base_results if r["retirement_age"] == recommended_age),
        None,
    )
    baseline_success = float(baseline_row["success_probability"]) if baseline_row else 0.0
    baseline_p50 = float(
        baseline_row.get("terminal_balance_percentiles_real", {}).get("p50", 0)
    ) if baseline_row else 0.0

    claiming_age = inputs["social_security_claiming_age"]
    ss_67 = inputs["social_security_age_67_annual"]
    ss_70 = inputs["social_security_age_70_annual"]
    if claiming_age <= 67:
        ss_annual = ss_67
    elif claiming_age >= 70:
        ss_annual = ss_70
    else:
        frac = (claiming_age - 67) / 3.0
        ss_annual = ss_67 + (ss_70 - ss_67) * frac

    comparisons: list[dict[str, Any]] = []
    for period in BUILT_IN_PERIODS:
        outcome = simulate_period_outcome(
            start_balance=start_balance,
            annual_returns_real=period["annual_returns_real"],
            longevity_age=inputs["longevity_age"],
            retirement_age=recommended_age,
            monthly_spending=inputs["retirement_spending_monthly_real"],
            ss_annual=ss_annual if recommended_age >= claiming_age else 0.0,
            legacy_floor=inputs["legacy_floor"],
            return_mean=inputs["return_mean"],
        )
        success_prob = 1.0 if outcome["success"] else 0.0
        terminal = float(outcome["terminal_balance_real"])
        comparisons.append({
            "name": period["name"],
            "label": period["label"],
            "start_year": period["years"][0],
            "end_year": period["years"][-1],
            "years_applied": outcome["years_applied"],
            "success": outcome["success"],
            "success_as_probability": success_prob,
            "delta_success_vs_baseline": round(success_prob - baseline_success, 4),
            "terminal_balance_real": terminal,
            "delta_terminal_vs_baseline_p50": round(terminal - baseline_p50, 2),
            "depletion_age": outcome["depletion_age"],
        })

    return {
        "retirement_age": recommended_age,
        "baseline_success": baseline_success,
        "baseline_p50": baseline_p50,
        "period_comparisons": comparisons,
    }
