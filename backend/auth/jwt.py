"""Auth0 JWT verification using RS256 and cached JWKS."""

from __future__ import annotations

import time
from typing import Any

import httpx
from jose import JWTError, jwt

from backend.auth.models import Auth0Claims, UserRole
from backend.config import get_settings

ROLES_CLAIM_NAMESPACE = "https://northharbor.dev/roles"

_jwks_cache: dict[str, Any] = {}
_jwks_cache_expiry: float = 0
_JWKS_CACHE_TTL_SECONDS = 3600


async def _fetch_jwks() -> dict[str, Any]:
    """Fetch JWKS from Auth0, with in-memory caching."""
    global _jwks_cache, _jwks_cache_expiry

    now = time.monotonic()
    if _jwks_cache and now < _jwks_cache_expiry:
        return _jwks_cache

    settings = get_settings()
    async with httpx.AsyncClient() as client:
        resp = await client.get(settings.auth0_jwks_url)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cache_expiry = now + _JWKS_CACHE_TTL_SECONDS
        return _jwks_cache


def _find_rsa_key(jwks: dict[str, Any], token: str) -> dict[str, str]:
    """Match the JWT kid to a key in the JWKS."""
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    raise JWTError(f"No matching key found for kid={kid}")


async def verify_token(token: str) -> Auth0Claims:
    """Verify an Auth0 JWT and return decoded claims.

    Raises ``JWTError`` on invalid/expired/tampered tokens.
    """
    settings = get_settings()
    jwks = await _fetch_jwks()
    rsa_key = _find_rsa_key(jwks, token)

    payload = jwt.decode(
        token,
        rsa_key,
        algorithms=[settings.auth0_algorithms],
        audience=settings.auth0_api_audience,
        issuer=settings.auth0_issuer,
    )

    raw_roles = payload.get(ROLES_CLAIM_NAMESPACE, [])
    roles = []
    for r in raw_roles:
        try:
            roles.append(UserRole(r))
        except ValueError:
            continue
    if not roles:
        roles = [UserRole.CLIENT]

    return Auth0Claims(
        sub=payload["sub"],
        email=payload.get("email"),
        name=payload.get("name"),
        roles=roles,
        email_verified=payload.get("email_verified", False),
        iss=payload.get("iss", ""),
        aud=payload.get("aud", ""),
        exp=payload.get("exp", 0),
        iat=payload.get("iat", 0),
    )


def clear_jwks_cache() -> None:
    """Reset the JWKS cache (useful in tests)."""
    global _jwks_cache, _jwks_cache_expiry
    _jwks_cache = {}
    _jwks_cache_expiry = 0
