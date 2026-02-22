"""Shared analytics model types."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
        timestamp = data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        return cls(
            timestamp=timestamp,
            model=data["model"],
            request_bytes=data["request_bytes"],
            response_bytes=data["response_bytes"],
            estimated_tokens=data["estimated_tokens"],
            session_id=data.get("session_id"),
        )
