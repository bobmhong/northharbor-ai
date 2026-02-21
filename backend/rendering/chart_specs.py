"""Chart spec builder -- converts raw pipeline charts into ChartSpec objects."""

from __future__ import annotations

from typing import Any

from backend.rendering.contracts import ChartSpec


def build_chart_specs(raw_charts: list[dict[str, Any]]) -> list[ChartSpec]:
    """Convert raw chart dicts from the pipeline into ``ChartSpec`` objects."""
    return [
        ChartSpec(
            id=c["id"],
            title=c["title"],
            chart_type=c.get("chart_type", "bar"),
            description=c.get("description", ""),
            echarts_option=c.get("echarts_option", {}),
            data_source=c.get("data_source", ""),
            section=c.get("section", "dashboard"),
        )
        for c in raw_charts
    ]
