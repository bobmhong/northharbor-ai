"""Deterministic cross-field validation rules.

These check logical relationships between multiple schema fields and
return advisory warnings (non-blocking) to surface in the UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from backend.schema.canonical import CanonicalPlanSchema
from backend.schema.provenance import ProvenanceField


@dataclass
class CrossFieldWarning:
    """A single cross-field validation warning."""

    rule_id: str
    fields: list[str]
    message: str
    suggestion: str


def _pf_value(pf: ProvenanceField | None):
    if pf is None:
        return None
    return pf.value


def _range_attr(val, attr: str):
    """Extract min/max from a NumericRange or dict."""
    result = getattr(val, attr, None)
    if result is not None:
        return result
    if isinstance(val, dict):
        return val.get(attr)
    return None


def _check_ss_benefits_increase(schema: CanonicalPlanSchema) -> list[CrossFieldWarning]:
    at_67 = _pf_value(schema.social_security.combined_at_67_monthly)
    at_70 = _pf_value(schema.social_security.combined_at_70_monthly)
    if at_67 is None or at_70 is None:
        return []
    if at_70 >= at_67:
        return []
    return [
        CrossFieldWarning(
            rule_id="ss_benefits_increase",
            fields=[
                "social_security.combined_at_67_monthly",
                "social_security.combined_at_70_monthly",
            ],
            message=(
                f"Social Security benefits typically increase with delayed claiming. "
                f"Your estimate at 70 (${at_70:,}/mo) is lower than at 67 (${at_67:,}/mo)."
            ),
            suggestion="Double-check these values — you may have them reversed.",
        )
    ]


def _check_cannot_retire_in_past(schema: CanonicalPlanSchema) -> list[CrossFieldWarning]:
    birth_year = _pf_value(schema.client.birth_year)
    rw_val = _pf_value(schema.client.retirement_window)
    if birth_year is None or rw_val is None:
        return []
    rw_min = _range_attr(rw_val, "min")
    if rw_min is None:
        return []
    retire_year = int(rw_min) + int(birth_year)
    current_year = datetime.now(timezone.utc).year
    if retire_year > current_year:
        return []
    return [
        CrossFieldWarning(
            rule_id="cannot_retire_in_past",
            fields=["client.birth_year", "client.retirement_window"],
            message=(
                f"Your earliest retirement age ({int(rw_min)}) with birth year "
                f"{int(birth_year)} means you'd retire in {retire_year}, "
                f"which is in the past."
            ),
            suggestion="Update your retirement age or birth year.",
        )
    ]


def _check_horizon_past_retirement(schema: CanonicalPlanSchema) -> list[CrossFieldWarning]:
    horizon_age = _pf_value(schema.monte_carlo.horizon_age)
    rw_val = _pf_value(schema.client.retirement_window)
    if horizon_age is None or rw_val is None:
        return []
    rw_max = _range_attr(rw_val, "max")
    if rw_max is None:
        return []
    if horizon_age > rw_max:
        return []
    return [
        CrossFieldWarning(
            rule_id="horizon_past_retirement",
            fields=["monte_carlo.horizon_age", "client.retirement_window"],
            message=(
                f"Your planning horizon ({horizon_age}) doesn't extend past your "
                f"latest retirement age ({rw_max}). This may underestimate long-term needs."
            ),
            suggestion=f"Consider setting horizon to at least age {int(rw_max) + 5}.",
        )
    ]


def _check_full_match_capture(schema: CanonicalPlanSchema) -> list[CrossFieldWarning]:
    contrib = _pf_value(schema.accounts.employee_contribution_percent)
    match = _pf_value(schema.accounts.employer_match_percent)
    if contrib is None or match is None:
        return []
    if match <= 0:
        return []
    if contrib >= 2 * match:
        return []
    return [
        CrossFieldWarning(
            rule_id="full_match_capture",
            fields=[
                "accounts.employee_contribution_percent",
                "accounts.employer_match_percent",
            ],
            message=(
                f"Your contribution ({contrib}%) may not capture your full employer "
                f"match ({match}%). You may need at least {2 * match}% to maximize the match."
            ),
            suggestion="Consider increasing your contribution to capture the full match.",
        )
    ]


def _check_spending_vs_income(schema: CanonicalPlanSchema) -> list[CrossFieldWarning]:
    spending = _pf_value(schema.spending.retirement_monthly_real)
    annual_income = _pf_value(schema.income.current_gross_annual)
    if spending is None or annual_income is None:
        return []
    if annual_income <= 0:
        return []
    monthly_income = annual_income / 12
    if spending <= monthly_income:
        return []
    return [
        CrossFieldWarning(
            rule_id="spending_vs_income",
            fields=[
                "spending.retirement_monthly_real",
                "income.current_gross_annual",
            ],
            message=(
                f"Your planned retirement spending (${spending:,}/mo) exceeds your "
                f"current monthly gross income (${monthly_income:,.0f}/mo)."
            ),
            suggestion="This is unusual — verify your spending target is realistic.",
        )
    ]


def _check_legacy_vs_balance(schema: CanonicalPlanSchema) -> list[CrossFieldWarning]:
    legacy = _pf_value(schema.retirement_philosophy.legacy_goal_total_real)
    balance = _pf_value(schema.accounts.retirement_balance)
    if legacy is None or balance is None:
        return []
    if legacy <= 0 or balance <= 0:
        return []
    if legacy <= 10 * balance:
        return []
    return [
        CrossFieldWarning(
            rule_id="legacy_vs_balance",
            fields=[
                "retirement_philosophy.legacy_goal_total_real",
                "accounts.retirement_balance",
            ],
            message=(
                f"Your legacy goal (${legacy:,}) is more than 10x your current "
                f"balance (${balance:,})."
            ),
            suggestion="This is ambitious — consider whether this goal is realistic.",
        )
    ]


def run_cross_field_checks(schema: CanonicalPlanSchema) -> list[CrossFieldWarning]:
    """Run all cross-field rules and return active warnings."""
    warnings: list[CrossFieldWarning] = []
    warnings.extend(_check_ss_benefits_increase(schema))
    warnings.extend(_check_cannot_retire_in_past(schema))
    warnings.extend(_check_horizon_past_retirement(schema))
    warnings.extend(_check_full_match_capture(schema))
    warnings.extend(_check_spending_vs_income(schema))
    warnings.extend(_check_legacy_vs_balance(schema))
    return warnings
