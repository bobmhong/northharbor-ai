"""Tests for YAML plan_dataset migration to CanonicalPlanSchema."""

from pathlib import Path

import yaml

from backend.schema.canonical import NumericRange
from backend.schema.migrations import yaml_plan_to_canonical
from backend.schema.provenance import FieldSource

ADAM_PLAN_PATH = (
    Path(__file__).resolve().parents[4]
    / "retire-ai"
    / "plans"
    / "adam"
    / "plan_datasets"
    / "plan_dataset_v1.yaml"
)

ADAM_PLAN_INLINE = {
    "plan_dataset": {
        "version": 1,
        "created_date": "2026-02-19",
        "status": "intake_in_progress",
    },
    "clients": {
        "primary": {
            "name": "Adam",
            "birth_year": 2000,
            "current_age": {"min": 25, "max": 26},
            "retirement_window": {"min": 66, "max": 68},
        }
    },
    "location": {
        "state": "MI",
        "city": "Grand Rapids",
        "social_security_taxation": "exempt",
        "property_tax_estimate_annual": 0,
    },
    "income": {"current": {"gross_annual": 60000}, "scheduled_adjustments": []},
    "retirement_philosophy": {
        "success_probability_target": 0.95,
        "legacy_goal_total_real": 0,
        "preferred_retirement_age": 67,
        "flexibility": {
            "delay_retirement": True,
            "reduce_spending_in_downturn": True,
            "part_time_income": "none",
        },
    },
    "accounts": {
        "retirement": {
            "type": "roth_ira",
            "balance_current": 15000,
            "monthly_contribution": 200,
            "annual_contribution": 2400,
            "employee_contribution_percent": 4,
            "employer_match_percent": 0,
            "employer_non_elective_percent": 0,
            "total_savings_rate_percent": 4,
            "investment_strategy_id": "balanced_core",
        }
    },
    "housing": {"status": "renting", "monthly_rent": 1375},
    "spending": {
        "retirement_spending_monthly_real": 5000,
        "discretionary_adjustable": True,
        "current_monthly_spending": 2750,
        "retirement_budget_monthly": {
            "housing": 1375,
            "food": 600,
            "transportation": 300,
            "utilities": 300,
            "internet_phone": 150,
            "healthcare_out_of_pocket": 400,
            "home_maintenance": 200,
            "entertainment_travel": 500,
            "insurance": 200,
            "misc": 350,
        },
    },
    "planned_cashflows": [],
    "social_security": {
        "primary_at_67_monthly": 2300,
        "combined_at_67_monthly": 2300,
        "combined_at_70_monthly": 2850,
        "claiming_preference": 67,
        "confirmation_needed_from_ssa_statement": True,
    },
    "monte_carlo": {
        "required_success_rate": 0.95,
        "horizon_age": 95,
        "legacy_floor": 0,
    },
    "risk_summary": {
        "retirement_viable": "pending",
        "retirement_preferred_window": {"min": 66, "max": 68},
        "mitigation": "pending",
    },
}


