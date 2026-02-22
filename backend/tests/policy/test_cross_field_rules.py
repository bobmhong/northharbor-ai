"""Tests for cross-field validation rules."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.policy.cross_field_rules import run_cross_field_checks
from backend.schema.canonical import (
    AccountsProfile,
    CanonicalPlanSchema,
    ClientProfile,
    HousingProfile,
    IncomeProfile,
    LocationProfile,
    MonteCarloConfig,
    NumericRange,
    RetirementPhilosophy,
    SocialSecurityProfile,
    SpendingProfile,
)
from backend.schema.patch_ops import PatchOp, apply_patches
from backend.schema.provenance import FieldSource, ProvenanceField


def _default_pf(value: object = None) -> ProvenanceField:
    return ProvenanceField(value=value, source=FieldSource.DEFAULT, confidence=0.0)


def _make_schema() -> CanonicalPlanSchema:
    now = datetime.now(timezone.utc)
    return CanonicalPlanSchema(
        plan_id="plan-test",
        owner_id="anonymous",
        created_at=now,
        updated_at=now,
        client=ClientProfile(
            name=_default_pf(),
            birth_year=_default_pf(0),
            retirement_window=_default_pf(NumericRange(min=65, max=67)),
        ),
        location=LocationProfile(state=_default_pf(), city=_default_pf()),
        income=IncomeProfile(current_gross_annual=_default_pf(0)),
        retirement_philosophy=RetirementPhilosophy(
            success_probability_target=_default_pf(0.95),
            legacy_goal_total_real=_default_pf(0),
        ),
        accounts=AccountsProfile(
            retirement_balance=_default_pf(0),
            savings_rate_percent=_default_pf(0),
        ),
        housing=HousingProfile(),
        spending=SpendingProfile(retirement_monthly_real=_default_pf(0)),
        social_security=SocialSecurityProfile(
            combined_at_67_monthly=_default_pf(0),
            combined_at_70_monthly=_default_pf(0),
        ),
        monte_carlo=MonteCarloConfig(
            required_success_rate=_default_pf(0.95),
            horizon_age=_default_pf(95),
            legacy_floor=_default_pf(0),
        ),
    )


def _set_fields(schema: CanonicalPlanSchema, patches: list[PatchOp]) -> CanonicalPlanSchema:
    updated, _ = apply_patches(schema, patches)
    return updated


class TestCrossFieldRules(unittest.TestCase):
    """Tests for run_cross_field_checks."""

    def test_ss_benefits_increase_warns(self) -> None:
        schema = _set_fields(_make_schema(), [
            PatchOp(op="set", path="social_security.combined_at_67_monthly", value=4200, confidence=0.85),
            PatchOp(op="set", path="social_security.combined_at_70_monthly", value=3800, confidence=0.85),
        ])

        warnings = run_cross_field_checks(schema)

        rule_ids = [w.rule_id for w in warnings]
        self.assertIn("ss_benefits_increase", rule_ids)

    def test_ss_benefits_normal_no_warning(self) -> None:
        schema = _set_fields(_make_schema(), [
            PatchOp(op="set", path="social_security.combined_at_67_monthly", value=4200, confidence=0.85),
            PatchOp(op="set", path="social_security.combined_at_70_monthly", value=5300, confidence=0.85),
        ])

        warnings = run_cross_field_checks(schema)

        rule_ids = [w.rule_id for w in warnings]
        self.assertNotIn("ss_benefits_increase", rule_ids)

    def test_cannot_retire_in_past_warns(self) -> None:
        current_year = datetime.now(timezone.utc).year
        retire_age = current_year - 1960 + 1  # ensures retire year is in the past
        schema = _set_fields(_make_schema(), [
            PatchOp(op="set", path="client.birth_year", value=1960, confidence=0.85),
            PatchOp(op="set", path="client.retirement_window",
                    value=NumericRange(min=60, max=62).model_dump(), confidence=0.85),
        ])

        warnings = run_cross_field_checks(schema)

        rule_ids = [w.rule_id for w in warnings]
        self.assertIn("cannot_retire_in_past", rule_ids)

    def test_horizon_past_retirement_warns(self) -> None:
        schema = _set_fields(_make_schema(), [
            PatchOp(op="set", path="monte_carlo.horizon_age", value=65, confidence=0.85),
            PatchOp(op="set", path="client.retirement_window",
                    value=NumericRange(min=65, max=67).model_dump(), confidence=0.85),
        ])

        warnings = run_cross_field_checks(schema)

        rule_ids = [w.rule_id for w in warnings]
        self.assertIn("horizon_past_retirement", rule_ids)

    def test_full_match_capture_warns(self) -> None:
        schema = _set_fields(_make_schema(), [
            PatchOp(op="set", path="accounts.employee_contribution_percent", value=3, confidence=0.85),
            PatchOp(op="set", path="accounts.employer_match_percent", value=5, confidence=0.85),
        ])

        warnings = run_cross_field_checks(schema)

        rule_ids = [w.rule_id for w in warnings]
        self.assertIn("full_match_capture", rule_ids)

    def test_spending_vs_income_warns(self) -> None:
        schema = _set_fields(_make_schema(), [
            PatchOp(op="set", path="spending.retirement_monthly_real", value=20000, confidence=0.85),
            PatchOp(op="set", path="income.current_gross_annual", value=100000, confidence=0.85),
        ])

        warnings = run_cross_field_checks(schema)

        rule_ids = [w.rule_id for w in warnings]
        self.assertIn("spending_vs_income", rule_ids)

    def test_legacy_vs_balance_warns(self) -> None:
        schema = _set_fields(_make_schema(), [
            PatchOp(op="set", path="retirement_philosophy.legacy_goal_total_real", value=5_000_000, confidence=0.85),
            PatchOp(op="set", path="accounts.retirement_balance", value=100_000, confidence=0.85),
        ])

        warnings = run_cross_field_checks(schema)

        rule_ids = [w.rule_id for w in warnings]
        self.assertIn("legacy_vs_balance", rule_ids)

    def test_no_warnings_for_empty_schema(self) -> None:
        schema = _make_schema()
        schema, _ = apply_patches(schema, [
            PatchOp(op="set", path="client.birth_year", value=None, confidence=0.0),
        ])

        warnings = run_cross_field_checks(schema)

        self.assertEqual(warnings, [])


if __name__ == "__main__":
    unittest.main()
