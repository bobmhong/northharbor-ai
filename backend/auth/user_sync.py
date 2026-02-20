"""Sync Auth0 claims to a local user profile on each request."""

from __future__ import annotations

from datetime import datetime, timezone

from backend.auth.models import Auth0Claims, UserProfile
from backend.stores.protocols import UserProfileStore


async def sync_user_profile(
    claims: Auth0Claims,
    store: UserProfileStore,
) -> UserProfile:
    """Upsert a local user profile from Auth0 JWT claims.

    Called on every authenticated request.  Creates the profile on
    first login and updates ``last_seen_at`` on subsequent requests.
    """
    now = datetime.now(timezone.utc)
    existing = await store.get_by_sub(claims.sub)

    if existing is not None:
        existing.last_seen_at = now
        existing.role = claims.primary_role
        existing.updated_at = now
        if claims.email:
            existing.email = claims.email
        if claims.name:
            existing.display_name = claims.name
        await store.upsert(existing)
        return existing

    profile = UserProfile(
        auth0_sub=claims.sub,
        email=claims.email or "unknown@example.com",
        display_name=claims.name or "New User",
        role=claims.primary_role,
        created_at=now,
        updated_at=now,
        last_seen_at=now,
    )
    await store.upsert(profile)
    return profile
