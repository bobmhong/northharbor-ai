"""MongoDB store implementations for user profiles and audit log."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pymongo.database import Database

from backend.auth.models import AuditEntry, UserProfile


class MongoDBUserProfileStore:
    """MongoDB-backed UserProfileStore."""

    COLLECTION = "user_profiles"

    def __init__(self, db: Database[Any]) -> None:
        self._col = db[self.COLLECTION]

    async def get_by_sub(self, auth0_sub: str) -> UserProfile | None:
        doc = self._col.find_one({"auth0_sub": auth0_sub})
        if doc is None:
            return None
        doc.pop("_id", None)
        return UserProfile.model_validate(doc)

    async def upsert(self, profile: UserProfile) -> None:
        self._col.update_one(
            {"auth0_sub": profile.auth0_sub},
            {"$set": profile.model_dump(mode="json")},
            upsert=True,
        )

    async def list_profiles(
        self, *, skip: int = 0, limit: int = 50
    ) -> list[UserProfile]:
        docs = (
            self._col.find()
            .sort("created_at", 1)
            .skip(skip)
            .limit(limit)
        )
        results = []
        for doc in docs:
            doc.pop("_id", None)
            results.append(UserProfile.model_validate(doc))
        return results

    async def deactivate(self, auth0_sub: str) -> bool:
        result = self._col.update_one(
            {"auth0_sub": auth0_sub},
            {
                "$set": {
                    "is_active": False,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            },
        )
        return result.matched_count > 0

    def ensure_indexes(self) -> None:
        self._col.create_index("auth0_sub", unique=True)
        self._col.create_index("email")


class MongoDBAuditStore:
    """Append-only MongoDB audit log.

    This store intentionally has no update or delete methods.
    """

    COLLECTION = "audit_log"

    def __init__(self, db: Database[Any]) -> None:
        self._col = db[self.COLLECTION]

    async def append(self, entry: AuditEntry) -> None:
        self._col.insert_one(entry.model_dump(mode="json"))

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
        query: dict[str, Any] = {}
        if auth0_sub:
            query["auth0_sub"] = auth0_sub
        if action:
            query["action"] = action
        if resource_type:
            query["resource_type"] = resource_type
        if since or until:
            ts_filter: dict[str, str] = {}
            if since:
                ts_filter["$gte"] = since
            if until:
                ts_filter["$lte"] = until
            query["timestamp"] = ts_filter

        docs = (
            self._col.find(query)
            .sort("timestamp", -1)
            .skip(skip)
            .limit(limit)
        )
        results = []
        for doc in docs:
            doc.pop("_id", None)
            results.append(AuditEntry.model_validate(doc))
        return results

    def ensure_indexes(self) -> None:
        self._col.create_index("auth0_sub")
        self._col.create_index("action")
        self._col.create_index("timestamp")
        self._col.create_index("resource_type")
