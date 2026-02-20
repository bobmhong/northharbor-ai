"""Tenant isolation: scopes all data queries to the authenticated user."""

from __future__ import annotations

from dataclasses import dataclass

from backend.auth.models import Auth0Claims


@dataclass(frozen=True)
class TenantScope:
    """Carries the authenticated user's owner_id for data scoping.

    Every store query for plan/result/report data must accept a
    ``TenantScope`` and filter by ``owner_id``.  This is enforced at
    the store protocol level so even buggy route handlers cannot leak
    cross-tenant data.
    """

    owner_id: str

    @classmethod
    def from_claims(cls, claims: Auth0Claims) -> TenantScope:
        return cls(owner_id=claims.sub)

    def as_filter(self) -> dict[str, str]:
        """Return a MongoDB query filter dict."""
        return {"owner_id": self.owner_id}