class TestYamlPlanToCanonical:
    def test_inline_adam_plan(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.plan_id == "adam-001"
        assert schema.owner_id == "auth0|adam"
        assert schema.status == "intake_in_progress"

    def test_client_fields(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.client.name.value == "Adam"
        assert schema.client.name.source == FieldSource.PROVIDED
        assert schema.client.birth_year.value == 2000
        age_range = schema.client.current_age
        assert age_range is not None
        assert isinstance(age_range.value, NumericRange)
        assert age_range.value.min == 25.0
        assert age_range.value.max == 26.0

    def test_location_fields(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.location.state.value == "MI"
        assert schema.location.city.value == "Grand Rapids"
        assert schema.location.social_security_taxation is not None
        assert schema.location.social_security_taxation.value == "exempt"

    def test_income_fields(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.income.current_gross_annual.value == 60000
        assert schema.income.scheduled_adjustments == []

    def test_retirement_philosophy(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.retirement_philosophy.success_probability_target.value == 0.95
        assert schema.retirement_philosophy.preferred_retirement_age is not None
        assert schema.retirement_philosophy.preferred_retirement_age.value == 67
        assert schema.retirement_philosophy.flexibility.delay_retirement is True
        assert schema.retirement_philosophy.flexibility.part_time_income is None

    def test_accounts_fields(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.accounts.retirement_balance.value == 15000
        assert schema.accounts.savings_rate_percent.value == 4
        assert schema.accounts.retirement_type is not None
        assert schema.accounts.retirement_type.value == "roth_ira"
        assert schema.accounts.investment_strategy_id is not None
        assert schema.accounts.investment_strategy_id.value == "balanced_core"

    def test_housing_fields(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.housing.status is not None
        assert schema.housing.status.value == "renting"
        assert schema.housing.monthly_rent is not None
        assert schema.housing.monthly_rent.value == 1375
        assert schema.housing.mortgage_balance is None

    def test_spending_fields(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.spending.retirement_monthly_real.value == 5000
        assert len(schema.spending.budget_monthly) == 10
        assert schema.spending.budget_monthly["housing"].value == 1375

    def test_social_security_fields(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.social_security.combined_at_67_monthly.value == 2300
        assert schema.social_security.combined_at_70_monthly.value == 2850
        assert schema.social_security.claiming_preference is not None
        assert schema.social_security.claiming_preference.value == 67

    def test_monte_carlo_fields(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.monte_carlo.required_success_rate.value == 0.95
        assert schema.monte_carlo.horizon_age.value == 95
        assert schema.monte_carlo.legacy_floor.value == 0

    def test_risk_summary(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.risk_summary.retirement_viable is not None
        assert schema.risk_summary.retirement_viable.value == "pending"
        assert schema.risk_summary.retirement_preferred_window is not None
        window = schema.risk_summary.retirement_preferred_window.value
        assert isinstance(window, NumericRange)
        assert window.min == 66.0

    def test_empty_planned_cashflows(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.planned_cashflows == []

    def test_provenance_source_is_provided(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.client.name.source == FieldSource.PROVIDED
        assert schema.income.current_gross_annual.source == FieldSource.PROVIDED

    def test_schema_version(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        assert schema.schema_version == "1.0"

    def test_serialization_roundtrip(self) -> None:
        schema = yaml_plan_to_canonical(
            ADAM_PLAN_INLINE, plan_id="adam-001", owner_id="auth0|adam"
        )
        data = schema.model_dump(mode="json")
        restored = type(schema).model_validate(data)
        assert restored.plan_id == schema.plan_id
        assert restored.client.name.value == "Adam"
        assert len(restored.spending.budget_monthly) == 10

    def test_from_yaml_file(self) -> None:
        """Load Adam's actual YAML file if available in the workspace."""
        if not ADAM_PLAN_PATH.exists():
            import pytest

            pytest.skip("retire-ai plan file not in workspace")

        with open(ADAM_PLAN_PATH) as f:
            data = yaml.safe_load(f)

        schema = yaml_plan_to_canonical(
            data, plan_id="adam-file", owner_id="auth0|adam"
        )
        assert schema.client.name.value == "Adam"
        assert schema.client.birth_year.value == 2000

    def test_missing_sections_use_defaults(self) -> None:
        minimal = {
            "clients": {
                "primary": {
                    "name": "Min",
                    "birth_year": 1980,
                    "retirement_window": {"min": 65, "max": 67},
                }
            },
            "income": {"current": {"gross_annual": 50000}},
            "accounts": {"retirement": {"balance_current": 10000, "total_savings_rate_percent": 5}},
            "spending": {"retirement_spending_monthly_real": 3000},
            "social_security": {
                "combined_at_67_monthly": 2000,
                "combined_at_70_monthly": 2500,
            },
            "monte_carlo": {
                "required_success_rate": 0.9,
                "horizon_age": 90,
                "legacy_floor": 0,
            },
        }
        schema = yaml_plan_to_canonical(
            minimal, plan_id="min-001", owner_id="auth0|min"
        )
        assert schema.location.state.value == ""
        assert schema.housing.status is None
        assert schema.risk_summary.retirement_viable is None
