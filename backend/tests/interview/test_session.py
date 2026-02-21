"""Tests for interview session fallback extraction behavior."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.ai.extractor import StubLLMClient
from backend.interview.session import InterviewSession
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
        self.assertIn("What is your full name?", turn.assistant_message)

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

    async def test_affirmative_confirmation_marks_field_high_confidence(self) -> None:
        session = InterviewSession(_make_schema(), llm=StubLLMClient())
        session.start()

        # Fill required fields so policy reaches low-confidence confirmations.
        for answer in [
            "bob jones",
            "1982",
            "Washington",
            "Seattle",
            "185000",
            "500000",
            "750000",
            "15%",
            "9000",
            "4200",
            "5300",
            "250000",
        ]:
            await session.respond(answer)

        confirm_turn = await session.respond("yes")
        self.assertIn(
            "retirement_philosophy.success_probability_target",
            [p.path for p in confirm_turn.patch_result.applied],
        )

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
