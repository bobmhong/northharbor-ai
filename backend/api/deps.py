"""FastAPI dependency injection -- stores, config, and session management."""

from __future__ import annotations

import logging
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.ai.extractor import (
    LLMClient,
    OllamaLLMClient,
    OpenAILLMClient,
    StubLLMClient,
)
from backend.analytics.llm_tracker import get_llm_tracker
from backend.analytics.store import (
    InMemoryLLMAnalyticsStore,
    LLMAnalyticsStore,
    MongoLLMAnalyticsStore,
)
from backend.config import Settings, get_settings
from backend.interview.session import InterviewMessage, InterviewSession
from backend.schema.canonical import CanonicalPlanSchema
from backend.stores.memory import InMemoryPlanStore, InMemorySessionStore, InMemorySnapshotStore
from backend.stores.protocols import PlanStore, SessionDocument, SessionStore

_plan_store: PlanStore | None = None
_session_store: SessionStore | None = None
_snapshot_store: Any = None
_live_sessions: dict[str, InterviewSession] = {}
_llm: LLMClient | None = None
_motor_client: AsyncIOMotorClient | None = None
_analytics_store: LLMAnalyticsStore | None = None
logger = logging.getLogger(__name__)


def _get_motor_database() -> AsyncIOMotorDatabase:
    global _motor_client
    if _motor_client is None:
        settings = get_settings()
        _motor_client = AsyncIOMotorClient(settings.mongodb_uri)
    settings = get_settings()
    return _motor_client[settings.mongodb_database]


async def init_stores(settings: Settings | None = None) -> None:
    """Initialize stores based on STORE_BACKEND setting."""
    global _plan_store, _session_store, _snapshot_store, _analytics_store

    if settings is None:
        settings = get_settings()

    backend = settings.store_backend.strip().lower()

    if backend == "mongodb":
        from backend.stores.mongo_plans import MongoPlanStore
        from backend.stores.mongo_sessions import MongoSessionStore
        from backend.stores.mongo_snapshots import MongoSnapshotStore

        db = _get_motor_database()
        plan_store = MongoPlanStore(db)
        session_store = MongoSessionStore(db)
        snapshot_store = MongoSnapshotStore(db)
        analytics_store = MongoLLMAnalyticsStore(db)

        await plan_store.ensure_indexes()
        await session_store.ensure_indexes()
        await snapshot_store.ensure_indexes()
        await analytics_store.ensure_indexes()

        _plan_store = plan_store
        _session_store = session_store
        _snapshot_store = snapshot_store
        _analytics_store = analytics_store
    else:
        _plan_store = InMemoryPlanStore()
        _session_store = InMemorySessionStore()
        _snapshot_store = InMemorySnapshotStore()
        _analytics_store = InMemoryLLMAnalyticsStore()

    get_llm_tracker(store=_analytics_store)
    logger.info("Stores initialized with backend=%s", backend)


def _get_plan_store() -> PlanStore:
    if _plan_store is None:
        raise RuntimeError("Stores not initialized -- call init_stores() first")
    return _plan_store


def _get_session_store() -> SessionStore:
    if _session_store is None:
        raise RuntimeError("Stores not initialized -- call init_stores() first")
    return _session_store


def get_snapshot_store() -> Any:
    if _snapshot_store is None:
        return InMemorySnapshotStore()
    return _snapshot_store


def get_llm_client() -> LLMClient:
    global _llm
    if _llm is None:
        get_llm_tracker(store=get_llm_analytics_store())
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
        elif provider == "openai":
            logger.warning(
                "LLM provider 'openai' selected but NORTHHARBOR_OPENAPI_KEY is empty; "
                "falling back to StubLLMClient"
            )
            _llm = StubLLMClient()
        else:
            logger.warning(
                "Unsupported LLM provider '%s'; falling back to StubLLMClient",
                settings.llm_provider,
            )
            _llm = StubLLMClient()
    return _llm


def set_llm_client(llm: LLMClient) -> None:
    global _llm
    _llm = llm


def get_llm_analytics_store() -> LLMAnalyticsStore:
    if _analytics_store is not None:
        return _analytics_store
    return InMemoryLLMAnalyticsStore()


# ---------------------------------------------------------------------------
# Plan operations
# ---------------------------------------------------------------------------

async def get_plan(plan_id: str) -> CanonicalPlanSchema | None:
    return await _get_plan_store().get(plan_id)


async def store_plan(plan: CanonicalPlanSchema) -> None:
    await _get_plan_store().save(plan)


async def list_plans(owner_id: str) -> list[CanonicalPlanSchema]:
    return await _get_plan_store().list_by_owner(owner_id)


async def delete_plan(plan_id: str) -> bool:
    await _get_session_store().delete_for_plan(plan_id)
    return await _get_plan_store().delete(plan_id)


# ---------------------------------------------------------------------------
# Session operations (with live-session cache for active interviews)
# ---------------------------------------------------------------------------

def _session_to_doc(session: InterviewSession) -> SessionDocument:
    return SessionDocument(
        session_id=session.session_id,
        plan_id=session.schema.plan_id,
        model=session.model,
        history=[m.model_dump(mode="json") for m in session.history],
        created_at=session.created_at,
    )


def _doc_to_session(
    doc: SessionDocument, schema: CanonicalPlanSchema
) -> InterviewSession:
    session = InterviewSession(
        schema,
        llm=get_llm_client(),
        model=doc.model,
        session_id=doc.session_id,
    )
    session.history = [
        InterviewMessage.model_validate(m)
        for m in doc.history
        if isinstance(m, dict)
    ]
    session.created_at = doc.created_at
    return session


async def get_session(session_id: str) -> InterviewSession | None:
    if session_id in _live_sessions:
        return _live_sessions[session_id]
    doc = await _get_session_store().get(session_id)
    if doc is None:
        return None
    plan = await get_plan(doc.plan_id)
    if plan is None:
        return None
    session = _doc_to_session(doc, plan)
    _live_sessions[session_id] = session
    return session


async def store_session(session: InterviewSession) -> None:
    _live_sessions[session.session_id] = session
    await _get_session_store().save(_session_to_doc(session))


async def get_session_for_plan(plan_id: str) -> InterviewSession | None:
    matches = [
        s for s in _live_sessions.values() if s.schema.plan_id == plan_id
    ]
    if matches:
        return max(matches, key=lambda s: s.created_at)
    doc = await _get_session_store().get_for_plan(plan_id)
    if doc is None:
        return None
    plan = await get_plan(doc.plan_id)
    if plan is None:
        return None
    session = _doc_to_session(doc, plan)
    _live_sessions[session.session_id] = session
    return session
