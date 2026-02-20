"""Tests for canonical plan schema models."""

from datetime import datetime, timezone

import pytest

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
    PlannedCashflow,
    RetirementPhilosophy,
    RiskSummary,
    SocialSecurityProfile,
    SpendingProfile,
)
from backend.schema.provenance import FieldSource, ProvenanceField


def _pf(value, source=FieldSource.USER):
    return ProvenanceField(value=value, source=source)


def _make_minimal_schema(**overrides):
    """Build a minimal valid CanonicalPlanSchema."""
    defaults = dict(
        plan_id="plan-001",
        owner_id="auth0|user1",
        client=ClientProfile(
            name=_pf("Test User"),
            birth_year=_pf(1990),
            retirement_window=_pf(NumericRange(min=65, max=67)),
        ),
        location=LocationProfile(
            state=_pf("MI"),
            city=_pf("Grand Rapids"),
        ),
        income=IncomeProfile(current_gross_annual=_pf(60000)),
        retirement_philosophy=RetirementPhilosophy(
            success_probability_target=_pf(0.95),
            legacy_goal_total_real=_pf(0),
        ),
        accounts=AccountsProfile(
            retirement_balance=_pf(15000),
            savings_rate_percent=_pf(4),
        ),
        housing=HousingProfile(),
        spending=SpendingProfile(retirement_monthly_real=_pf(5000)),
        social_security=SocialSecurityProfile(
            combined_at_67_monthly=_pf(2300),
            combined_at_70_monthly=_pf(2850),
        ),
        monte_carlo=MonteCarloConfig(
            required_success_rate=_pf(0.95),
            horizon_age=_pf(95),
            legacy_floor=_pf(0),
        ),
    )
    defaults.update(overrides)
    return CanonicalPlanSchema(**defaults)


class TestNumericRange:
    def test_construction(self) -> None:
        r = NumericRange(min=25, max=26)
        assert r.min == 25.0
        assert r.max == 26.0

    def test_serialization(self) -> None:
        r = NumericRange(min=65, max=67)
        data = r.model_dump()
        assert data == {"min": 65.0, "max": 67.0}


class TestClientProfile:
    def test_required_fields(self) -> None:
        with pytest.raises(Exception):
            ClientProfile(name=_pf("Bob"))

    def test_optional_current_age(self) -> None:
        cp = ClientProfile(
            name=_pf("Bob"),
            birth_year=_pf(2000),
            retirement_window=_pf(NumericRange(min=66, max=68)),
        )
        assert cp.current_age is None


class TestPlannedCashflow:
    def test_valid_cashflow(self) -> None:
        cf = PlannedCashflow(
            type="income",
            amount=500.0,
            start_date="2030-01",
            duration_months=12,
        )
        assert cf.type == "income"
        assert cf.cadence == "monthly"

    def test_invalid_type(self) -> None:
        with pytest.raises(Exception):
            PlannedCashflow(
                type="other",
                amount=100,
                start_date="2030-01",
                duration_months=6,
            )

    def test_negative_amount_rejected(self) -> None:
        with pytest.raises(Exception):
            PlannedCashflow(
                type="expense",
                amount=-100,
                start_date="2030-01",
                duration_months=6,
            )

    def test_zero_duration_rejected(self) -> None:
        with pytest.raises(Exception):
            PlannedCashflow(
                type="expense",
                amount=100,
                start_date="2030-01",
                duration_months=0,
            )


class TestCanonicalPlanSchema:
    def test_minimal_construction(self) -> None:
        schema = _make_minimal_schema()
        assert schema.plan_id == "plan-001"
        assert schema.owner_id == "auth0|user1"
        assert schema.schema_version == "1.0"
        assert schema.status == "intake_in_progress"

    def test_default_status(self) -> None:
        schema = _make_minimal_schema()
        assert schema.status == "intake_in_progress"

    def test_status_values(self) -> None:
        for status in [
            "intake_in_progress",
            "intake_complete",
            "analysis_ready",
            "review",
            "finalized",
        ]:
            schema = _make_minimal_schema(status=status)
            assert schema.status == status

    def test_invalid_status_rejected(self) -> None:
        with pytest.raises(Exception):
            _make_minimal_schema(status="bogus")

    def test_timestamps_auto_populated(self) -> None:
        schema = _make_minimal_schema()
        assert isinstance(schema.created_at, datetime)
        assert isinstance(schema.updated_at, datetime)

    def test_empty_planned_cashflows(self) -> None:
        schema = _make_minimal_schema()
        assert schema.planned_cashflows == []

    def test_empty_advisor_interview(self) -> None:
        schema = _make_minimal_schema()
        assert schema.advisor_interview == {}

    def test_budget_monthly_dict(self) -> None:
        schema = _make_minimal_schema(
            spending=SpendingProfile(
                retirement_monthly_real=_pf(5000),
                budget_monthly={
                    "housing": _pf(1375),
                    "food": _pf(600),
                },
            ),
        )
        assert "housing" in schema.spending.budget_monthly
        assert schema.spending.budget_monthly["housing"].value == 1375

    def test_serialization_roundtrip(self) -> None:
        schema = _make_minimal_schema()
        data = schema.model_dump(mode="json")
        restored = CanonicalPlanSchema.model_validate(data)
        assert restored.plan_id == schema.plan_id
        assert restored.client.name.value == schema.client.name.value

    def test_flexibility_defaults(self) -> None:
        schema = _make_minimal_schema()
        flex = schema.retirement_philosophy.flexibility
        assert isinstance(flex, FlexibilityOptions)
        assert flex.delay_retirement is False

    def test_risk_summary_defaults(self) -> None:
        schema = _make_minimal_schema()
        assert schema.risk_summary.retirement_viable is None
        assert schema.risk_summary.mitigation is None
