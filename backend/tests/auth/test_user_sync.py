"""Tests for user profile sync from Auth0 claims."""

from __future__ import annotations

import unittest

from backend.auth.models import Auth0Claims, UserRole
from backend.auth.user_sync import sync_user_profile
from backend.stores.memory import MemoryUserProfileStore


class TestUserSync(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.store = MemoryUserProfileStore()

    async def test_creates_profile_on_first_login(self) -> None:
        claims = Auth0Claims(
            sub="auth0|new-user",
            email="new@example.com",
            name="New User",
            roles=[UserRole.CLIENT],
        )
        profile = await sync_user_profile(claims, self.store)
        self.assertEqual(profile.auth0_sub, "auth0|new-user")
        self.assertEqual(profile.email, "new@example.com")
        self.assertEqual(profile.role, UserRole.CLIENT)

        stored = await self.store.get_by_sub("auth0|new-user")
        self.assertIsNotNone(stored)

    async def test_updates_existing_profile(self) -> None:
        claims = Auth0Claims(
            sub="auth0|existing",
            email="old@example.com",
            name="Old Name",
        )
        await sync_user_profile(claims, self.store)

        updated_claims = Auth0Claims(
            sub="auth0|existing",
            email="new@example.com",
            name="New Name",
            roles=[UserRole.ADMIN],
        )
        profile = await sync_user_profile(updated_claims, self.store)
        self.assertEqual(profile.email, "new@example.com")
        self.assertEqual(profile.display_name, "New Name")
        self.assertEqual(profile.role, UserRole.ADMIN)
        self.assertIsNotNone(profile.last_seen_at)

    async def test_handles_missing_email_gracefully(self) -> None:
        claims = Auth0Claims(sub="auth0|no-email")
        profile = await sync_user_profile(claims, self.store)
        self.assertEqual(profile.email, "unknown@example.com")


if __name__ == "__main__":
    unittest.main()
