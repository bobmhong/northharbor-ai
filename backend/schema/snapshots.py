"""Schema snapshots -- immutable, hash-addressable copies of plan state.

Every mutation to a ``CanonicalPlanSchema`` produces a snapshot so we
have a full audit trail and can reproduce any prior state.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field

from backend.schema.canonical import CanonicalPlanSchema


class SchemaSnapshot(BaseModel):
    """Immutable snapshot of a canonical plan schema."""

    snapshot_id: str
    plan_id: str
    owner_id: str
    schema_version: str
    data: dict[str, Any]
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def create_snapshot(schema: CanonicalPlanSchema) -> SchemaSnapshot:
    """Serialize *schema* to canonical JSON and hash with SHA-256."""
    data = schema.model_dump(mode="json")
    digest = hashlib.sha256(_canonical_json(data).encode("utf-8")).hexdigest()
    return SchemaSnapshot(
        snapshot_id=digest,
        plan_id=schema.plan_id,
        owner_id=schema.owner_id,
        schema_version=schema.schema_version,
        data=data,
    )


@runtime_checkable
class SnapshotStore(Protocol):
    """Storage protocol for schema snapshots."""

    async def save(self, snapshot: SchemaSnapshot) -> None: ...

    async def get(self, snapshot_id: str) -> SchemaSnapshot | None: ...

    async def list_for_plan(
        self, plan_id: str, owner_id: str
    ) -> list[SchemaSnapshot]: ...


class MemorySnapshotStore:
    """In-memory snapshot store for testing."""

    def __init__(self) -> None:
        self._store: dict[str, SchemaSnapshot] = {}

    async def save(self, snapshot: SchemaSnapshot) -> None:
        self._store[snapshot.snapshot_id] = snapshot

    async def get(self, snapshot_id: str) -> SchemaSnapshot | None:
        return self._store.get(snapshot_id)

    async def list_for_plan(
        self, plan_id: str, owner_id: str
    ) -> list[SchemaSnapshot]:
        return sorted(
            (
                s
                for s in self._store.values()
                if s.plan_id == plan_id and s.owner_id == owner_id
            ),
            key=lambda s: s.created_at,
        )
