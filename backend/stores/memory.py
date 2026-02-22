"""In-memory store implementations for development and testing.

Used when ``STORE_BACKEND=memory``.  All methods are async to satisfy
the protocol contracts, but perform no real I/O.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from backend.auth.models import AuditEntry, UserProfile
from backend.schema.canonical import CanonicalPlanSchema
from backend.schema.snapshots import MemorySnapshotStore
from backend.stores.protocols import SessionDocument


class InMemoryPlanStore:
    """Dict-backed plan store keyed by ``plan_id``."""

    def __init__(self) -> None:
        self._plans: dict[str, CanonicalPlanSchema] = {}

    async def get(self, plan_id: str) -> CanonicalPlanSchema | None:
        return self._plans.get(plan_id)

    async def save(self, plan: CanonicalPlanSchema) -> None:
        plan.version += 1
        self._plans[plan.plan_id] = plan

    async def list_by_owner(
        self, owner_id: str
    ) -> list[CanonicalPlanSchema]:
        return [p for p in self._plans.values() if p.owner_id == owner_id]

    async def delete(self, plan_id: str) -> bool:
        return self._plans.pop(plan_id, None) is not None

    async def update_fields(
        self,
        plan_id: str,
        updates: dict[str, Any],
        expected_version: int | None = None,
    ) -> CanonicalPlanSchema | None:
        plan = self._plans.get(plan_id)
        if plan is None:
            return None

        if expected_version is not None and plan.version != expected_version:
            return None

        for key, value in updates.items():
            _set_dot_path(plan, key, value)

        plan.version += 1
        plan.updated_at = datetime.now(timezone.utc)
        return plan


def _set_dot_path(obj: Any, path: str, value: Any) -> None:
    """Set a value on *obj* following a dot-delimited attribute path."""
    parts = path.split(".")
    for part in parts[:-1]:
        obj = getattr(obj, part)
    setattr(obj, parts[-1], value)


class InMemorySessionStore:
    """Dict-backed session store keyed by ``session_id``."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionDocument] = {}

    async def get(self, session_id: str) -> SessionDocument | None:
        return self._sessions.get(session_id)

    async def save(self, session: SessionDocument) -> None:
        self._sessions[session.session_id] = session

    async def get_for_plan(self, plan_id: str) -> SessionDocument | None:
        matches = [
            s for s in self._sessions.values() if s.plan_id == plan_id
        ]
        if not matches:
            return None
        return max(matches, key=lambda s: s.created_at)

    async def delete_for_plan(self, plan_id: str) -> int:
        to_delete = [
            sid
            for sid, s in self._sessions.items()
            if s.plan_id == plan_id
        ]
        for sid in to_delete:
            del self._sessions[sid]
        return len(to_delete)


InMemorySnapshotStore = MemorySnapshotStore


class MemoryUserProfileStore:
    """In-memory UserProfileStore for unit tests."""

    def __init__(self) -> None:
        self._profiles: dict[str, UserProfile] = {}

    async def get_by_sub(self, auth0_sub: str) -> UserProfile | None:
        return self._profiles.get(auth0_sub)

    async def upsert(self, profile: UserProfile) -> None:
        self._profiles[profile.auth0_sub] = profile

    async def list_profiles(
        self, *, skip: int = 0, limit: int = 50
    ) -> list[UserProfile]:
        all_profiles = sorted(
            self._profiles.values(), key=lambda p: p.created_at
        )
        return all_profiles[skip : skip + limit]

    async def deactivate(self, auth0_sub: str) -> bool:
        profile = self._profiles.get(auth0_sub)
        if profile is None:
            return False
        profile.is_active = False
        profile.updated_at = datetime.now(timezone.utc)
        return True


class MemoryAuditStore:
    """In-memory AuditStore for unit tests."""

    def __init__(self) -> None:
        self._entries: list[AuditEntry] = []

    async def append(self, entry: AuditEntry) -> None:
        self._entries.append(entry)

    async def query(
        self,
        *,
        auth0_sub: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        since: str | None = None,
        until: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[AuditEntry]:
        results = list(self._entries)
        if auth0_sub:
            results = [e for e in results if e.auth0_sub == auth0_sub]
        if action:
            results = [e for e in results if e.action == action]
        if resource_type:
            results = [e for e in results if e.resource_type == resource_type]
        if since:
            since_dt = datetime.fromisoformat(since)
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)
            results = [e for e in results if e.timestamp >= since_dt]
        if until:
            until_dt = datetime.fromisoformat(until)
            if until_dt.tzinfo is None:
                until_dt = until_dt.replace(tzinfo=timezone.utc)
            results = [e for e in results if e.timestamp <= until_dt]
        return results[skip : skip + limit]
