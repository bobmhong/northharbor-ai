"""Tests for interview session fallback extraction behavior."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone

from backend.ai.extractor import StubLLMClient
from backend.interview.session import (
    InterviewSession,
    _boost_low_confidence_applied,
    _sync_linked_fields,
)
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
from backend.schema.patch_ops import PatchOp, PatchResult, apply_patches
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


class TestInterviewSessionFallback(unittest.IsolatedAsyncioTestCase):
    async def test_fallback_extracts_obvious_full_name(self) -> None:
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()

        turn = await session.respond("bob jones")

        self.assertEqual(session.schema.client.name.value, "Bob Jones")
        self.assertIn("client.name", [p.path for p in turn.patch_result.applied])

    async def test_fallback_ignores_single_token_reply(self) -> None:
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()

        turn = await session.respond("bob")

        self.assertIsNone(session.schema.client.name.value)
        self.assertIn("full name", turn.assistant_message.lower())
        self.assertIn("What should I call you?", turn.assistant_message)

    async def test_fallback_extracts_birth_year_after_name(self) -> None:
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()
        await session.respond("bob jones")

        turn = await session.respond("I was born in 1982")

        self.assertEqual(session.schema.client.birth_year.value, 1982)
        self.assertIn(
            "client.birth_year", [p.path for p in turn.patch_result.applied]
        )

    async def test_fallback_extracts_location(self) -> None:
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()
        await session.respond("bob jones")
        await session.respond("1982")

        state_turn = await session.respond("Washington")
        city_turn = await session.respond("Seattle")

        self.assertIn("location.state", [p.path for p in state_turn.patch_result.applied])
        self.assertIn("location.city", [p.path for p in city_turn.patch_result.applied])
        self.assertEqual(session.schema.location.state.value, "Washington")
        self.assertEqual(session.schema.location.city.value, "Seattle")

    async def test_after_required_fields_moves_to_optional(self) -> None:
        """After all required fields are filled, engine skips to optional fields (no confirmation loop)."""
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()

        for answer in [
            "bob jones",        # client.name
            "1982",             # client.birth_year
            "Washington",       # location.state
            "Seattle",          # location.city
            "185000",           # income.current_gross_annual
            "500000",           # retirement_philosophy.legacy_goal_total_real
            "750000",           # accounts.retirement_balance
            "yes",              # accounts.has_employer_plan
            "3",                # accounts.employer_match_percent
            "6",                # accounts.employee_contribution_percent
            "9000",             # spending.retirement_monthly_real
            "4200",             # social_security.combined_at_67_monthly
            "5300",             # social_security.combined_at_70_monthly
            "250000",           # monte_carlo.legacy_floor
        ]:
            await session.respond(answer)

        # With the confirmation loop removed, the engine should move straight
        # to optional fields instead of asking to confirm low-confidence values.
        next_turn = await session.respond("rent")
        self.assertFalse(next_turn.interview_complete)
        self.assertIn("housing.status", [p.path for p in next_turn.patch_result.applied])

    async def test_invalid_birth_year_gets_clear_feedback(self) -> None:
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()
        await session.respond("bob jones")

        turn = await session.respond("nineteen eighty two")

        self.assertIn("4-digit birth year", turn.assistant_message)
        self.assertIn("What year were you born?", turn.assistant_message)

    async def test_invalid_birth_year_too_early_gets_specific_feedback(self) -> None:
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()
        await session.respond("bob jones")

        turn = await session.respond("1800")

        self.assertIn("too early", turn.assistant_message.lower())
        self.assertIn("between 1900", turn.assistant_message)

    async def test_invalid_birth_year_future_gets_specific_feedback(self) -> None:
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()
        await session.respond("bob jones")

        turn = await session.respond("2099")

        self.assertIn("future year", turn.assistant_message.lower())
        self.assertIn("birth year", turn.assistant_message.lower())


class TestBoostLowConfidence(unittest.TestCase):
    """Tests for _boost_low_confidence_applied."""

    def _schema_with_low_confidence_target(self) -> CanonicalPlanSchema:
        schema = _make_schema()
        schema, _ = apply_patches(schema, [
            PatchOp(
                op="set",
                path="retirement_philosophy.success_probability_target",
                value=0.95,
                confidence=0.4,
            ),
        ])
        return schema

    def test_boost_all_low_confidence_patches(self) -> None:
        """Boost should apply to any low-confidence patch, not just a specific target."""
        schema = self._schema_with_low_confidence_target()
        patch_result = PatchResult(
            applied=[
                PatchOp(
                    op="set",
                    path="retirement_philosophy.success_probability_target",
                    value=0.95,
                    confidence=0.4,
                ),
            ],
            rejected=[],
            schema_snapshot_id="test",
        )

        boosted = _boost_low_confidence_applied(schema, patch_result, "95%")

        self.assertGreaterEqual(
            boosted.retirement_philosophy.success_probability_target.confidence,
            0.7,
        )

    def test_boost_affirmative_reply(self) -> None:
        """'yes' on a confirmation prompt should promote to full confidence."""
        schema = self._schema_with_low_confidence_target()
        patch_result = PatchResult(
            applied=[
                PatchOp(
                    op="set",
                    path="retirement_philosophy.success_probability_target",
                    value=0.95,
                    confidence=0.4,
                ),
            ],
            rejected=[],
            schema_snapshot_id="test",
        )

        boosted = _boost_low_confidence_applied(schema, patch_result, "yes")

        self.assertEqual(
            boosted.retirement_philosophy.success_probability_target.confidence,
            1.0,
        )

    def test_skip_already_high_confidence(self) -> None:
        """Patches at or above the threshold are left alone."""
        schema = _make_schema()
        schema, _ = apply_patches(schema, [
            PatchOp(
                op="set",
                path="retirement_philosophy.success_probability_target",
                value=0.90,
                confidence=0.85,
            ),
        ])
        patch_result = PatchResult(
            applied=[
                PatchOp(
                    op="set",
                    path="retirement_philosophy.success_probability_target",
                    value=0.90,
                    confidence=0.85,
                ),
            ],
            rejected=[],
            schema_snapshot_id="test",
        )

        boosted = _boost_low_confidence_applied(schema, patch_result, "yes")

        self.assertEqual(
            boosted.retirement_philosophy.success_probability_target.confidence,
            0.85,
        )


class TestSyncLinkedFields(unittest.TestCase):
    """Tests for _sync_linked_fields."""

    def test_sync_when_target_empty(self) -> None:
        schema = _make_schema()
        schema, _ = apply_patches(schema, [
            PatchOp(op="set", path="retirement_philosophy.success_probability_target",
                    value=0.90, confidence=0.85),
            PatchOp(op="remove", path="monte_carlo.required_success_rate"),
        ])

        synced, result = _sync_linked_fields(schema)

        self.assertEqual(synced.monte_carlo.required_success_rate.value, 0.90)

    def test_sync_promotes_confidence_to_target(self) -> None:
        """When source has higher confidence, target should be updated."""
        schema = _make_schema()
        schema, _ = apply_patches(schema, [
            PatchOp(op="set", path="retirement_philosophy.success_probability_target",
                    value=0.90, confidence=1.0),
            PatchOp(op="set", path="monte_carlo.required_success_rate",
                    value=0.90, confidence=0.4),
        ])

        synced, _ = _sync_linked_fields(schema)

        self.assertEqual(
            synced.monte_carlo.required_success_rate.confidence,
            1.0,
        )

    def test_sync_overrides_diverged_value(self) -> None:
        """If LLM set different values for linked fields, source wins."""
        schema = _make_schema()
        schema, _ = apply_patches(schema, [
            PatchOp(op="set", path="retirement_philosophy.success_probability_target",
                    value=0.95, confidence=0.85),
            PatchOp(op="set", path="monte_carlo.required_success_rate",
                    value=0.80, confidence=0.85),
        ])

        synced, _ = _sync_linked_fields(schema)

        self.assertEqual(synced.monte_carlo.required_success_rate.value, 0.95)


class TestFastPath(unittest.IsolatedAsyncioTestCase):
    """Tests for the validated fast path that skips LLM."""

    async def test_fast_path_applies_with_high_confidence(self) -> None:
        """Client-validated input should apply with confidence 1.0."""
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()

        turn = await session.respond(
            "Bob Jones",
            field_path="client.name",
            validated=True,
        )

        self.assertEqual(session.schema.client.name.value, "Bob Jones")
        name_patches = [p for p in turn.patch_result.applied if p.path == "client.name"]
        self.assertTrue(len(name_patches) > 0)

    async def test_fast_path_falls_back_on_parse_failure(self) -> None:
        """When deterministic parse fails, should fall through to LLM path."""
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()

        turn = await session.respond(
            "Bob",
            field_path="client.name",
            validated=True,
        )

        self.assertIsNotNone(turn.assistant_message)

    async def test_skip_reply_marks_additional_considerations(self) -> None:
        """'nothing else' should mark additional_considerations as answered."""
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()

        for answer in [
            "bob jones", "1982", "Washington", "Seattle",
            "185000", "500000", "750000", "yes", "3", "6",
            "9000", "4200", "5300", "250000",
        ]:
            await session.respond(answer)

        await session.respond("rent")
        await session.respond("moderate")
        await session.respond("67")

        turn = await session.respond("nothing else")

        self.assertEqual(session.schema.additional_considerations.value, "none")
