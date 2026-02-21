"""FastAPI dependency injection -- stores, config, and session management."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.ai.extractor import (
    LLMClient,
    OllamaLLMClient,
    OpenAILLMClient,
    StubLLMClient,
)
from backend.config import Settings, get_settings
from backend.interview.session import InterviewMessage, InterviewSession
from backend.schema.canonical import CanonicalPlanSchema
from backend.schema.snapshots import MemorySnapshotStore, SnapshotStore


_snapshot_store: MemorySnapshotStore | None = None
_sessions: dict[str, InterviewSession] = {}
_plans: dict[str, CanonicalPlanSchema] = {}
_llm: LLMClient | None = None
_runtime_loaded = False
_RUNTIME_STATE_PATH = Path(".data/runtime_state.json")


def get_snapshot_store() -> MemorySnapshotStore:
    global _snapshot_store
    if _snapshot_store is None:
        _snapshot_store = MemorySnapshotStore()
    return _snapshot_store


def get_llm_client() -> LLMClient:
    global _llm
    if _llm is None:
        settings = get_settings()
        provider = settings.llm_provider.strip().lower()
        if provider == "ollama":
            _llm = OllamaLLMClient(
                base_url=settings.ollama_base_url,
                timeout_seconds=settings.ollama_timeout_seconds,
            )
        elif provider == "openai" and settings.openai_api_key.strip():
            _llm = OpenAILLMClient(
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                timeout_seconds=settings.openai_timeout_seconds,
            )
        else:
            _llm = StubLLMClient()
    return _llm


def set_llm_client(llm: LLMClient) -> None:
    global _llm
    _llm = llm


def _ensure_runtime_loaded() -> None:
    global _runtime_loaded
    if _runtime_loaded:
        return
    _runtime_loaded = True

    if not _RUNTIME_STATE_PATH.exists():
        return

    try:
        raw = json.loads(_RUNTIME_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return

    plans_raw = raw.get("plans", [])
    for plan_obj in plans_raw:
        try:
            plan = CanonicalPlanSchema.model_validate(plan_obj)
            _plans[plan.plan_id] = plan
        except Exception:
            continue

    sessions_raw = raw.get("sessions", [])
    for session_obj in sessions_raw:
        session_id = session_obj.get("session_id")
        plan_id = session_obj.get("plan_id")
        if not isinstance(session_id, str) or not isinstance(plan_id, str):
            continue
        plan = _plans.get(plan_id)
        if plan is None:
            continue
        try:
            session = InterviewSession(
                plan,
                llm=get_llm_client(),
                model=session_obj.get("model", "gpt-4o-mini"),
                session_id=session_id,
            )
            history = session_obj.get("history", [])
            session.history = [
                InterviewMessage.model_validate(m)
                for m in history
                if isinstance(m, dict)
            ]
            created_at_raw = session_obj.get("created_at")
            if isinstance(created_at_raw, str):
                session.created_at = datetime.fromisoformat(created_at_raw)
            _sessions[session.session_id] = session
        except Exception:
            continue


def _persist_runtime_state() -> None:
    _RUNTIME_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "plans": [p.model_dump(mode="json") for p in _plans.values()],
        "sessions": [
            {
                "session_id": s.session_id,
                "plan_id": s.schema.plan_id,
                "model": s.model,
                "history": [m.model_dump(mode="json") for m in s.history],
                "created_at": s.created_at.isoformat(),
            }
            for s in _sessions.values()
        ],
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    _RUNTIME_STATE_PATH.write_text(
        json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8"
    )


def get_session(session_id: str) -> InterviewSession | None:
    _ensure_runtime_loaded()
    return _sessions.get(session_id)


def store_session(session: InterviewSession) -> None:
    _ensure_runtime_loaded()
    _sessions[session.session_id] = session
    _persist_runtime_state()


def get_plan(plan_id: str) -> CanonicalPlanSchema | None:
    _ensure_runtime_loaded()
    return _plans.get(plan_id)


def store_plan(plan: CanonicalPlanSchema) -> None:
    _ensure_runtime_loaded()
    _plans[plan.plan_id] = plan
    _persist_runtime_state()


def list_plans(owner_id: str) -> list[CanonicalPlanSchema]:
    _ensure_runtime_loaded()
    return [p for p in _plans.values() if p.owner_id == owner_id]


def delete_plan(plan_id: str) -> bool:
    """Delete a plan by ID. Returns True if deleted, False if not found."""
    _ensure_runtime_loaded()
    if plan_id not in _plans:
        return False
    del _plans[plan_id]
    sessions_to_remove = [
        sid for sid, s in _sessions.items() if s.schema.plan_id == plan_id
    ]
    for sid in sessions_to_remove:
        del _sessions[sid]
    _persist_runtime_state()
    return True


def get_session_for_plan(plan_id: str) -> InterviewSession | None:
    """Find the most recent session for a given plan."""
    _ensure_runtime_loaded()
    matching_sessions = [
        s for s in _sessions.values() if s.schema.plan_id == plan_id
    ]
    if not matching_sessions:
        return None
    return max(matching_sessions, key=lambda s: s.created_at)
