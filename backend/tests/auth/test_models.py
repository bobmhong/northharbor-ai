"""Tests for auth models."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.auth.models import AuditEntry, Auth0Claims, UserProfile, UserRole


class TestUserProfile(unittest.TestCase):
    def test_default_role_is_client(self) -> None:
        profile = UserProfile(
            auth0_sub="auth0|123",
            email="test@example.com",
            display_name="Test User",
        )
        self.assertEqual(profile.role, UserRole.CLIENT)
        self.assertTrue(profile.is_active)

    def test_timestamps_auto_populated(self) -> None:
        profile = UserProfile(
            auth0_sub="auth0|123",
            email="test@example.com",
            display_name="Test User",
        )
        self.assertIsInstance(profile.created_at, datetime)
        self.assertIsInstance(profile.updated_at, datetime)

    def test_serialization_round_trip(self) -> None:
        profile = UserProfile(
            auth0_sub="google-oauth2|456",
            email="user@gmail.com",
            display_name="Google User",
            role=UserRole.ADMIN,
        )
        data = profile.model_dump(mode="json")
        restored = UserProfile.model_validate(data)
        self.assertEqual(restored.auth0_sub, profile.auth0_sub)
        self.assertEqual(restored.role, UserRole.ADMIN)


class TestAuth0Claims(unittest.TestCase):
    def test_primary_role_admin(self) -> None:
        claims = Auth0Claims(
            sub="auth0|admin",
            roles=[UserRole.CLIENT, UserRole.ADMIN],
        )
        self.assertEqual(claims.primary_role, UserRole.ADMIN)

    def test_primary_role_default_client(self) -> None:
        claims = Auth0Claims(sub="auth0|user")
        self.assertEqual(claims.primary_role, UserRole.CLIENT)

    def test_empty_roles_defaults_to_client(self) -> None:
        claims = Auth0Claims(sub="auth0|user", roles=[])
        self.assertEqual(claims.primary_role, UserRole.CLIENT)


class TestAuditEntry(unittest.TestCase):
    def test_creation(self) -> None:
        entry = AuditEntry(
            id="abc-123",
            auth0_sub="auth0|user1",
            action="plan.create",
            resource_type="plan",
            resource_id="plan-001",
        )
        self.assertEqual(entry.action, "plan.create")
        self.assertIsInstance(entry.timestamp, datetime)

    def test_details_default_empty(self) -> None:
        entry = AuditEntry(
            id="abc-456",
            auth0_sub="auth0|user1",
            action="login",
            resource_type="session",
        )
        self.assertEqual(entry.details, {})


if __name__ == "__main__":
    unittest.main()
