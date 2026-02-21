"""Interview session state machine.

Tracks conversation history, current schema state, and delegates
extraction and policy decisions to the AI extractor and policy engine.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from backend.ai.extractor import LLMClient, StubLLMClient, extract_and_apply
from backend.interview.questions import completion_message, welcome_message
from backend.policy.engine import PolicyDecision, select_next_question
from backend.schema.canonical import CanonicalPlanSchema
from backend.schema.patch_ops import PatchResult
from backend.schema.provenance import ProvenanceField


class InterviewMessage(BaseModel):
    """A single message in the interview conversation."""

    role: str
    content: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class InterviewTurnResult(BaseModel):
    """Result of processing a single user message in the interview."""

    assistant_message: str
    patch_result: PatchResult | None = None
    policy_decision: PolicyDecision
    interview_complete: bool = False


class InterviewSession:
    """Manages the state of a single plan interview.

    The session tracks:
    - The canonical schema being built up
    - Conversation history for context
    - The LLM client used for extraction
    """

    def __init__(
        self,
        schema: CanonicalPlanSchema,
        *,
        llm: LLMClient | None = None,
        session_id: str | None = None,
    ) -> None:
        self.session_id = session_id or str(uuid.uuid4())
        self.schema = schema
        self.llm = llm or StubLLMClient()
        self.history: list[InterviewMessage] = []
        self.created_at = datetime.now(timezone.utc)

    @property
    def conversation_history(self) -> list[dict[str, str]]:
        """Return conversation history in the format expected by the LLM."""
        return [{"role": m.role, "content": m.content} for m in self.history]

    def start(self) -> InterviewTurnResult:
        """Begin the interview and return the first question."""
        decision = select_next_question(self.schema)
        greeting = welcome_message()
        first_question = decision.next_question or completion_message()
        message = f"{greeting}\n\n{first_question}"

        self.history.append(
            InterviewMessage(role="assistant", content=message)
        )

        return InterviewTurnResult(
            assistant_message=message,
            policy_decision=decision,
            interview_complete=decision.interview_complete,
        )

    async def respond(self, user_message: str) -> InterviewTurnResult:
        """Process a user message and return the next assistant response."""
        self.history.append(
            InterviewMessage(role="user", content=user_message)
        )

        updated_schema, patch_result, decision = await extract_and_apply(
            user_message,
            self.schema,
            self.conversation_history,
            llm=self.llm,
        )
        self.schema = updated_schema

        if decision.interview_complete:
            reply = completion_message()
        elif patch_result.applied:
            applied_fields = ", ".join(p.path for p in patch_result.applied)
            reply = f"Got it, I've recorded {applied_fields}."
            if decision.next_question:
                reply += f"\n\n{decision.next_question}"
        elif patch_result.rejected:
            reasons = "; ".join(r for _, r in patch_result.rejected)
            reply = f"I had trouble with that: {reasons}."
            if decision.next_question:
                reply += f"\n\nLet's try again: {decision.next_question}"
        else:
            reply = decision.next_question or "Could you tell me more?"

        self.history.append(
            InterviewMessage(role="assistant", content=reply)
        )

        return InterviewTurnResult(
            assistant_message=reply,
            patch_result=patch_result,
            policy_decision=decision,
            interview_complete=decision.interview_complete,
        )
