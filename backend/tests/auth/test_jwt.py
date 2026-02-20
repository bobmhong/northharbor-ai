"""Tests for JWT verification logic."""

from __future__ import annotations

import time
import unittest
from unittest.mock import AsyncMock, patch

from jose import JWTError
from jose import jwt as jose_jwt

from backend.auth.jwt import (
    ROLES_CLAIM_NAMESPACE,
    _find_rsa_key,
    clear_jwks_cache,
    verify_token,
)
from backend.auth.models import UserRole
from backend.tests.auth._test_keys import TEST_JWKS, TEST_PEM_PRIVATE_KEY

_DEFAULT_AUDIENCE = "https://api.northharbor.ai"
_DEFAULT_ISSUER = "https://test-tenant.auth0.com/"


def _make_test_token(
    sub: str = "auth0|test123",
    roles: list[str] | None = None,
    expired: bool = False,
    kid: str = "test-kid-001",
    audience: str = _DEFAULT_AUDIENCE,
    issuer: str = _DEFAULT_ISSUER,
) -> str:
    """Create a signed JWT for testing."""
    now = int(time.time())
    payload = {
        "sub": sub,
        "iss": issuer,
        "aud": audience,
        "iat": now,
        "exp": now - 3600 if expired else now + 3600,
        "email": "test@example.com",
        "email_verified": True,
    }
    if roles is not None:
        payload[ROLES_CLAIM_NAMESPACE] = roles

    return jose_jwt.encode(
        payload,
        TEST_PEM_PRIVATE_KEY,
        algorithm="RS256",
        headers={"kid": kid},
    )


class TestFindRsaKey(unittest.TestCase):
    def test_finds_matching_kid(self) -> None:
        token = _make_test_token()
        key = _find_rsa_key(TEST_JWKS, token)
        self.assertEqual(key["kid"], "test-kid-001")

    def test_raises_on_missing_kid(self) -> None:
        token = _make_test_token(kid="nonexistent-kid")
        with self.assertRaises(JWTError):
            _find_rsa_key(TEST_JWKS, token)


class TestVerifyToken(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        clear_jwks_cache()
        self._settings_patch = patch("backend.auth.jwt.get_settings")
        mock_settings = self._settings_patch.start()
        mock_settings.return_value.auth0_jwks_url = (
            "https://test-tenant.auth0.com/.well-known/jwks.json"
        )
        mock_settings.return_value.auth0_algorithms = "RS256"
        mock_settings.return_value.auth0_api_audience = _DEFAULT_AUDIENCE
        mock_settings.return_value.auth0_issuer = _DEFAULT_ISSUER

    def tearDown(self) -> None:
        self._settings_patch.stop()
        clear_jwks_cache()

    @patch("backend.auth.jwt._fetch_jwks", new_callable=AsyncMock)
    async def test_valid_token(self, mock_fetch: AsyncMock) -> None:
        mock_fetch.return_value = TEST_JWKS
        token = _make_test_token(roles=["client"])
        claims = await verify_token(token)
        self.assertEqual(claims.sub, "auth0|test123")
        self.assertIn(UserRole.CLIENT, claims.roles)

    @patch("backend.auth.jwt._fetch_jwks", new_callable=AsyncMock)
    async def test_admin_role_extracted(self, mock_fetch: AsyncMock) -> None:
        mock_fetch.return_value = TEST_JWKS
        token = _make_test_token(roles=["admin", "client"])
        claims = await verify_token(token)
        self.assertIn(UserRole.ADMIN, claims.roles)
        self.assertEqual(claims.primary_role, UserRole.ADMIN)

    @patch("backend.auth.jwt._fetch_jwks", new_callable=AsyncMock)
    async def test_missing_roles_defaults_to_client(
        self, mock_fetch: AsyncMock
    ) -> None:
        mock_fetch.return_value = TEST_JWKS
        token = _make_test_token(roles=None)
        claims = await verify_token(token)
        self.assertEqual(claims.roles, [UserRole.CLIENT])

    @patch("backend.auth.jwt._fetch_jwks", new_callable=AsyncMock)
    async def test_expired_token_rejected(
        self, mock_fetch: AsyncMock
    ) -> None:
        mock_fetch.return_value = TEST_JWKS
        token = _make_test_token(expired=True)
        with self.assertRaises(JWTError):
            await verify_token(token)

    @patch("backend.auth.jwt._fetch_jwks", new_callable=AsyncMock)
    async def test_wrong_audience_rejected(
        self, mock_fetch: AsyncMock
    ) -> None:
        mock_fetch.return_value = TEST_JWKS
        token = _make_test_token(audience="https://wrong-api.example.com")
        with self.assertRaises(JWTError):
            await verify_token(token)


if __name__ == "__main__":
    unittest.main()
