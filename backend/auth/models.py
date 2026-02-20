"""Auth and user profile models.

Auth0 owns identity (email, password, OAuth links, MFA).
We store a lightweight local profile keyed by auth0_sub for app-specific data.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    CLIENT = "client"
    ADMIN = "admin"


class UserProfile(BaseModel):
    """Local user profile synced from Auth0 claims.

    Stored in MongoDB ``user_profiles`` collection, keyed by ``auth0_sub``.
    """

    auth0_sub: str
    email: EmailStr
    display_name: str
    role: UserRole = UserRole.CLIENT
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen_at: datetime | None = None
    preferences: dict[str, Any] = Field(default_factory=dict)


class Auth0Claims(BaseModel):
    """Decoded claims from an Auth0 JWT access token."""

    sub: str
    email: EmailStr | None = None
    name: str | None = None
    roles: list[UserRole] = Field(default_factory=lambda: [UserRole.CLIENT])
    email_verified: bool = False
    iss: str = ""
    aud: str | list[str] = ""
    exp: int = 0
    iat: int = 0

    @property
    def primary_role(self) -> UserRole:
        if UserRole.ADMIN in self.roles:
            return UserRole.ADMIN
        return UserRole.CLIENT


class AuditEntry(BaseModel):
    """Immutable audit log entry."""

    id: str
    auth0_sub: str
    action: str
    resource_type: str
    resource_id: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    ip_address: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
