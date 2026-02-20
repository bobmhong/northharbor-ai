"""Tests for in-memory store implementations."""

from __future__ import annotations

import unittest

from backend.auth.models import AuditEntry, UserProfile, UserRole
from backend.stores.memory import MemoryAuditStore, MemoryUserProfileStore


class TestMemoryUserProfileStore(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.store = MemoryUserProfileStore()

    async def test_get_nonexistent_returns_none(self) -> None:
        result = await self.store.get_by_sub("auth0|nobody")
        self.assertIsNone(result)

    async def test_upsert_and_get(self) -> None:
        profile = UserProfile(
            auth0_sub="auth0|user1",
            email="user1@example.com",
            display_name="User One",
        )
        await self.store.upsert(profile)
        loaded = await self.store.get_by_sub("auth0|user1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.email, "user1@example.com")  # type: ignore[union-attr]

    async def test_upsert_overwrites(self) -> None:
        profile = UserProfile(
            auth0_sub="auth0|user1",
            email="old@example.com",
            display_name="Old",
        )
        await self.store.upsert(profile)

        profile.email = "new@example.com"  # type: ignore[assignment]
        profile.display_name = "New"
        await self.store.upsert(profile)

        loaded = await self.store.get_by_sub("auth0|user1")
        self.assertEqual(loaded.email, "new@example.com")  # type: ignore[union-attr]

    async def test_list_profiles_pagination(self) -> None:
        for i in range(5):
            await self.store.upsert(
                UserProfile(
                    auth0_sub=f"auth0|user{i}",
                    email=f"user{i}@example.com",
                    display_name=f"User {i}",
                )
            )
        page1 = await self.store.list_profiles(skip=0, limit=3)
        self.assertEqual(len(page1), 3)
        page2 = await self.store.list_profiles(skip=3, limit=3)
        self.assertEqual(len(page2), 2)

    async def test_deactivate(self) -> None:
        await self.store.upsert(
            UserProfile(
                auth0_sub="auth0|deactivate-me",
                email="bye@example.com",
                display_name="Goodbye",
            )
        )
        result = await self.store.deactivate("auth0|deactivate-me")
        self.assertTrue(result)

        profile = await self.store.get_by_sub("auth0|deactivate-me")
        self.assertFalse(profile.is_active)  # type: ignore[union-attr]

    async def test_deactivate_nonexistent_returns_false(self) -> None:
        result = await self.store.deactivate("auth0|ghost")
        self.assertFalse(result)

    async def test_tenant_isolation(self) -> None:
        """User A's profile is not returned when querying for User B."""
        await self.store.upsert(
            UserProfile(
                auth0_sub="auth0|user-a",
                email="a@example.com",
                display_name="User A",
            )
        )
        result = await self.store.get_by_sub("auth0|user-b")
        self.assertIsNone(result)


class TestMemoryAuditStore(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.store = MemoryAuditStore()

    async def test_append_and_query(self) -> None:
        entry = AuditEntry(
            id="e1",
            auth0_sub="auth0|user1",
            action="plan.create",
            resource_type="plan",
            resource_id="plan-001",
        )
        await self.store.append(entry)
        results = await self.store.query()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].action, "plan.create")

    async def test_filter_by_user(self) -> None:
        await self.store.append(
            AuditEntry(id="e1", auth0_sub="auth0|a", action="x", resource_type="y")
        )
        await self.store.append(
            AuditEntry(id="e2", auth0_sub="auth0|b", action="x", resource_type="y")
        )
        results = await self.store.query(auth0_sub="auth0|a")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].auth0_sub, "auth0|a")

    async def test_filter_by_action(self) -> None:
        await self.store.append(
            AuditEntry(id="e1", auth0_sub="u", action="login", resource_type="session")
        )
        await self.store.append(
            AuditEntry(id="e2", auth0_sub="u", action="plan.create", resource_type="plan")
        )
        results = await self.store.query(action="login")
        self.assertEqual(len(results), 1)

    async def test_pagination(self) -> None:
        for i in range(10):
            await self.store.append(
                AuditEntry(
                    id=f"e{i}",
                    auth0_sub="u",
                    action="test",
                    resource_type="test",
                )
            )
        page = await self.store.query(skip=5, limit=3)
        self.assertEqual(len(page), 3)


if __name__ == "__main__":
    unittest.main()
