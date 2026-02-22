"""MongoDB-backed snapshot store using Motor async driver."""

from __future__ import annotations

from pymongo import ASCENDING
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.schema.snapshots import SchemaSnapshot


class MongoSnapshotStore:
    """Async MongoDB store for schema snapshots."""

    COLLECTION = "snapshots"

    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._col = db[self.COLLECTION]

    async def save(self, snapshot: SchemaSnapshot) -> None:
        data = snapshot.model_dump(mode="json")
        await self._col.update_one(
            {"snapshot_id": snapshot.snapshot_id},
            {"$set": data},
            upsert=True,
        )

    async def get(self, snapshot_id: str) -> SchemaSnapshot | None:
        doc = await self._col.find_one({"snapshot_id": snapshot_id})
        if doc is None:
            return None
        doc.pop("_id", None)
        return SchemaSnapshot.model_validate(doc)

    async def list_for_plan(
        self, plan_id: str, owner_id: str
    ) -> list[SchemaSnapshot]:
        results: list[SchemaSnapshot] = []
        cursor = self._col.find(
            {"plan_id": plan_id, "owner_id": owner_id}
        ).sort("created_at", ASCENDING)
        async for doc in cursor:
            doc.pop("_id", None)
            results.append(SchemaSnapshot.model_validate(doc))
        return results

    async def ensure_indexes(self) -> None:
        await self._col.create_index("snapshot_id", unique=True)
        await self._col.create_index(
            [
                ("plan_id", ASCENDING),
                ("owner_id", ASCENDING),
                ("created_at", ASCENDING),
            ]
        )
