"""Role-based access control guards."""

from __future__ import annotations

from typing import Callable

from fastapi import Depends, HTTPException, status

from backend.auth.deps import get_current_user
from backend.auth.models import Auth0Claims, UserRole


def require_role(role: UserRole) -> Callable[..., Auth0Claims]:
    """Return a FastAPI dependency that enforces a minimum role.

    Usage::

        @router.get("/admin/users")
        async def list_users(
            user: Auth0Claims = Depends(require_role(UserRole.ADMIN)),
        ):
            ...
    """

    async def _check(
        user: Auth0Claims = Depends(get_current_user),
    ) -> Auth0Claims:
        if role == UserRole.ADMIN and UserRole.ADMIN not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )
        return user

    return _check
