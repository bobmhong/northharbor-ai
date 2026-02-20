"""PatchOps contract -- the ONLY format an LLM may emit to modify plan data.

The system validates each ``PatchOp`` against the canonical schema,
applies valid ops, and returns a ``PatchResult`` summarising what
happened.
"""

from __future__ import annotations

import types
from datetime import datetime, timezone
from typing import Any, Literal, get_args, get_origin

from pydantic import BaseModel, Field

from backend.schema.canonical import CanonicalPlanSchema
from backend.schema.provenance import FieldSource, ProvenanceField


class PatchOp(BaseModel):
    """A single structured update to the canonical schema."""

    op: Literal["set", "remove", "append"]
    path: str
    value: Any = None
    source: FieldSource = FieldSource.USER
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class PatchResponse(BaseModel):
    """AI extractor output contract.  This is the ONLY format the LLM may emit."""

    patch_ops: list[PatchOp]
    next_question: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
    rationale: str = ""


class PatchResult(BaseModel):
    """Result of applying a batch of patches to the schema."""

    applied: list[PatchOp]
    rejected: list[tuple[PatchOp, str]]
    schema_snapshot_id: str
    warnings: list[str] = Field(default_factory=list)


def _is_provenance_annotation(annotation: Any) -> bool:
    """Return True if *annotation* is ``ProvenanceField`` or ``ProvenanceField | None``."""
    if annotation is ProvenanceField:
        return True
    origin = get_origin(annotation)
    if origin is types.UnionType:
        return ProvenanceField in get_args(annotation)
    # typing.Union fallback (Python <3.10 style)
    import typing

    if origin is typing.Union:
        return ProvenanceField in get_args(annotation)
    return False


def _resolve_parent(
    obj: Any, segments: list[str]
) -> tuple[Any, str]:
    """Walk *segments* on *obj*, returning ``(parent, final_key)``.

    Supports Pydantic models (attribute access) and dicts (key access).
    Raises ``ValueError`` when a segment cannot be resolved.
    """
    current = obj
    for seg in segments[:-1]:
        if isinstance(current, BaseModel):
            if seg not in type(current).model_fields:
                raise ValueError(f"Unknown field '{seg}'")
            current = getattr(current, seg)
        elif isinstance(current, dict):
            if seg not in current:
                raise ValueError(f"Unknown key '{seg}'")
            current = current[seg]
        else:
            raise ValueError(
                f"Cannot traverse into {type(current).__name__}"
            )
    return current, segments[-1]


def _apply_set(parent: Any, key: str, patch: PatchOp) -> None:
    if isinstance(parent, BaseModel):
        cls_fields = type(parent).model_fields
        if key not in cls_fields:
            raise ValueError(f"Unknown field '{key}'")
        annotation = cls_fields[key].annotation
        if _is_provenance_annotation(annotation):
            new_pf = ProvenanceField(
                value=patch.value,
                source=patch.source,
                confidence=patch.confidence,
            )
            object.__setattr__(parent, key, new_pf)
        else:
            object.__setattr__(parent, key, patch.value)
    elif isinstance(parent, dict):
        parent[key] = ProvenanceField(
            value=patch.value,
            source=patch.source,
            confidence=patch.confidence,
        )
    else:
        raise ValueError(
            f"Cannot set on {type(parent).__name__}"
        )


def _apply_remove(parent: Any, key: str) -> None:
    if isinstance(parent, BaseModel):
        cls_fields = type(parent).model_fields
        if key not in cls_fields:
            raise ValueError(f"Unknown field '{key}'")
        annotation = cls_fields[key].annotation
        is_optional = False
        origin = get_origin(annotation)
        if origin is types.UnionType:
            is_optional = type(None) in get_args(annotation)
        else:
            import typing

            if origin is typing.Union:
                is_optional = type(None) in get_args(annotation)
        if not is_optional:
            raise ValueError(
                f"Cannot remove required field '{key}'"
            )
        object.__setattr__(parent, key, None)
    elif isinstance(parent, dict):
        if key not in parent:
            raise ValueError(f"Key '{key}' not found")
        del parent[key]
    else:
        raise ValueError(
            f"Cannot remove from {type(parent).__name__}"
        )


def _apply_append(parent: Any, key: str, patch: PatchOp) -> None:
    if isinstance(parent, BaseModel):
        target = getattr(parent, key, None)
    elif isinstance(parent, dict):
        target = parent.get(key)
    else:
        raise ValueError(
            f"Cannot access '{key}' on {type(parent).__name__}"
        )
    if not isinstance(target, list):
        raise ValueError(
            f"Cannot append to non-list field '{key}'"
        )
    target.append(patch.value)


def apply_patches(
    schema: CanonicalPlanSchema,
    patches: list[PatchOp],
) -> tuple[CanonicalPlanSchema, PatchResult]:
    """Apply *patches* to a deep copy of *schema*.

    Returns ``(updated_schema, result)``.  The original schema is
    never mutated.
    """
    from backend.schema.snapshots import create_snapshot

    model = schema.model_copy(deep=True)
    applied: list[PatchOp] = []
    rejected: list[tuple[PatchOp, str]] = []
    warnings: list[str] = []

    for patch in patches:
        segments = patch.path.split(".")
        if not segments or not all(segments):
            rejected.append((patch, "Empty or malformed path"))
            continue
        try:
            parent, key = _resolve_parent(model, segments)
            if patch.op == "set":
                _apply_set(parent, key, patch)
            elif patch.op == "remove":
                _apply_remove(parent, key)
            elif patch.op == "append":
                _apply_append(parent, key, patch)
            applied.append(patch)
        except ValueError as exc:
            rejected.append((patch, str(exc)))

    model.updated_at = datetime.now(timezone.utc)
    snapshot = create_snapshot(model)

    return model, PatchResult(
        applied=applied,
        rejected=rejected,
        schema_snapshot_id=snapshot.snapshot_id,
        warnings=warnings,
    )
