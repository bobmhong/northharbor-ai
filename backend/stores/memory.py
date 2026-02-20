"""In-memory store implementations for testing."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.auth.models import AuditEntry, UserProfile


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
