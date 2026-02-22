"""Canonical plan schema -- the single source of truth for plan data.

All computation reads from this schema.  AI proposes structured patches;
the system validates and applies them.  No computation logic lives here.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from backend.schema.provenance import ProvenanceField


class NumericRange(BaseModel):
    """A min/max numeric range (e.g. retirement window, age range)."""

    min: float
    max: float


class FlexibilityOptions(BaseModel):
    """Client flexibility preferences for retirement planning."""

    delay_retirement: bool = False
    reduce_spending_in_downturn: bool = False
    part_time_income: str | None = None


class ClientProfile(BaseModel):
    """Primary client demographics."""

    name: ProvenanceField
    birth_year: ProvenanceField
    current_age: ProvenanceField | None = None
    retirement_window: ProvenanceField


class LocationProfile(BaseModel):
    """Geographic and tax-related location info."""

    state: ProvenanceField
    city: ProvenanceField
    social_security_taxation: ProvenanceField | None = None
    property_tax_estimate_annual: ProvenanceField | None = None


class IncomeProfile(BaseModel):
    """Current and projected income."""

    current_gross_annual: ProvenanceField
    scheduled_adjustments: list[dict[str, Any]] = Field(default_factory=list)
    growth_rate_nominal: ProvenanceField | None = None


class RetirementPhilosophy(BaseModel):
    """Goals and preferences for retirement planning."""

    success_probability_target: ProvenanceField
    legacy_goal_total_real: ProvenanceField
    preferred_retirement_age: ProvenanceField | None = None
    flexibility: FlexibilityOptions = Field(
        default_factory=FlexibilityOptions
    )


class AccountsProfile(BaseModel):
    """Retirement account details."""

    retirement_type: ProvenanceField | None = None
    retirement_balance: ProvenanceField
    has_employer_plan: ProvenanceField | None = None
    monthly_contribution: ProvenanceField | None = None
    annual_contribution: ProvenanceField | None = None
    employee_contribution_percent: ProvenanceField | None = None
    employer_match_percent: ProvenanceField | None = None
    employer_non_elective_percent: ProvenanceField | None = None
    savings_rate_percent: ProvenanceField
    investment_strategy_id: ProvenanceField | None = None


class HousingProfile(BaseModel):
    """Housing situation -- rental or mortgage."""

    status: ProvenanceField | None = None
    monthly_rent: ProvenanceField | None = None
    mortgage_balance: ProvenanceField | None = None
    mortgage_rate: ProvenanceField | None = None
    mortgage_term_years: ProvenanceField | None = None
    mortgage_payment_monthly: ProvenanceField | None = None
    homeowners_insurance_annual: ProvenanceField | None = None


class SpendingProfile(BaseModel):
    """Spending targets and budget breakdown."""

    retirement_monthly_real: ProvenanceField
    discretionary_adjustable: ProvenanceField | None = None
    current_monthly_spending: ProvenanceField | None = None
    budget_monthly: dict[str, ProvenanceField] = Field(default_factory=dict)


class PlannedCashflow(BaseModel):
    """A planned future income or expense event."""

    type: Literal["income", "expense"]
    amount: float = Field(ge=0.0)
    start_date: str
    duration_months: int = Field(gt=0)
    cadence: str = "monthly"
    currency_basis: str = "nominal"
    tax_treatment: str = "tax_neutral"
    apply_in_stress_scenarios: bool = True


class SocialSecurityProfile(BaseModel):
    """Social Security benefit estimates and claiming strategy."""

    primary_at_67_monthly: ProvenanceField | None = None
    combined_at_67_monthly: ProvenanceField
    combined_at_70_monthly: ProvenanceField
    claiming_preference: ProvenanceField | None = None
    confirmation_needed: ProvenanceField | None = None


class MonteCarloConfig(BaseModel):
    """Monte Carlo simulation parameters."""

    required_success_rate: ProvenanceField
    horizon_age: ProvenanceField
    legacy_floor: ProvenanceField
    return_assumption_real_mean: ProvenanceField | None = None
    return_assumption_nominal: ProvenanceField | None = None
    inflation_assumption: ProvenanceField | None = None


class RiskSummary(BaseModel):
    """High-level risk assessment."""

    retirement_viable: ProvenanceField | None = None
    retirement_preferred_window: ProvenanceField | None = None
    mitigation: ProvenanceField | None = None


PlanStatus = Literal[
    "intake_in_progress",
    "intake_complete",
    "analysis_ready",
    "review",
    "finalized",
]


class CanonicalPlanSchema(BaseModel):
    """v1 canonical plan schema -- the single source of truth.

    ``owner_id`` is the tenant isolation key (Auth0 ``sub``).
    """

    schema_version: str = "1.0"
    version: int = 1
    plan_id: str
    owner_id: str
    scenario_name: str = "Default"
    base_plan_id: str | None = None
    status: PlanStatus = "intake_in_progress"
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    client: ClientProfile
    location: LocationProfile
    income: IncomeProfile
    retirement_philosophy: RetirementPhilosophy
    accounts: AccountsProfile
    housing: HousingProfile
    spending: SpendingProfile
    social_security: SocialSecurityProfile
    monte_carlo: MonteCarloConfig
    planned_cashflows: list[PlannedCashflow] = Field(default_factory=list)
    risk_summary: RiskSummary = Field(default_factory=RiskSummary)
    advisor_interview: dict[str, Any] = Field(default_factory=dict)
    additional_considerations: ProvenanceField | None = None
