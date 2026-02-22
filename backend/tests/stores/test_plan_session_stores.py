"""Tests for InMemoryPlanStore and InMemorySessionStore."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone, timedelta

from backend.schema.canonical import (
    CanonicalPlanSchema,
    ClientProfile,
    LocationProfile,
    IncomeProfile,
    RetirementPhilosophy,
    AccountsProfile,
    HousingProfile,
    SpendingProfile,
    SocialSecurityProfile,
    MonteCarloConfig,
    NumericRange,
)
from backend.schema.provenance import FieldSource, ProvenanceField
from backend.stores.memory import InMemoryPlanStore, InMemorySessionStore
from backend.stores.protocols import PlanStore, SessionDocument, SessionStore


def _pf(value=None):
    return ProvenanceField(value=value, source=FieldSource.DEFAULT, confidence=0.0)


def _make_plan(plan_id="plan-1", owner_id="owner-a"):
    now = datetime.now(timezone.utc)
    return CanonicalPlanSchema(
        plan_id=plan_id,
        owner_id=owner_id,
        created_at=now,
        updated_at=now,
        client=ClientProfile(
            name=_pf(),
            birth_year=_pf(0),
            retirement_window=_pf(NumericRange(min=65, max=67)),
        ),
        location=LocationProfile(state=_pf(), city=_pf()),
        income=IncomeProfile(current_gross_annual=_pf(0)),
        retirement_philosophy=RetirementPhilosophy(
            success_probability_target=_pf(0.95),
            legacy_goal_total_real=_pf(0),
        ),
        accounts=AccountsProfile(retirement_balance=_pf(0), savings_rate_percent=_pf(0)),
        housing=HousingProfile(),
        spending=SpendingProfile(retirement_monthly_real=_pf(0)),
        social_security=SocialSecurityProfile(
            combined_at_67_monthly=_pf(0),
            combined_at_70_monthly=_pf(0),
        ),
        monte_carlo=MonteCarloConfig(
            required_success_rate=_pf(0.95),
            horizon_age=_pf(95),
            legacy_floor=_pf(0),
        ),
    )


class TestInMemoryPlanStore(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.store = InMemoryPlanStore()

    async def test_get_nonexistent_returns_none(self) -> None:
        result = await self.store.get("unknown-plan")
        self.assertIsNone(result)

    async def test_save_and_get(self) -> None:
        plan = _make_plan(plan_id="plan-1", owner_id="owner-a")
        await self.store.save(plan)
        loaded = await self.store.get("plan-1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.plan_id, "plan-1")  # type: ignore[union-attr]

    async def test_save_increments_version(self) -> None:
        plan = _make_plan()
        await self.store.save(plan)
        v1 = await self.store.get(plan.plan_id)
        self.assertEqual(v1.version, 2)  # type: ignore[union-attr]
        await self.store.save(v1)  # type: ignore[arg-type]
        v2 = await self.store.get(plan.plan_id)
        self.assertEqual(v2.version, 3)  # type: ignore[union-attr]

    async def test_list_by_owner_filters(self) -> None:
        await self.store.save(_make_plan(plan_id="p1", owner_id="owner-a"))
        await self.store.save(_make_plan(plan_id="p2", owner_id="owner-a"))
        await self.store.save(_make_plan(plan_id="p3", owner_id="owner-b"))
        list_a = await self.store.list_by_owner("owner-a")
        self.assertEqual(len(list_a), 2)
        self.assertEqual({p.plan_id for p in list_a}, {"p1", "p2"})
        list_b = await self.store.list_by_owner("owner-b")
        self.assertEqual(len(list_b), 1)
        self.assertEqual(list_b[0].plan_id, "p3")

    async def test_list_by_owner_empty(self) -> None:
        result = await self.store.list_by_owner("unknown-owner")
        self.assertEqual(result, [])

    async def test_delete_existing(self) -> None:
        plan = _make_plan()
        await self.store.save(plan)
        result = await self.store.delete(plan.plan_id)
        self.assertTrue(result)
        loaded = await self.store.get(plan.plan_id)
        self.assertIsNone(loaded)

    async def test_delete_nonexistent_returns_false(self) -> None:
        result = await self.store.delete("unknown-plan")
        self.assertFalse(result)

    async def test_update_fields(self) -> None:
        plan = _make_plan()
        await self.store.save(plan)
        updated = await self.store.update_fields(
            "plan-1",
            {"status": "intake_complete"},
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.status, "intake_complete")  # type: ignore[union-attr]
        self.assertEqual(updated.version, 3)  # type: ignore[union-attr]
        loaded = await self.store.get("plan-1")
        self.assertEqual(loaded.status, "intake_complete")  # type: ignore[union-attr]

    async def test_update_fields_dot_path(self) -> None:
        plan = _make_plan()
        await self.store.save(plan)
        updated = await self.store.update_fields(
            "plan-1",
            {"scenario_name": "New Name"},
        )
        self.assertIsNotNone(updated)
        self.assertEqual(updated.scenario_name, "New Name")  # type: ignore[union-attr]
        loaded = await self.store.get("plan-1")
        self.assertEqual(loaded.scenario_name, "New Name")  # type: ignore[union-attr]

    async def test_update_fields_version_mismatch(self) -> None:
        plan = _make_plan()
        await self.store.save(plan)
        result = await self.store.update_fields(
            "plan-1",
            {"status": "intake_complete"},
            expected_version=999,
        )
        self.assertIsNone(result)
        loaded = await self.store.get("plan-1")
        self.assertEqual(loaded.status, "intake_in_progress")  # type: ignore[union-attr]

    async def test_update_fields_nonexistent(self) -> None:
        result = await self.store.update_fields(
            "unknown-plan",
            {"status": "intake_complete"},
        )
        self.assertIsNone(result)

    async def test_protocol_compliance(self) -> None:
        self.assertTrue(isinstance(self.store, PlanStore))


class TestInMemorySessionStore(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.store = InMemorySessionStore()

    async def test_get_nonexistent_returns_none(self) -> None:
        result = await self.store.get("unknown-session")
        self.assertIsNone(result)

    async def test_save_and_get(self) -> None:
        doc = SessionDocument(
            session_id="sess-1",
            plan_id="plan-1",
            model="gpt-4o-mini",
            history=[],
            created_at=datetime.now(timezone.utc),
        )
        await self.store.save(doc)
        loaded = await self.store.get("sess-1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.session_id, "sess-1")  # type: ignore[union-attr]
        self.assertEqual(loaded.plan_id, "plan-1")  # type: ignore[union-attr]

    async def test_get_for_plan_returns_most_recent(self) -> None:
        base = datetime.now(timezone.utc)
        older = SessionDocument(
            session_id="sess-old",
            plan_id="plan-1",
            model="gpt-4o-mini",
            history=[],
            created_at=base,
        )
        newer = SessionDocument(
            session_id="sess-new",
            plan_id="plan-1",
            model="gpt-4o-mini",
            history=[],
            created_at=base + timedelta(seconds=10),
        )
        await self.store.save(older)
        await self.store.save(newer)
        result = await self.store.get_for_plan("plan-1")
        self.assertIsNotNone(result)
        self.assertEqual(result.session_id, "sess-new")  # type: ignore[union-attr]

    async def test_get_for_plan_no_match(self) -> None:
        result = await self.store.get_for_plan("unknown-plan")
        self.assertIsNone(result)

    async def test_delete_for_plan(self) -> None:
        await self.store.save(
            SessionDocument(
                session_id="s1",
                plan_id="plan-1",
                model="gpt-4o-mini",
                history=[],
                created_at=datetime.now(timezone.utc),
            )
        )
        await self.store.save(
            SessionDocument(
                session_id="s2",
                plan_id="plan-1",
                model="gpt-4o-mini",
                history=[],
                created_at=datetime.now(timezone.utc),
            )
        )
        count = await self.store.delete_for_plan("plan-1")
        self.assertEqual(count, 2)
        result = await self.store.get_for_plan("plan-1")
        self.assertIsNone(result)

    async def test_delete_for_plan_no_match(self) -> None:
        count = await self.store.delete_for_plan("unknown-plan")
        self.assertEqual(count, 0)

    async def test_protocol_compliance(self) -> None:
        self.assertTrue(isinstance(self.store, SessionStore))


if __name__ == "__main__":
    unittest.main()
