"""Migrate retire-ai YAML plan datasets to CanonicalPlanSchema.

This module converts the flat YAML format used by the predecessor
``retire-ai`` CLI into strongly-typed Pydantic models with provenance
tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.schema.canonical import (
    AccountsProfile,
    CanonicalPlanSchema,
    ClientProfile,
    FlexibilityOptions,
    HousingProfile,
    IncomeProfile,
    LocationProfile,
    MonteCarloConfig,
    NumericRange,
    PlanStatus,
    PlannedCashflow,
    RetirementPhilosophy,
    RiskSummary,
    SocialSecurityProfile,
    SpendingProfile,
)
from backend.schema.provenance import FieldSource, ProvenanceField


def _pf(
    value: Any, source: FieldSource = FieldSource.PROVIDED
) -> ProvenanceField:
    return ProvenanceField(value=value, source=source, confidence=1.0)


def _pf_optional(
    value: Any, source: FieldSource = FieldSource.PROVIDED
) -> ProvenanceField | None:
    if value is None:
        return None
    return _pf(value, source)


def _to_range(data: Any) -> NumericRange | None:
    if isinstance(data, dict) and "min" in data and "max" in data:
        return NumericRange(min=float(data["min"]), max=float(data["max"]))
    return None


_STATUS_MAP: dict[str, PlanStatus] = {
    "intake_in_progress": "intake_in_progress",
    "intake_complete": "intake_complete",
    "analysis_ready": "analysis_ready",
    "review": "review",
    "finalized": "finalized",
}


def yaml_plan_to_canonical(
    data: dict[str, Any],
    *,
    plan_id: str,
    owner_id: str,
) -> CanonicalPlanSchema:
    """Convert a retire-ai YAML plan_dataset dict to ``CanonicalPlanSchema``."""
    now = datetime.now(timezone.utc)
    src = FieldSource.PROVIDED

    meta = data.get("plan_dataset", {})
    status: PlanStatus = _STATUS_MAP.get(
        str(meta.get("status", "intake_in_progress")),
        "intake_in_progress",
    )

    # --- Client ---
    primary = data.get("clients", {}).get("primary", {})
    retirement_window = _to_range(primary.get("retirement_window"))
    if retirement_window is None:
        retirement_window = NumericRange(min=65.0, max=67.0)
    current_age = _to_range(primary.get("current_age"))

    client = ClientProfile(
        name=_pf(primary.get("name", ""), src),
        birth_year=_pf(primary.get("birth_year", 0), src),
        current_age=_pf(current_age, src) if current_age else None,
        retirement_window=_pf(retirement_window, src),
    )

    # --- Location ---
    loc = data.get("location", {})
    location = LocationProfile(
        state=_pf(loc.get("state", ""), src),
        city=_pf(loc.get("city", ""), src),
        social_security_taxation=_pf_optional(
            loc.get("social_security_taxation"), src
        ),
        property_tax_estimate_annual=_pf_optional(
            loc.get("property_tax_estimate_annual"), src
        ),
    )

    # --- Income ---
    inc = data.get("income", {})
    current_inc = inc.get("current", {})
    income = IncomeProfile(
        current_gross_annual=_pf(current_inc.get("gross_annual", 0), src),
        scheduled_adjustments=inc.get("scheduled_adjustments", []),
        growth_rate_nominal=_pf_optional(
            inc.get("income_growth_rate_assumption_nominal"), src
        ),
    )

    # --- Retirement Philosophy ---
    phil = data.get("retirement_philosophy", {})
    flex = phil.get("flexibility", {})
    part_time = flex.get("part_time_income")
    flexibility = FlexibilityOptions(
        delay_retirement=flex.get("delay_retirement", False),
        reduce_spending_in_downturn=flex.get(
            "reduce_spending_in_downturn", False
        ),
        part_time_income=part_time
        if isinstance(part_time, str) and part_time != "none"
        else None,
    )
    retirement_philosophy = RetirementPhilosophy(
        success_probability_target=_pf(
            phil.get("success_probability_target", 0.95), src
        ),
        legacy_goal_total_real=_pf(
            phil.get("legacy_goal_total_real", 0), src
        ),
        preferred_retirement_age=_pf_optional(
            phil.get("preferred_retirement_age"), src
        ),
        flexibility=flexibility,
    )

    # --- Accounts ---
    ret_acct = data.get("accounts", {}).get("retirement", {})
    accounts = AccountsProfile(
        retirement_type=_pf_optional(ret_acct.get("type"), src),
        retirement_balance=_pf(ret_acct.get("balance_current", 0), src),
        monthly_contribution=_pf_optional(
            ret_acct.get("monthly_contribution"), src
        ),
        annual_contribution=_pf_optional(
            ret_acct.get("annual_contribution"), src
        ),
        employee_contribution_percent=_pf_optional(
            ret_acct.get("employee_contribution_percent"), src
        ),
        employer_match_percent=_pf_optional(
            ret_acct.get("employer_match_percent"), src
        ),
        employer_non_elective_percent=_pf_optional(
            ret_acct.get("employer_non_elective_percent"), src
        ),
        savings_rate_percent=_pf(
            ret_acct.get("total_savings_rate_percent", 0), src
        ),
        investment_strategy_id=_pf_optional(
            ret_acct.get("investment_strategy_id"), src
        ),
    )

    # --- Housing ---
    h = data.get("housing", {})
    housing = HousingProfile(
        status=_pf_optional(h.get("status"), src),
        monthly_rent=_pf_optional(h.get("monthly_rent"), src),
        mortgage_balance=_pf_optional(
            h.get("mortgage_balance_estimate"), src
        ),
        mortgage_rate=_pf_optional(
            h.get("mortgage_rate_assumption_nominal"), src
        ),
        mortgage_term_years=_pf_optional(h.get("mortgage_term_years"), src),
        mortgage_payment_monthly=_pf_optional(
            h.get("mortgage_payment_estimate_monthly"), src
        ),
        homeowners_insurance_annual=_pf_optional(
            h.get("homeowners_insurance_estimate_annual"), src
        ),
    )

    # --- Spending ---
    sp = data.get("spending", {})
    budget_raw = sp.get("retirement_budget_monthly", {})
    budget_monthly = (
        {k: _pf(v, src) for k, v in budget_raw.items()}
        if isinstance(budget_raw, dict)
        else {}
    )
    spending = SpendingProfile(
        retirement_monthly_real=_pf(
            sp.get("retirement_spending_monthly_real", 0), src
        ),
        discretionary_adjustable=_pf_optional(
            sp.get("discretionary_adjustable"), src
        ),
        current_monthly_spending=_pf_optional(
            sp.get("current_monthly_spending"), src
        ),
        budget_monthly=budget_monthly,
    )

    # --- Planned Cashflows ---
    cashflows_raw = data.get("planned_cashflows", [])
    planned_cashflows: list[PlannedCashflow] = []
    if isinstance(cashflows_raw, list):
        for cf in cashflows_raw:
            if isinstance(cf, dict):
                planned_cashflows.append(
                    PlannedCashflow(
                        type=cf.get("type", "expense"),
                        amount=float(cf.get("amount", 0)),
                        start_date=str(cf.get("start_date", "")),
                        duration_months=int(cf.get("duration_months", 1)),
                        cadence=cf.get("cadence", "monthly"),
                        currency_basis=cf.get("currency_basis", "nominal"),
                        tax_treatment=cf.get("tax_treatment", "tax_neutral"),
                        apply_in_stress_scenarios=cf.get(
                            "apply_in_stress_scenarios", True
                        ),
                    )
                )

    # --- Social Security ---
    ss = data.get("social_security", {})
    social_security = SocialSecurityProfile(
        primary_at_67_monthly=_pf_optional(
            ss.get("primary_at_67_monthly"), src
        ),
        combined_at_67_monthly=_pf(
            ss.get("combined_at_67_monthly", 0), src
        ),
        combined_at_70_monthly=_pf(
            ss.get("combined_at_70_monthly", 0), src
        ),
        claiming_preference=_pf_optional(
            ss.get("claiming_preference"), src
        ),
        confirmation_needed=_pf_optional(
            ss.get("confirmation_needed_from_ssa_statement"), src
        ),
    )

    # --- Monte Carlo ---
    mc = data.get("monte_carlo", {})
    monte_carlo = MonteCarloConfig(
        required_success_rate=_pf(
            mc.get("required_success_rate", 0.95), src
        ),
        horizon_age=_pf(mc.get("horizon_age", 95), src),
        legacy_floor=_pf(mc.get("legacy_floor", 0), src),
        return_assumption_real_mean=_pf_optional(
            mc.get("return_assumption_real_mean"), src
        ),
        return_assumption_nominal=_pf_optional(
            mc.get("return_assumption_nominal"), src
        ),
        inflation_assumption=_pf_optional(
            mc.get("inflation_assumption"), src
        ),
    )

    # --- Risk Summary ---
    risk = data.get("risk_summary", {})
    preferred_window = _to_range(risk.get("retirement_preferred_window"))
    risk_summary = RiskSummary(
        retirement_viable=_pf_optional(risk.get("retirement_viable"), src),
        retirement_preferred_window=_pf(preferred_window, src)
        if preferred_window
        else None,
        mitigation=_pf_optional(risk.get("mitigation"), src),
    )

    return CanonicalPlanSchema(
        plan_id=plan_id,
        owner_id=owner_id,
        status=status,
        created_at=now,
        updated_at=now,
        client=client,
        location=location,
        income=income,
        retirement_philosophy=retirement_philosophy,
        accounts=accounts,
        housing=housing,
        spending=spending,
        social_security=social_security,
        monte_carlo=monte_carlo,
        planned_cashflows=planned_cashflows,
        risk_summary=risk_summary,
        advisor_interview=data.get("advisor_interview", {}),
    )
