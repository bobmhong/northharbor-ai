"""Protocol definitions for NorthHarbor Sage data stores.

Each protocol describes the contract for a single data domain.  Concrete
implementations (in-memory, MongoDB) satisfy these protocols through
structural subtyping -- no base-class inheritance required.

All store methods are async.  In-memory implementations are trivially
async; Motor-backed implementations use native async I/O.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from backend.auth.models import AuditEntry, UserProfile
from backend.schema.canonical import CanonicalPlanSchema


class SessionDocument(BaseModel):
    """Serializable session data (no live LLMClient reference)."""

    session_id: str
    plan_id: str
    model: str
    history: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@runtime_checkable
class PlanStore(Protocol):
    """Storage protocol for canonical plan schemas."""

    async def get(self, plan_id: str) -> CanonicalPlanSchema | None: ...

    async def save(self, plan: CanonicalPlanSchema) -> None: ...

    async def list_by_owner(self, owner_id: str) -> list[CanonicalPlanSchema]: ...

    async def delete(self, plan_id: str) -> bool: ...

    async def update_fields(
        self,
        plan_id: str,
        updates: dict[str, Any],
        expected_version: int | None = None,
    ) -> CanonicalPlanSchema | None: ...


@runtime_checkable
class SessionStore(Protocol):
    """Storage protocol for interview session data."""

    async def get(self, session_id: str) -> SessionDocument | None: ...

    async def save(self, session: SessionDocument) -> None: ...

    async def get_for_plan(self, plan_id: str) -> SessionDocument | None: ...

    async def delete_for_plan(self, plan_id: str) -> int: ...


@runtime_checkable
class UserProfileStore(Protocol):
    """Read/write local user profiles (synced from Auth0)."""

    async def get_by_sub(self, auth0_sub: str) -> UserProfile | None: ...

    async def upsert(self, profile: UserProfile) -> None: ...

    async def list_profiles(
        self, *, skip: int = 0, limit: int = 50
    ) -> list[UserProfile]: ...

    async def deactivate(self, auth0_sub: str) -> bool: ...


@runtime_checkable
class AuditStore(Protocol):
    """Append-only audit log storage."""

    async def append(self, entry: AuditEntry) -> None: ...

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
    ) -> list[AuditEntry]: ...
