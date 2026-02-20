"""Tests for PatchOp validation and apply_patches."""

import pytest

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
from backend.schema.patch_ops import (
    PatchOp,
    PatchResponse,
    PatchResult,
    apply_patches,
)
from backend.schema.provenance import FieldSource, ProvenanceField


def _pf(value, source=FieldSource.USER):
    return ProvenanceField(value=value, source=source)


def _make_schema():
    return CanonicalPlanSchema(
        plan_id="plan-001",
        owner_id="auth0|user1",
        client=ClientProfile(
            name=_pf("Adam"),
            birth_year=_pf(2000),
            retirement_window=_pf(NumericRange(min=66, max=68)),
        ),
        location=LocationProfile(state=_pf("MI"), city=_pf("Grand Rapids")),
        income=IncomeProfile(current_gross_annual=_pf(60000)),
        retirement_philosophy=RetirementPhilosophy(
            success_probability_target=_pf(0.95),
            legacy_goal_total_real=_pf(0),
        ),
        accounts=AccountsProfile(
            retirement_balance=_pf(15000), savings_rate_percent=_pf(4)
        ),
        housing=HousingProfile(status=_pf("renting"), monthly_rent=_pf(1375)),
        spending=SpendingProfile(
            retirement_monthly_real=_pf(5000),
            budget_monthly={"housing": _pf(1375), "food": _pf(600)},
        ),
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


class TestPatchOpModel:
    def test_valid_set(self) -> None:
        op = PatchOp(op="set", path="client.name", value="Bob")
        assert op.op == "set"
        assert op.path == "client.name"

    def test_valid_remove(self) -> None:
        op = PatchOp(op="remove", path="housing.monthly_rent")
        assert op.op == "remove"

    def test_valid_append(self) -> None:
        op = PatchOp(
            op="append",
            path="planned_cashflows",
            value={"type": "income", "amount": 500},
        )
        assert op.op == "append"

    def test_invalid_op_rejected(self) -> None:
        with pytest.raises(Exception):
            PatchOp(op="update", path="client.name", value="X")

    def test_confidence_bounds(self) -> None:
        PatchOp(op="set", path="x", value=1, confidence=0.0)
        PatchOp(op="set", path="x", value=1, confidence=1.0)
        with pytest.raises(Exception):
            PatchOp(op="set", path="x", value=1, confidence=1.5)
        with pytest.raises(Exception):
            PatchOp(op="set", path="x", value=1, confidence=-0.1)


class TestPatchResponse:
    def test_construction(self) -> None:
        resp = PatchResponse(
            patch_ops=[PatchOp(op="set", path="client.name", value="Bob")],
            next_question="What is your birth year?",
            missing_fields=["client.birth_year"],
            rationale="Name captured from user input.",
        )
        assert len(resp.patch_ops) == 1
        assert resp.next_question is not None
        assert "birth_year" in resp.missing_fields[0]


class TestApplyPatches:
    def test_set_provenance_field(self) -> None:
        schema = _make_schema()
        patches = [PatchOp(op="set", path="client.name", value="Bob")]
        updated, result = apply_patches(schema, patches)

        assert len(result.applied) == 1
        assert len(result.rejected) == 0
        assert updated.client.name.value == "Bob"
        assert updated.client.name.source == FieldSource.USER
        # original unchanged
        assert schema.client.name.value == "Adam"

    def test_set_with_source_and_confidence(self) -> None:
        schema = _make_schema()
        patches = [
            PatchOp(
                op="set",
                path="client.birth_year",
                value=1995,
                source=FieldSource.INFERRED,
                confidence=0.7,
            )
        ]
        updated, result = apply_patches(schema, patches)
        assert updated.client.birth_year.value == 1995
        assert updated.client.birth_year.source == FieldSource.INFERRED
        assert updated.client.birth_year.confidence == 0.7

    def test_set_nested_dict_key(self) -> None:
        schema = _make_schema()
        patches = [
            PatchOp(op="set", path="spending.budget_monthly.food", value=700)
        ]
        updated, result = apply_patches(schema, patches)
        assert updated.spending.budget_monthly["food"].value == 700

    def test_set_new_dict_key(self) -> None:
        schema = _make_schema()
        patches = [
            PatchOp(
                op="set",
                path="spending.budget_monthly.transportation",
                value=300,
            )
        ]
        updated, result = apply_patches(schema, patches)
        assert "transportation" in updated.spending.budget_monthly
        assert updated.spending.budget_monthly["transportation"].value == 300

    def test_invalid_path_rejected(self) -> None:
        schema = _make_schema()
        patches = [
            PatchOp(op="set", path="client.nonexistent", value="x")
        ]
        _, result = apply_patches(schema, patches)
        assert len(result.rejected) == 1
        assert "Unknown field" in result.rejected[0][1]

    def test_empty_path_rejected(self) -> None:
        schema = _make_schema()
        patches = [PatchOp(op="set", path="", value="x")]
        _, result = apply_patches(schema, patches)
        assert len(result.rejected) == 1

    def test_remove_optional_field(self) -> None:
        schema = _make_schema()
        assert schema.housing.monthly_rent is not None
        patches = [PatchOp(op="remove", path="housing.monthly_rent")]
        updated, result = apply_patches(schema, patches)
        assert len(result.applied) == 1
        assert updated.housing.monthly_rent is None

    def test_remove_required_field_rejected(self) -> None:
        schema = _make_schema()
        patches = [PatchOp(op="remove", path="client.name")]
        _, result = apply_patches(schema, patches)
        assert len(result.rejected) == 1
        assert "required" in result.rejected[0][1].lower()

    def test_remove_dict_key(self) -> None:
        schema = _make_schema()
        patches = [
            PatchOp(op="remove", path="spending.budget_monthly.food")
        ]
        updated, result = apply_patches(schema, patches)
        assert "food" not in updated.spending.budget_monthly

    def test_append_to_list(self) -> None:
        schema = _make_schema()
        cf = {
            "type": "income",
            "amount": 500,
            "start_date": "2030-01",
            "duration_months": 12,
        }
        patches = [PatchOp(op="append", path="planned_cashflows", value=cf)]
        updated, result = apply_patches(schema, patches)
        assert len(result.applied) == 1
        assert len(updated.planned_cashflows) == 1

    def test_append_to_non_list_rejected(self) -> None:
        schema = _make_schema()
        patches = [PatchOp(op="append", path="client.name", value="x")]
        _, result = apply_patches(schema, patches)
        assert len(result.rejected) == 1
        assert "non-list" in result.rejected[0][1].lower()

    def test_multiple_patches_mixed(self) -> None:
        schema = _make_schema()
        patches = [
            PatchOp(op="set", path="client.name", value="Bob"),
            PatchOp(op="set", path="client.nonexistent", value="x"),
            PatchOp(op="set", path="location.state", value="CA"),
        ]
        updated, result = apply_patches(schema, patches)
        assert len(result.applied) == 2
        assert len(result.rejected) == 1
        assert updated.client.name.value == "Bob"
        assert updated.location.state.value == "CA"

    def test_snapshot_id_generated(self) -> None:
        schema = _make_schema()
        patches = [PatchOp(op="set", path="client.name", value="Bob")]
        _, result = apply_patches(schema, patches)
        assert len(result.schema_snapshot_id) == 64  # SHA-256 hex

    def test_original_not_mutated(self) -> None:
        schema = _make_schema()
        original_name = schema.client.name.value
        patches = [PatchOp(op="set", path="client.name", value="New Name")]
        apply_patches(schema, patches)
        assert schema.client.name.value == original_name
