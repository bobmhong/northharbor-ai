"""MongoDB-backed session store using Motor async driver."""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import DESCENDING

from backend.stores.protocols import SessionDocument


class MongoSessionStore:
    """Async MongoDB store for interview session documents."""

    COLLECTION = "sessions"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db[self.COLLECTION]

    async def get(self, session_id: str) -> SessionDocument | None:
        doc = await self._col.find_one({"session_id": session_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return SessionDocument.model_validate(doc)

    async def save(self, session: SessionDocument) -> None:
        data = session.model_dump(mode="json")
        await self._col.update_one(
            {"session_id": session.session_id},
            {"$set": data},
            upsert=True,
        )

    async def get_for_plan(self, plan_id: str) -> SessionDocument | None:
        doc = await self._col.find_one(
            {"plan_id": plan_id},
            sort=[("created_at", DESCENDING)],
        )
        if doc is None:
            return None
        doc.pop("_id", None)
        return SessionDocument.model_validate(doc)

    async def delete_for_plan(self, plan_id: str) -> int:
        result = await self._col.delete_many({"plan_id": plan_id})
        return result.deleted_count

    async def ensure_indexes(self) -> None:
        await self._col.create_index("session_id", unique=True)
        await self._col.create_index("plan_id")
        await self._col.create_index("created_at")
