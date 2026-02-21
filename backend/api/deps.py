"""FastAPI dependency injection -- stores, config, and session management."""

from __future__ import annotations

from typing import Any

from backend.ai.extractor import LLMClient, StubLLMClient
from backend.config import Settings, get_settings
from backend.interview.session import InterviewSession
from backend.schema.canonical import CanonicalPlanSchema
from backend.schema.snapshots import MemorySnapshotStore, SnapshotStore


_snapshot_store: MemorySnapshotStore | None = None
_sessions: dict[str, InterviewSession] = {}
_plans: dict[str, CanonicalPlanSchema] = {}
_llm: LLMClient | None = None


def get_snapshot_store() -> MemorySnapshotStore:
    global _snapshot_store
    if _snapshot_store is None:
        _snapshot_store = MemorySnapshotStore()
    return _snapshot_store


def get_llm_client() -> LLMClient:
    global _llm
    if _llm is None:
        _llm = StubLLMClient()
    return _llm


def set_llm_client(llm: LLMClient) -> None:
    global _llm
    _llm = llm


def get_session(session_id: str) -> InterviewSession | None:
    return _sessions.get(session_id)


def store_session(session: InterviewSession) -> None:
    _sessions[session.session_id] = session


def get_plan(plan_id: str) -> CanonicalPlanSchema | None:
    return _plans.get(plan_id)


def store_plan(plan: CanonicalPlanSchema) -> None:
    _plans[plan.plan_id] = plan


def list_plans(owner_id: str) -> list[CanonicalPlanSchema]:
    return [p for p in _plans.values() if p.owner_id == owner_id]
