"""Monte Carlo simulation stage.

A standalone vectorized Monte Carlo engine (NumPy) that reads from
normalized pipeline inputs. Adapted from retire-ai monte_carlo_runner.py.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _simulate_retirement_age(
    *,
    retirement_age: int,
    start_balance: float,
    return_mean: float,
    return_std_dev: float,
    longevity_age: int,
    monthly_spending: float,
    ss_annual: float,
    legacy_floor: float,
    simulation_count: int,
    seed: int,
    scenario: str | None = None,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    years = longevity_age - retirement_age
    if years <= 0:
        return {
            "retirement_age": retirement_age,
            "scenario": scenario or "base",
            "success_probability": 0.0,
            "years_simulated": 0,
        }

    if scenario == "poor_sequence_first_3_years":
        draws = np.vstack([
            _scenario_draws(scenario, years, np.random.default_rng(seed + i), return_mean, return_std_dev)
            for i in range(simulation_count)
        ])
    elif scenario == "delayed_market_recovery":
        draws = np.vstack([
            _scenario_draws(scenario, years, np.random.default_rng(seed + i), return_mean, return_std_dev)
            for i in range(simulation_count)
        ])
    else:
        draws = rng.normal(return_mean, return_std_dev, size=(simulation_count, years))

    balance = np.full(simulation_count, float(start_balance))
    failed = np.zeros(simulation_count, dtype=bool)
    annual_spending = monthly_spending * 12.0

    for i in range(years):
        withdrawal = np.maximum(annual_spending - ss_annual, 0.0)
        balance = (balance - withdrawal) * (1.0 + draws[:, i])
        failed |= balance <= 0.0
        balance = np.where(balance < 0.0, 0.0, balance)

    success = (~failed) & (balance >= legacy_floor)
    percentiles = np.percentile(balance, [5, 25, 50, 75, 95]).tolist()

    return {
        "retirement_age": retirement_age,
        "scenario": scenario or "base",
        "starting_balance_real": round(float(start_balance), 2),
        "years_simulated": years,
        "success_probability": round(float(np.mean(success)), 4),
        "terminal_balance_percentiles_real": {
            "p05": round(percentiles[0], 2),
            "p25": round(percentiles[1], 2),
            "p50": round(percentiles[2], 2),
            "p75": round(percentiles[3], 2),
            "p95": round(percentiles[4], 2),
        },
    }


def _scenario_draws(
    name: str,
    years: int,
    rng: np.random.Generator,
    mean: float,
    std: float,
) -> np.ndarray:
    returns = rng.normal(mean, std, size=years)
    if name == "poor_sequence_first_3_years":
        n = min(3, years)
        returns[:n] = np.minimum(returns[:n], -0.15)
    elif name == "delayed_market_recovery":
        n = min(2, years)
        returns[:n] = np.minimum(returns[:n], -0.10)
    return returns


def run_monte_carlo(
    inputs: dict[str, Any],
    derived: dict[str, Any],
    seed: int = 42,
) -> dict[str, Any]:
    """Run Monte Carlo simulations for all retirement ages.

    *inputs* is from the normalize stage; *derived* from the derive stage.
    """
    retirement_ages: list[int] = inputs["retirement_ages"]
    return_mean: float = inputs["return_mean"]
    return_std_dev: float = inputs["return_std_dev"]
    longevity_age: int = inputs["longevity_age"]
    monthly_spending: float = inputs["retirement_spending_monthly_real"]
    legacy_floor: float = inputs["legacy_floor"]
    required_prob: float = inputs["required_success_probability"]
    simulation_count: int = inputs["simulation_count"]
    claiming_age: int = inputs["social_security_claiming_age"]

    ss_67_annual: float = inputs["social_security_age_67_annual"]
    ss_70_annual: float = inputs["social_security_age_70_annual"]
    if claiming_age <= 67:
        ss_annual = ss_67_annual
    elif claiming_age >= 70:
        ss_annual = ss_70_annual
    else:
        frac = (claiming_age - 67) / 3.0
        ss_annual = ss_67_annual + (ss_70_annual - ss_67_annual) * frac

    balances = derived.get("projected_balances_base_case_real", {})

    base_results: list[dict[str, Any]] = []
    for age in retirement_ages:
        start_balance = balances.get(f"age_{age}", inputs["current_balance"])
        result = _simulate_retirement_age(
            retirement_age=age,
            start_balance=float(start_balance),
            return_mean=return_mean,
            return_std_dev=return_std_dev,
            longevity_age=longevity_age,
            monthly_spending=monthly_spending,
            ss_annual=ss_annual if age >= claiming_age else 0.0,
            legacy_floor=legacy_floor,
            simulation_count=simulation_count,
            seed=seed + age,
        )
        base_results.append(result)

    sensitivity_scenarios = ["poor_sequence_first_3_years", "delayed_market_recovery"]
    sensitivity_results: dict[str, list[dict[str, Any]]] = {}
    for scenario in sensitivity_scenarios:
        scenario_results = []
        for age in retirement_ages:
            start_balance = balances.get(f"age_{age}", inputs["current_balance"])
            result = _simulate_retirement_age(
                retirement_age=age,
                start_balance=float(start_balance),
                return_mean=return_mean,
                return_std_dev=return_std_dev,
                longevity_age=longevity_age,
                monthly_spending=monthly_spending,
                ss_annual=ss_annual if age >= claiming_age else 0.0,
                legacy_floor=legacy_floor,
                simulation_count=simulation_count,
                seed=seed + age + 1000,
                scenario=scenario,
            )
            scenario_results.append(result)
        sensitivity_results[scenario] = scenario_results

    recommended = max(
        base_results, key=lambda x: (x["success_probability"], x["retirement_age"])
    )

    return {
        "base_results": base_results,
        "sensitivity_results": sensitivity_results,
        "assessment": {
            "minimum_success_probability_target": required_prob,
            "all_retirement_ages_meet_target": all(
                r["success_probability"] >= required_prob for r in base_results
            ),
            "recommended_retirement_age": recommended["retirement_age"],
        },
    }
