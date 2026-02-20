"""Audit log writer."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from backend.auth.models import AuditEntry, Auth0Claims
from backend.stores.protocols import AuditStore


async def log_action(
    store: AuditStore,
    *,
    user: Auth0Claims,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str = "",
) -> AuditEntry:
    """Create and persist an audit entry."""
    entry = AuditEntry(
        id=str(uuid.uuid4()),
        auth0_sub=user.sub,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details or {},
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc),
    )
    await store.append(entry)
    return entry
