"""Metrics builder -- extracts key metrics for dashboard display."""

from __future__ import annotations

from typing import Any

from backend.pipelines.contracts import PipelineResult


def build_metrics_summary(result: PipelineResult) -> dict[str, Any]:
    """Build a summary metrics dict from pipeline results."""
    metrics = dict(result.outputs.metrics)

    stages_summary: dict[str, Any] = {}
    total_ms = 0
    for stage in result.stages:
        stages_summary[stage.stage.value] = {
            "status": stage.status,
            "duration_ms": stage.duration_ms,
        }
        total_ms += stage.duration_ms

    metrics["pipeline_id"] = result.pipeline_id
    metrics["total_duration_ms"] = total_ms
    metrics["stages_summary"] = stages_summary
    metrics["recommendations_count"] = len(result.outputs.recommendations)
    metrics["charts_count"] = len(result.outputs.chart_specs)
    metrics["tables_count"] = len(result.outputs.tables)

    return metrics
