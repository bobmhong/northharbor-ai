"""Normalization stage -- converts schema fields into pipeline-ready format."""

from __future__ import annotations

from typing import Any

from backend.schema.canonical import CanonicalPlanSchema
from backend.schema.provenance import ProvenanceField


def _pf_val(pf: ProvenanceField | None, default: Any = None) -> Any:
    if pf is None:
        return default
    return pf.value if pf.value is not None else default


def normalize_inputs(schema: CanonicalPlanSchema) -> dict[str, Any]:
    """Extract raw numeric values from provenance-wrapped fields.

    Returns a flat dict suitable for computation stages.
    """
    retirement_window = _pf_val(schema.client.retirement_window)
    if retirement_window is not None and hasattr(retirement_window, "min"):
        retirement_ages = list(
            range(int(retirement_window.min), int(retirement_window.max) + 1)
        )
    else:
        retirement_ages = [65, 66, 67]

    claiming_pref = _pf_val(schema.social_security.claiming_preference, 67)
    if isinstance(claiming_pref, str):
        import re
        match = re.search(r"(\d+)", claiming_pref)
        claiming_pref = int(match.group(1)) if match else 67
    claiming_age = min(max(int(claiming_pref), 62), 70)

    ss_67 = float(_pf_val(schema.social_security.combined_at_67_monthly, 0))
    ss_70 = float(_pf_val(schema.social_security.combined_at_70_monthly, 0))

    mc = schema.monte_carlo
    inflation = float(_pf_val(mc.inflation_assumption, 0.025))
    return_mean_raw = _pf_val(mc.return_assumption_real_mean)
    nominal_raw = _pf_val(mc.return_assumption_nominal)
    if return_mean_raw is not None:
        return_mean = float(return_mean_raw)
    elif nominal_raw is not None:
        return_mean = float(nominal_raw) - inflation
    else:
        return_mean = 0.055

    birth_year = int(_pf_val(schema.client.birth_year, 1970))
    start_age = max(retirement_ages[0] - 5, birth_year and (2026 - birth_year) or 56)

    # Calculate total savings rate from employee contribution + employer match
    # Fall back to savings_rate_percent if the new fields aren't populated
    employee_contrib = float(_pf_val(schema.accounts.employee_contribution_percent, 0))
    employer_match = float(_pf_val(schema.accounts.employer_match_percent, 0))
    legacy_savings_rate = float(_pf_val(schema.accounts.savings_rate_percent, 0))
    
    # Use new fields if employee contribution is set, otherwise use legacy field
    total_savings_rate = (employee_contrib + employer_match) if employee_contrib > 0 else legacy_savings_rate

    return {
        "plan_id": schema.plan_id,
        "birth_year": birth_year,
        "start_age": start_age,
        "retirement_ages": retirement_ages,
        "current_balance": float(_pf_val(schema.accounts.retirement_balance, 0)),
        "savings_rate_percent": total_savings_rate,
        "gross_annual_income": float(
            _pf_val(schema.income.current_gross_annual, 0)
        ),
        "retirement_spending_monthly_real": float(
            _pf_val(schema.spending.retirement_monthly_real, 0)
        ),
        "social_security_age_67_monthly": ss_67,
        "social_security_age_70_monthly": ss_70,
        "social_security_age_67_annual": ss_67 * 12.0,
        "social_security_age_70_annual": ss_70 * 12.0,
        "social_security_claiming_age": claiming_age,
        "return_mean": return_mean,
        "return_std_dev": 0.11,
        "inflation_assumption": inflation,
        "longevity_age": int(_pf_val(mc.horizon_age, 95)),
        "legacy_floor": float(_pf_val(mc.legacy_floor, 0)),
        "required_success_probability": float(
            _pf_val(mc.required_success_rate)
            or _pf_val(schema.retirement_philosophy.success_probability_target, 0.95)
        ),
        "simulation_count": 10_000,
    }
