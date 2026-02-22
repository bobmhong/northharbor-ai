"""Tests for LLM analytics tracking and API access."""

from __future__ import annotations

import json
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


def _reset_tracker(monkeypatch, tmp_path) -> LLMTracker:
    monkeypatch.setattr(LLMTracker, "_instance", None)
    tracker = get_llm_tracker(store=InMemoryLLMAnalyticsStore())
    monkeypatch.setattr(api_deps, "get_llm_analytics_store", lambda: tracker._store)
    return tracker


def test_track_call_records_sizes_tokens_and_persists(tmp_path, monkeypatch) -> None:
    tracker = _reset_tracker(monkeypatch, tmp_path)

    request_content = "hello world"
    response_content = "ok"
    metric = tracker.track_call(
        model="gpt-4o-mini",
        request_content=request_content,
        response_content=response_content,
        session_id="abc-123",
    )

    assert metric.request_bytes == len(request_content.encode("utf-8"))
    assert metric.response_bytes == len(response_content.encode("utf-8"))
    assert metric.estimated_tokens == (len(request_content) + len(response_content)) // 4
    assert metric.session_id == "abc-123"

    recent = tracker.get_recent_calls(limit=1)
    persisted = json.loads(json.dumps([m.to_dict() for m in recent]))
    assert len(persisted) == 1
    assert persisted[0]["model"] == "gpt-4o-mini"


def test_aggregation_windows_and_model_counts(tmp_path, monkeypatch) -> None:
    tracker = _reset_tracker(monkeypatch, tmp_path)
    metrics = [
        _metric(days_ago=0, minutes_ago=5, model="gpt-4o-mini"),
        _metric(days_ago=2, model="gpt-4o-mini"),
        _metric(days_ago=20, model="gpt-4o"),
        _metric(days_ago=40, model="gpt-4o"),  # excluded from 30-day window
    ]
    for metric in metrics:
        tracker._store.append(metric)

    aggregated = tracker.get_aggregated_metrics()

    assert aggregated["today"].total_requests == 1
    assert aggregated["last_7_days"].total_requests == 2
    assert aggregated["last_30_days"].total_requests == 3
    assert aggregated["last_30_days"].models_used["gpt-4o-mini"] == 2
    assert aggregated["last_30_days"].models_used["gpt-4o"] == 1


def test_recent_calls_are_descending_and_limited(tmp_path, monkeypatch) -> None:
    tracker = _reset_tracker(monkeypatch, tmp_path)
    metrics = [
        _metric(days_ago=3),
        _metric(days_ago=2),
        _metric(days_ago=1),
        _metric(hours_ago=1),
    ]
    for metric in metrics:
        tracker._store.append(metric)

    recent = tracker.get_recent_calls(limit=2)

    assert len(recent) == 2
    assert recent[0].timestamp >= recent[1].timestamp


def test_llm_analytics_endpoint_returns_data_in_dev_mode(tmp_path, monkeypatch) -> None:
    _ = _reset_tracker(monkeypatch, tmp_path)
    tracker = get_llm_tracker()
    tracker.track_call(
        model="gpt-4o-mini",
        request_content="request text",
        response_content="response text",
        session_id="sess-1",
    )
    tracker.track_call(
        model="gpt-4o",
        request_content="another request",
        response_content="another response",
        session_id="sess-2",
    )

    monkeypatch.setenv("ENVIRONMENT", "development")
    client = TestClient(create_app())

    resp = client.get("/api/admin/analytics/llm")
    assert resp.status_code == 200
    data = resp.json()
    assert data["today"]["total_requests"] >= 2
    assert {"model": "gpt-4o-mini", "count": 1} in data["today"]["models_used"]
    assert {"model": "gpt-4o", "count": 1} in data["today"]["models_used"]
    assert len(data["recent_calls"]) >= 2


def test_llm_analytics_endpoint_forbidden_outside_dev(tmp_path, monkeypatch) -> None:
    _reset_tracker(monkeypatch, tmp_path)
    monkeypatch.setenv("ENVIRONMENT", "production")
    client = TestClient(create_app())

    resp = client.get("/api/admin/analytics/llm")
    assert resp.status_code == 403
    assert "development mode" in resp.json()["detail"]

