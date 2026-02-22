"""Storage backends for LLM analytics metrics."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from pymongo.collection import Collection
from pymongo.database import Database

from backend.analytics.models import LLMCallMetric


@runtime_checkable
class LLMAnalyticsStore(Protocol):
    """Interface for persisting and querying LLM analytics metrics."""

    def append(self, metric: LLMCallMetric) -> None:
        """Persist a single metric entry."""
        ...

    def get_since(self, since: datetime) -> list[LLMCallMetric]:
        """Return metrics whose timestamp is >= since."""
        ...

    def get_recent(self, limit: int = 10) -> list[LLMCallMetric]:
        """Return metrics ordered by descending timestamp."""
        ...

    def clear(self) -> None:
        """Delete all persisted metrics."""
        ...


class InMemoryLLMAnalyticsStore:
    """Simple in-memory analytics store for tests and fallback."""

    def __init__(self) -> None:
        self._metrics: list[LLMCallMetric] = []

    def append(self, metric: LLMCallMetric) -> None:
        self._metrics.append(metric)

    def get_since(self, since: datetime) -> list[LLMCallMetric]:
        return [m for m in self._metrics if m.timestamp >= since]

    def get_recent(self, limit: int = 10) -> list[LLMCallMetric]:
        return sorted(self._metrics, key=lambda m: m.timestamp, reverse=True)[:limit]

    def clear(self) -> None:
        self._metrics = []


class MongoLLMAnalyticsStore:
    """MongoDB analytics store for production-style persistence."""

    COLLECTION = "llm_usage_events"

    def __init__(self, db: Database[Any]) -> None:
        self._col: Collection[Any] = db[self.COLLECTION]

    def append(self, metric: LLMCallMetric) -> None:
        self._col.insert_one(asdict(metric))

    def get_since(self, since: datetime) -> list[LLMCallMetric]:
        docs = self._col.find({"timestamp": {"$gte": since}}).sort("timestamp", 1)
        return [self._from_doc(doc) for doc in docs]

    def get_recent(self, limit: int = 10) -> list[LLMCallMetric]:
        docs = self._col.find().sort("timestamp", -1).limit(limit)
        return [self._from_doc(doc) for doc in docs]

    def clear(self) -> None:
        self._col.delete_many({})

    def ensure_indexes(self) -> None:
        self._col.create_index("timestamp")
        self._col.create_index([("model", 1), ("timestamp", -1)])
        self._col.create_index([("session_id", 1), ("timestamp", -1)])

    @staticmethod
    def _from_doc(doc: dict[str, Any]) -> LLMCallMetric:
        doc.pop("_id", None)
        return LLMCallMetric(**doc)
