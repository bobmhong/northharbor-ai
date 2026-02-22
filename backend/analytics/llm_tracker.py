"""LLM usage analytics tracker.

Tracks request/response metrics for LLM calls with in-memory storage
and optional JSON persistence.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass
class LLMCallMetric:
    """Represents a single LLM call's metrics."""

    timestamp: datetime
    model: str
    request_bytes: int
    response_bytes: int
    estimated_tokens: int
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "model": self.model,
            "request_bytes": self.request_bytes,
            "response_bytes": self.response_bytes,
            "estimated_tokens": self.estimated_tokens,
            "session_id": self.session_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LLMCallMetric:
        return cls(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            model=data["model"],
            request_bytes=data["request_bytes"],
            response_bytes=data["response_bytes"],
            estimated_tokens=data["estimated_tokens"],
            session_id=data.get("session_id"),
        )


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a time period."""

    period: str
    total_requests: int
    total_tokens: int
    total_request_bytes: int
    total_response_bytes: int
    models_used: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "period": self.period,
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "total_request_bytes": self.total_request_bytes,
            "total_response_bytes": self.total_response_bytes,
            "models_used": self.models_used,
        }


class LLMTracker:
    """Tracks LLM usage metrics with in-memory storage and optional persistence."""

    _instance: LLMTracker | None = None
    _PERSISTENCE_PATH = Path(".data/llm_analytics.json")

    def __init__(self) -> None:
        self._metrics: list[LLMCallMetric] = []
        self._loaded = False

    @classmethod
    def get_instance(cls) -> LLMTracker:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_loaded(self) -> None:
        """Load persisted metrics if not already loaded."""
        if self._loaded:
            return
        self._loaded = True

        if not self._PERSISTENCE_PATH.exists():
            return

        try:
            raw = json.loads(self._PERSISTENCE_PATH.read_text(encoding="utf-8"))
            metrics_raw = raw.get("metrics", [])
            for m in metrics_raw:
                try:
                    self._metrics.append(LLMCallMetric.from_dict(m))
                except Exception:
                    continue
        except Exception:
            pass

    def _persist(self) -> None:
        """Persist metrics to JSON file."""
        self._PERSISTENCE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "metrics": [m.to_dict() for m in self._metrics],
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        self._PERSISTENCE_PATH.write_text(
            json.dumps(data, ensure_ascii=True, indent=2), encoding="utf-8"
        )

    def track_call(
        self,
        *,
        model: str,
        request_content: str,
        response_content: str,
        session_id: str | None = None,
    ) -> LLMCallMetric:
        """Track a single LLM call."""
        self._ensure_loaded()

        request_bytes = len(request_content.encode("utf-8"))
        response_bytes = len(response_content.encode("utf-8"))
        total_chars = len(request_content) + len(response_content)
        estimated_tokens = total_chars // 4

        metric = LLMCallMetric(
            timestamp=datetime.now(timezone.utc),
            model=model,
            request_bytes=request_bytes,
            response_bytes=response_bytes,
            estimated_tokens=estimated_tokens,
            session_id=session_id,
        )

        self._metrics.append(metric)
        self._persist()

        return metric

    def get_metrics_since(self, since: datetime) -> list[LLMCallMetric]:
        """Get all metrics since a given datetime."""
        self._ensure_loaded()
        return [m for m in self._metrics if m.timestamp >= since]

    def aggregate(self, period: str, since: datetime) -> AggregatedMetrics:
        """Aggregate metrics for a time period."""
        metrics = self.get_metrics_since(since)

        total_requests = len(metrics)
        total_tokens = sum(m.estimated_tokens for m in metrics)
        total_request_bytes = sum(m.request_bytes for m in metrics)
        total_response_bytes = sum(m.response_bytes for m in metrics)

        models_used: dict[str, int] = {}
        for m in metrics:
            models_used[m.model] = models_used.get(m.model, 0) + 1

        return AggregatedMetrics(
            period=period,
            total_requests=total_requests,
            total_tokens=total_tokens,
            total_request_bytes=total_request_bytes,
            total_response_bytes=total_response_bytes,
            models_used=models_used,
        )

    def get_aggregated_metrics(self) -> dict[str, AggregatedMetrics]:
        """Get metrics aggregated by today, last 7 days, and last 30 days."""
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        return {
            "today": self.aggregate("today", today_start),
            "last_7_days": self.aggregate("last_7_days", now - timedelta(days=7)),
            "last_30_days": self.aggregate("last_30_days", now - timedelta(days=30)),
        }

    def get_recent_calls(self, limit: int = 10) -> list[LLMCallMetric]:
        """Get the most recent LLM calls."""
        self._ensure_loaded()
        return sorted(self._metrics, key=lambda m: m.timestamp, reverse=True)[:limit]

    def clear(self) -> None:
        """Clear all metrics (useful for testing)."""
        self._metrics = []
        self._loaded = True
        if self._PERSISTENCE_PATH.exists():
            self._PERSISTENCE_PATH.unlink()


def get_llm_tracker() -> LLMTracker:
    """Get the global LLM tracker instance."""
    return LLMTracker.get_instance()
