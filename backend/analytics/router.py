"""FastAPI analytics endpoints for LLM usage metrics."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.analytics.llm_tracker import get_llm_tracker
from backend.api import deps as api_deps

router = APIRouter(prefix="/api/admin/analytics", tags=["admin", "analytics"])


def _is_dev_mode() -> bool:
    """Check if running in development mode."""
    return os.getenv("ENVIRONMENT", "development") == "development"


class ModelUsage(BaseModel):
    model: str
    count: int


class PeriodMetrics(BaseModel):
    period: str
    total_requests: int
    total_tokens: int
    total_request_bytes: int
    total_response_bytes: int
    models_used: list[ModelUsage] = Field(default_factory=list)


class RecentCall(BaseModel):
    timestamp: str
    model: str
    request_bytes: int
    response_bytes: int
    estimated_tokens: int
    session_id: str | None = None


class LLMAnalyticsResponse(BaseModel):
    today: PeriodMetrics
    last_7_days: PeriodMetrics
    last_30_days: PeriodMetrics
    recent_calls: list[RecentCall] = Field(default_factory=list)


@router.get("/llm", response_model=LLMAnalyticsResponse)
async def get_llm_analytics() -> LLMAnalyticsResponse:
    """Get aggregated LLM usage metrics.

    Only accessible in development mode.
    """
    if not _is_dev_mode():
        raise HTTPException(
            status_code=403,
            detail="Analytics endpoint is only available in development mode",
        )

    tracker = get_llm_tracker(store=api_deps.get_llm_analytics_store())
    aggregated = await tracker.get_aggregated_metrics()
    recent = await tracker.get_recent_calls(limit=10)

    def to_period_metrics(data: Any) -> PeriodMetrics:
        return PeriodMetrics(
            period=data.period,
            total_requests=data.total_requests,
            total_tokens=data.total_tokens,
            total_request_bytes=data.total_request_bytes,
            total_response_bytes=data.total_response_bytes,
            models_used=[
                ModelUsage(model=model, count=count)
                for model, count in data.models_used.items()
            ],
        )

    return LLMAnalyticsResponse(
        today=to_period_metrics(aggregated["today"]),
        last_7_days=to_period_metrics(aggregated["last_7_days"]),
        last_30_days=to_period_metrics(aggregated["last_30_days"]),
        recent_calls=[
            RecentCall(
                timestamp=m.timestamp.isoformat(),
                model=m.model,
                request_bytes=m.request_bytes,
                response_bytes=m.response_bytes,
                estimated_tokens=m.estimated_tokens,
                session_id=m.session_id,
            )
            for m in recent
        ],
    )
