"""Tests for LLM analytics tracking and API access."""

from __future__ import annotations

import json
import os
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from backend.analytics.llm_tracker import LLMCallMetric, LLMTracker, get_llm_tracker
from backend.analytics.store import InMemoryLLMAnalyticsStore
from backend.api import deps as api_deps
from backend.api.app import create_app


def _metric(
    *,
    days_ago: int = 0,
    hours_ago: int = 0,
    minutes_ago: int = 0,
    model: str = "gpt-4o-mini",
    request_bytes: int = 100,
    response_bytes: int = 60,
    estimated_tokens: int = 40,
) -> LLMCallMetric:
    return LLMCallMetric(
        timestamp=datetime.now(timezone.utc)
        - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago),
        model=model,
        request_bytes=request_bytes,
        response_bytes=response_bytes,
        estimated_tokens=estimated_tokens,
        session_id="session-1",
    )


class TestLLMTracker(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._prev_instance = LLMTracker._instance
        LLMTracker._instance = None
        self._store = InMemoryLLMAnalyticsStore()
        self._tracker = get_llm_tracker(store=self._store)
        self._prev_get_store = api_deps.get_llm_analytics_store
        api_deps.get_llm_analytics_store = lambda: self._store

    def tearDown(self) -> None:
        LLMTracker._instance = self._prev_instance
        api_deps.get_llm_analytics_store = self._prev_get_store

    async def test_track_call_records_sizes_tokens_and_persists(self) -> None:
        request_content = "hello world"
        response_content = "ok"
        metric = await self._tracker.track_call(
            model="gpt-4o-mini",
            request_content=request_content,
            response_content=response_content,
            session_id="abc-123",
        )

        self.assertEqual(metric.request_bytes, len(request_content.encode("utf-8")))
        self.assertEqual(metric.response_bytes, len(response_content.encode("utf-8")))
        self.assertEqual(
            metric.estimated_tokens,
            (len(request_content) + len(response_content)) // 4,
        )
        self.assertEqual(metric.session_id, "abc-123")

        recent = await self._tracker.get_recent_calls(limit=1)
        persisted = json.loads(json.dumps([m.to_dict() for m in recent]))
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["model"], "gpt-4o-mini")

    async def test_aggregation_windows_and_model_counts(self) -> None:
        metrics = [
            _metric(days_ago=0, minutes_ago=5, model="gpt-4o-mini"),
            _metric(days_ago=2, model="gpt-4o-mini"),
            _metric(days_ago=20, model="gpt-4o"),
            _metric(days_ago=40, model="gpt-4o"),  # excluded from 30-day window
        ]
        for metric in metrics:
            await self._store.append(metric)

        aggregated = await self._tracker.get_aggregated_metrics()

        self.assertEqual(aggregated["today"].total_requests, 1)
        self.assertEqual(aggregated["last_7_days"].total_requests, 2)
        self.assertEqual(aggregated["last_30_days"].total_requests, 3)
        self.assertEqual(aggregated["last_30_days"].models_used["gpt-4o-mini"], 2)
        self.assertEqual(aggregated["last_30_days"].models_used["gpt-4o"], 1)

    async def test_recent_calls_are_descending_and_limited(self) -> None:
        metrics = [
            _metric(days_ago=3),
            _metric(days_ago=2),
            _metric(days_ago=1),
            _metric(hours_ago=1),
        ]
        for metric in metrics:
            await self._store.append(metric)

        recent = await self._tracker.get_recent_calls(limit=2)

        self.assertEqual(len(recent), 2)
        self.assertGreaterEqual(recent[0].timestamp, recent[1].timestamp)


class TestLLMAnalyticsEndpoint(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self._prev_instance = LLMTracker._instance
        LLMTracker._instance = None
        self._store = InMemoryLLMAnalyticsStore()
        self._tracker = get_llm_tracker(store=self._store)
        self._prev_get_store = api_deps.get_llm_analytics_store
        api_deps.get_llm_analytics_store = lambda: self._store
        self._prev_env = os.environ.get("ENVIRONMENT")

    def tearDown(self) -> None:
        LLMTracker._instance = self._prev_instance
        api_deps.get_llm_analytics_store = self._prev_get_store
        if self._prev_env is None:
            os.environ.pop("ENVIRONMENT", None)
        else:
            os.environ["ENVIRONMENT"] = self._prev_env

    async def test_endpoint_returns_data_in_dev_mode(self) -> None:
        tracker = get_llm_tracker()
        await tracker.track_call(
            model="gpt-4o-mini",
            request_content="request text",
            response_content="response text",
            session_id="sess-1",
        )
        await tracker.track_call(
            model="gpt-4o",
            request_content="another request",
            response_content="another response",
            session_id="sess-2",
        )

        os.environ["ENVIRONMENT"] = "development"
        client = TestClient(create_app())

        resp = client.get("/api/admin/analytics/llm")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreaterEqual(data["today"]["total_requests"], 2)
        self.assertIn({"model": "gpt-4o-mini", "count": 1}, data["today"]["models_used"])
        self.assertIn({"model": "gpt-4o", "count": 1}, data["today"]["models_used"])
        self.assertGreaterEqual(len(data["recent_calls"]), 2)

    async def test_endpoint_forbidden_outside_dev(self) -> None:
        os.environ["ENVIRONMENT"] = "production"
        client = TestClient(create_app())

        resp = client.get("/api/admin/analytics/llm")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("development mode", resp.json()["detail"])
