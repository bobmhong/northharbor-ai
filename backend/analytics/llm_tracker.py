"""LLM usage analytics tracker."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from backend.analytics.models import LLMCallMetric
from backend.analytics.store import InMemoryLLMAnalyticsStore, LLMAnalyticsStore


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
    """Tracks LLM usage metrics through a pluggable store backend."""

    _instance: LLMTracker | None = None

    def __init__(self, store: LLMAnalyticsStore | None = None) -> None:
        self._store: LLMAnalyticsStore = store or InMemoryLLMAnalyticsStore()

    @classmethod
    def get_instance(cls, store: LLMAnalyticsStore | None = None) -> LLMTracker:
        if cls._instance is None:
            cls._instance = cls(store=store)
        elif store is not None:
            cls._instance.set_store(store)
        return cls._instance

    def set_store(self, store: LLMAnalyticsStore) -> None:
        """Swap tracker storage backend."""
        self._store = store

    def track_call(
        self,
        *,
        model: str,
        request_content: str,
        response_content: str,
        session_id: str | None = None,
    ) -> LLMCallMetric:
        """Track a single LLM call."""
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

        self._store.append(metric)
        return metric

    def get_metrics_since(self, since: datetime) -> list[LLMCallMetric]:
        """Get all metrics since a given datetime."""
        return self._store.get_since(since)

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
        return self._store.get_recent(limit=limit)

    def clear(self) -> None:
        """Clear all metrics (useful for testing)."""
        self._store.clear()


def get_llm_tracker(store: LLMAnalyticsStore | None = None) -> LLMTracker:
    """Get the global LLM tracker instance."""
    return LLMTracker.get_instance(store=store)
