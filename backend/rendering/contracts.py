"""Rendering output contracts.

Defines the structured output formats for charts, tables, and report
artifacts consumed by the frontend.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChartSpec(BaseModel):
    """Declarative chart specification rendered by the frontend."""

    id: str
    title: str
    chart_type: Literal[
        "line", "bar", "scatter", "pie", "heatmap",
        "gauge", "radar", "area",
    ]
    description: str = ""
    echarts_option: dict[str, Any]
    data_source: str
    section: str = "dashboard"


class TableSpec(BaseModel):
    """Structured table specification for frontend rendering."""

    id: str
    title: str
    columns: list[dict[str, str]]
    rows: list[dict[str, Any]]
    section: str = "appendix"


class AIAnalysis(BaseModel):
    """AI analyst output -- reads only deterministic outputs."""

    interpretation: str
    key_tradeoffs: list[str] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)
    disclaimer: str = (
        "Analysis is based on modeled projections, not guarantees."
    )


class ReportArtifact(BaseModel):
    """Complete report artifact combining all pipeline outputs."""

    report_id: str
    plan_id: str
    pipeline_id: str
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    format: Literal["json"] = "json"
    metrics: dict[str, Any] = Field(default_factory=dict)
    tables: list[TableSpec] = Field(default_factory=list)
    chart_specs: list[ChartSpec] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    ai_analysis: AIAnalysis | None = None
