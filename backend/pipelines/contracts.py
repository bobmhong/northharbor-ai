"""Pipeline request/result contracts and stage definitions."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class PipelineStage(str, Enum):
    VALIDATE = "validate"
    NORMALIZE = "normalize"
    DERIVE = "derive"
    MONTE_CARLO = "monte_carlo"
    BACKTEST = "backtest"
    WHAT_IF = "what_if"
    RECOMMEND = "recommend"
    TABLES = "tables"
    CHARTS = "charts"


class PipelineRequest(BaseModel):
    plan_id: str
    owner_id: str
    schema_snapshot_id: str
    stages: list[PipelineStage] = Field(
        default_factory=lambda: list(PipelineStage)
    )
    seed: int = 42
    options: dict[str, Any] = Field(default_factory=dict)


class StageResult(BaseModel):
    stage: PipelineStage
    status: Literal["success", "skipped", "failed"]
    duration_ms: int = 0
    artifact_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class PipelineOutputs(BaseModel):
    metrics: dict[str, Any] = Field(default_factory=dict)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    chart_specs: list[dict[str, Any]] = Field(default_factory=list)
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    derived_fields: dict[str, Any] = Field(default_factory=dict)
    monte_carlo_results: dict[str, Any] = Field(default_factory=dict)
    backtest_results: dict[str, Any] = Field(default_factory=dict)
    what_if_results: dict[str, Any] = Field(default_factory=dict)


class PipelineResult(BaseModel):
    pipeline_id: str
    plan_id: str
    owner_id: str
    schema_snapshot_id: str
    started_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    completed_at: datetime | None = None
    stages: list[StageResult] = Field(default_factory=list)
    outputs: PipelineOutputs = Field(default_factory=PipelineOutputs)
