"""Store protocols for plans, sessions, and snapshots.

All store methods are async. In-memory implementations are trivially
async; Motor-backed implementations use native async I/O.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

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
