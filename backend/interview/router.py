"""FastAPI interview endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.deps import (
    get_llm_client,
    get_plan,
    get_session,
    store_plan,
    store_session,
)
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

router = APIRouter(prefix="/api/interview", tags=["interview"])


def _default_pf(value: Any = None) -> ProvenanceField:
    return ProvenanceField(value=value, source=FieldSource.DEFAULT, confidence=0.0)


class StartInterviewRequest(BaseModel):
    owner_id: str = "anonymous"


class StartInterviewResponse(BaseModel):
    session_id: str
    plan_id: str
    message: str
    interview_complete: bool = False


class RespondRequest(BaseModel):
    session_id: str
    message: str


class RespondResponse(BaseModel):
    message: str
    applied_fields: list[str] = Field(default_factory=list)
    rejected_fields: list[str] = Field(default_factory=list)
    interview_complete: bool = False
    missing_fields: list[str] = Field(default_factory=list)


@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(req: StartInterviewRequest) -> StartInterviewResponse:
    """Start a new interview session with an empty plan."""
    plan_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    schema = CanonicalPlanSchema(
        plan_id=plan_id,
        owner_id=req.owner_id,
        created_at=now,
        updated_at=now,
        client=ClientProfile(
            name=_default_pf(),
            birth_year=_default_pf(0),
            retirement_window=_default_pf(NumericRange(min=65, max=67)),
        ),
        location=LocationProfile(
            state=_default_pf(), city=_default_pf()
        ),
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

    store_plan(schema)

    session = InterviewSession(schema, llm=get_llm_client())
    turn = session.start()
    store_session(session)

    return StartInterviewResponse(
        session_id=session.session_id,
        plan_id=plan_id,
        message=turn.assistant_message,
        interview_complete=turn.interview_complete,
    )


@router.post("/respond", response_model=RespondResponse)
async def respond(req: RespondRequest) -> RespondResponse:
    """Process a user message in an active interview session."""
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    turn = await session.respond(req.message)

    store_plan(session.schema)

    applied = [p.path for p in turn.patch_result.applied] if turn.patch_result else []
    rejected = [r for _, r in turn.patch_result.rejected] if turn.patch_result else []

    return RespondResponse(
        message=turn.assistant_message,
        applied_fields=applied,
        rejected_fields=rejected,
        interview_complete=turn.interview_complete,
        missing_fields=turn.policy_decision.missing_fields,
    )
