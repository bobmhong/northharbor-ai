"""MongoDB-backed plan store using Motor async driver."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, ReturnDocument

from backend.schema.canonical import CanonicalPlanSchema


class MongoPlanStore:
    """Async MongoDB store for canonical plan schemas."""

    COLLECTION = "plans"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db[self.COLLECTION]

    async def get(self, plan_id: str) -> CanonicalPlanSchema | None:
        doc = await self._col.find_one({"plan_id": plan_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return CanonicalPlanSchema.model_validate(doc)

    async def save(self, plan: CanonicalPlanSchema) -> None:
        data = plan.model_dump(mode="json")
        await self._col.update_one(
            {"plan_id": plan.plan_id},
            {"$set": data},
            upsert=True,
        )

    async def list_by_owner(
        self, owner_id: str
    ) -> list[CanonicalPlanSchema]:
        results: list[CanonicalPlanSchema] = []
        async for doc in self._col.find({"owner_id": owner_id}):
            doc.pop("_id", None)
            results.append(CanonicalPlanSchema.model_validate(doc))
        return results

    async def delete(self, plan_id: str) -> bool:
        result = await self._col.delete_one({"plan_id": plan_id})
        return result.deleted_count > 0

    async def update_fields(
        self,
        plan_id: str,
        updates: dict[str, Any],
        expected_version: int | None = None,
    ) -> CanonicalPlanSchema | None:
        query: dict[str, Any] = {"plan_id": plan_id}
        if expected_version is not None:
            query["version"] = expected_version

        updates["updated_at"] = datetime.now(timezone.utc).isoformat()

        doc = await self._col.find_one_and_update(
            query,
            {"$set": updates, "$inc": {"version": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            return None
        doc.pop("_id", None)
        return CanonicalPlanSchema.model_validate(doc)

    async def ensure_indexes(self) -> None:
        await self._col.create_index("plan_id", unique=True)
        await self._col.create_index("owner_id")
        await self._col.create_index(
            [("owner_id", ASCENDING), ("status", ASCENDING)]
        )
