"""Table builder -- converts raw pipeline tables into TableSpec objects."""

from __future__ import annotations

from typing import Any

from backend.rendering.contracts import TableSpec


def build_table_specs(raw_tables: list[dict[str, Any]]) -> list[TableSpec]:
    """Convert raw table dicts from the pipeline into ``TableSpec`` objects."""
    return [
        TableSpec(
            id=t["id"],
            title=t["title"],
            columns=t.get("columns", []),
            rows=t.get("rows", []),
            section=t.get("section", "appendix"),
        )
        for t in raw_tables
    ]
