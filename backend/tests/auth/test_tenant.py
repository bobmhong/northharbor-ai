"""Tests for tenant isolation."""

from __future__ import annotations

import unittest

from backend.auth.models import Auth0Claims
from backend.auth.tenant import TenantScope


class TestTenantScope(unittest.TestCase):
    def test_from_claims(self) -> None:
        claims = Auth0Claims(sub="auth0|user-abc")
        scope = TenantScope.from_claims(claims)
        self.assertEqual(scope.owner_id, "auth0|user-abc")

    def test_as_filter(self) -> None:
        scope = TenantScope(owner_id="auth0|user-xyz")
        self.assertEqual(scope.as_filter(), {"owner_id": "auth0|user-xyz"})

    def test_different_users_different_scopes(self) -> None:
        scope_a = TenantScope(owner_id="auth0|user-a")
        scope_b = TenantScope(owner_id="auth0|user-b")
        self.assertNotEqual(scope_a.owner_id, scope_b.owner_id)
        self.assertNotEqual(scope_a.as_filter(), scope_b.as_filter())

    def test_frozen(self) -> None:
        scope = TenantScope(owner_id="auth0|immutable")
        with self.assertRaises(AttributeError):
            scope.owner_id = "auth0|tampered"  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
