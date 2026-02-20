"""Protocol definitions for North Harbor AI data stores.

Each protocol describes the contract for a single data domain.  Concrete
implementations (in-memory, MongoDB) satisfy these protocols through
structural subtyping -- no base-class inheritance required.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from backend.auth.models import AuditEntry, UserProfile


@runtime_checkable
class UserProfileStore(Protocol):
    """Read/write local user profiles (synced from Auth0)."""

    async def get_by_sub(self, auth0_sub: str) -> UserProfile | None:
        """Return a user profile by Auth0 subject, or None."""
        ...

    async def upsert(self, profile: UserProfile) -> None:
        """Create or update a user profile."""
        ...

    async def list_profiles(
        self, *, skip: int = 0, limit: int = 50
    ) -> list[UserProfile]:
        """Return paginated user profiles (admin use)."""
        ...

    async def deactivate(self, auth0_sub: str) -> bool:
        """Mark a user as inactive. Return True if found."""
        ...


@runtime_checkable
class AuditStore(Protocol):
    """Append-only audit log storage."""

    async def append(self, entry: AuditEntry) -> None:
        """Write an audit entry. Must never update or delete."""
        ...

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
        """Query audit entries with optional filters."""
        ...
