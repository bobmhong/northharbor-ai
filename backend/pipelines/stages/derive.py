"""Derived fields computation stage.

Computes projected retirement balances and withdrawal analysis
from normalized plan inputs -- a standalone version of the logic
in the retire-ai derive_calculated_fields.py script.
"""

from __future__ import annotations

from typing import Any


def _projected_balance(
    current_balance: float,
    annual_contribution_real: float,
    annual_return_real: float,
    years: int,
) -> float:
    bal = float(current_balance)
    for _ in range(years):
        bal = (bal + annual_contribution_real) * (1.0 + annual_return_real)
    return bal


def compute_derived_fields(inputs: dict[str, Any]) -> dict[str, Any]:
    """Compute projected balances and withdrawal analysis.

    *inputs* is the normalized dict from the normalize stage.
    """
    retirement_ages: list[int] = inputs["retirement_ages"]
    start_age: int = inputs["start_age"]
    current_balance: float = inputs["current_balance"]
    savings_rate: float = inputs["savings_rate_percent"]
    gross_income: float = inputs["gross_annual_income"]
    annual_return: float = inputs["return_mean"]
    monthly_spending: float = inputs["retirement_spending_monthly_real"]
    ss_67_annual: float = inputs["social_security_age_67_annual"]
    ss_70_annual: float = inputs["social_security_age_70_annual"]
    claiming_age: int = inputs["social_security_claiming_age"]

    annual_contribution = gross_income * (savings_rate / 100.0)
    annual_spending = monthly_spending * 12.0

    if claiming_age <= 67:
        ss_claim_annual = ss_67_annual
    elif claiming_age >= 70:
        ss_claim_annual = ss_70_annual
    else:
        frac = (claiming_age - 67) / 3.0
        ss_claim_annual = ss_67_annual + (ss_70_annual - ss_67_annual) * frac

    projected_balances: dict[str, Any] = {}
    withdrawal_analysis: dict[str, Any] = {
        "spending_assumption_monthly_real": round(monthly_spending, 2),
    }

    for age in retirement_ages:
        years = max(age - start_age, 0)
        balance = _projected_balance(
            current_balance, annual_contribution, annual_return, years
        )
        projected_balances[f"age_{age}"] = round(balance, 2)

        ss_annual = ss_claim_annual if age >= claiming_age else 0.0
        portfolio_needed = max(annual_spending - ss_annual, 0.0)
        withdrawal_4pct = balance * 0.04

        withdrawal_analysis[f"age_{age}"] = {
            "projected_balance_real": round(balance, 2),
            "annual_withdrawal_4_percent": round(withdrawal_4pct, 2),
            "monthly_withdrawal_4_percent": round(withdrawal_4pct / 12.0, 2),
            "social_security_annual": round(ss_annual, 2),
            "annual_spending": round(annual_spending, 2),
            "portfolio_needed_after_ss": round(portfolio_needed, 2),
            "effective_withdrawal_rate": round(
                (portfolio_needed / balance) if balance > 0 else 0.0, 6
            ),
        }

    return {
        "projected_balances_base_case_real": projected_balances,
        "withdrawal_analysis": withdrawal_analysis,
        "social_security": {
            "age_67_combined_annual": round(ss_67_annual, 2),
            "age_70_combined_annual": round(ss_70_annual, 2),
            "claiming_age": claiming_age,
            "claiming_age_combined_annual": round(ss_claim_annual, 2),
        },
    }
