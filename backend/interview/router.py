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
    get_session_for_plan,
    store_plan,
    store_session,
)
from backend.config import get_settings
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
    plan_id: str | None = None


class HistoryMessage(BaseModel):
    role: str
    content: str
    timestamp: str


class StartInterviewResponse(BaseModel):
    session_id: str
    plan_id: str
    message: str
    target_field: str | None = None
    interview_complete: bool = False
    history: list[HistoryMessage] = Field(default_factory=list)
    is_resumed: bool = False


class RespondRequest(BaseModel):
    session_id: str
    message: str


class RespondResponse(BaseModel):
    message: str
    target_field: str | None = None
    applied_fields: list[str] = Field(default_factory=list)
    rejected_fields: list[str] = Field(default_factory=list)
    interview_complete: bool = False
    missing_fields: list[str] = Field(default_factory=list)


@router.post("/start", response_model=StartInterviewResponse)
async def start_interview(req: StartInterviewRequest) -> StartInterviewResponse:
    """Start an interview session for a new or existing plan."""
    if req.plan_id:
        schema = get_plan(req.plan_id)
        if schema is None or schema.owner_id != req.owner_id:
            raise HTTPException(status_code=404, detail="Plan not found")
        plan_id = schema.plan_id
        
        existing_session = get_session_for_plan(plan_id)
        if existing_session and existing_session.history:
            history = [
                HistoryMessage(
                    role=m.role,
                    content=m.content,
                    timestamp=m.timestamp.isoformat(),
                )
                for m in existing_session.history
            ]
            from backend.policy.engine import select_next_question
            decision = select_next_question(existing_session.schema)
            
            if decision.interview_complete:
                message = "This plan is complete. Would you like to make any changes to your answers?"
            else:
                message = f"Welcome back! Let's continue where we left off.\n\n{decision.next_question}"
            
            return StartInterviewResponse(
                session_id=existing_session.session_id,
                plan_id=plan_id,
                message=message,
                target_field=decision.target_field,
                interview_complete=decision.interview_complete,
                history=history,
                is_resumed=True,
            )
    else:
        plan_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        schema = CanonicalPlanSchema(
            plan_id=plan_id,
            owner_id=req.owner_id,
            created_at=now,
            updated_at=now,
            scenario_name="Default",
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

    settings = get_settings()
    session = InterviewSession(
        schema,
        llm=get_llm_client(),
        model=settings.llm_model,
    )
    turn = session.start()
    store_session(session)

    return StartInterviewResponse(
        session_id=session.session_id,
        plan_id=plan_id,
        message=turn.assistant_message,
        target_field=turn.policy_decision.target_field,
        interview_complete=turn.interview_complete,
        history=[],
        is_resumed=False,
    )


@router.post("/respond", response_model=RespondResponse)
async def respond(req: RespondRequest) -> RespondResponse:
    """Process a user message in an active interview session."""
    session = get_session(req.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    turn = await session.respond(req.message)

    if turn.interview_complete and session.schema.status == "intake_in_progress":
        session.schema.status = "intake_complete"

    store_plan(session.schema)
    store_session(session)

    applied = [p.path for p in turn.patch_result.applied] if turn.patch_result else []
    rejected = [r for _, r in turn.patch_result.rejected] if turn.patch_result else []

    return RespondResponse(
        message=turn.assistant_message,
        target_field=turn.policy_decision.target_field,
        applied_fields=applied,
        rejected_fields=rejected,
        interview_complete=turn.interview_complete,
        missing_fields=turn.policy_decision.missing_fields,
    )
