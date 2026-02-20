"""Provenance tracking for canonical schema fields.

Every user-facing field in the canonical schema is wrapped in a
``ProvenanceField`` so we always know *where* a value came from, how
confident we are in it, and when it was last touched.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FieldSource(str, Enum):
    """Origin of a field value."""

    USER = "user"
    PROVIDED = "provided"
    INFERRED = "inferred"
    DEFAULT = "default"


class ProvenanceField(BaseModel):
    """Wraps a schema value with provenance metadata."""

    value: Any
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source: FieldSource = FieldSource.USER
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    note: str | None = None
