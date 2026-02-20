"""Tests for schema snapshots."""

import asyncio

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
from backend.schema.provenance import FieldSource, ProvenanceField
from backend.schema.snapshots import (
    MemorySnapshotStore,
    SchemaSnapshot,
    SnapshotStore,
    create_snapshot,
)


def _pf(value):
    return ProvenanceField(value=value, source=FieldSource.USER)


def _make_schema(**overrides):
    defaults = dict(
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


class TestCreateSnapshot:
    def test_returns_snapshot(self) -> None:
        schema = _make_schema()
        snap = create_snapshot(schema)
        assert isinstance(snap, SchemaSnapshot)
        assert snap.plan_id == "plan-001"
        assert snap.owner_id == "auth0|user1"
        assert snap.schema_version == "1.0"

    def test_snapshot_id_is_sha256(self) -> None:
        schema = _make_schema()
        snap = create_snapshot(schema)
        assert len(snap.snapshot_id) == 64
        assert all(c in "0123456789abcdef" for c in snap.snapshot_id)

    def test_deterministic_hash(self) -> None:
        """Same schema produces the same snapshot_id."""
        schema = _make_schema()
        snap1 = create_snapshot(schema)
        snap2 = create_snapshot(schema)
        assert snap1.snapshot_id == snap2.snapshot_id

    def test_different_data_different_hash(self) -> None:
        s1 = _make_schema()
        s2 = _make_schema(plan_id="plan-002")
        snap1 = create_snapshot(s1)
        snap2 = create_snapshot(s2)
        assert snap1.snapshot_id != snap2.snapshot_id

    def test_data_contains_serialized_schema(self) -> None:
        schema = _make_schema()
        snap = create_snapshot(schema)
        assert snap.data["plan_id"] == "plan-001"
        assert snap.data["client"]["name"]["value"] == "Adam"


class TestMemorySnapshotStore:
    def test_protocol_compliance(self) -> None:
        assert isinstance(MemorySnapshotStore(), SnapshotStore)

    def test_save_and_get(self) -> None:
        store = MemorySnapshotStore()
        schema = _make_schema()
        snap = create_snapshot(schema)

        asyncio.get_event_loop().run_until_complete(store.save(snap))
        retrieved = asyncio.get_event_loop().run_until_complete(
            store.get(snap.snapshot_id)
        )
        assert retrieved is not None
        assert retrieved.snapshot_id == snap.snapshot_id

    def test_get_missing_returns_none(self) -> None:
        store = MemorySnapshotStore()
        result = asyncio.get_event_loop().run_until_complete(
            store.get("nonexistent")
        )
        assert result is None

    def test_list_for_plan(self) -> None:
        store = MemorySnapshotStore()
        s1 = _make_schema()
        s2 = _make_schema(plan_id="plan-002")
        snap1 = create_snapshot(s1)
        snap2 = create_snapshot(s2)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(store.save(snap1))
        loop.run_until_complete(store.save(snap2))

        results = loop.run_until_complete(
            store.list_for_plan("plan-001", "auth0|user1")
        )
        assert len(results) == 1
        assert results[0].plan_id == "plan-001"
