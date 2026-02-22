"""Deterministic policy engine for interview question selection.

Given the current canonical schema state, the engine decides which
question to ask next based on:
1. Missing required fields (by group priority)
2. Low-confidence fields worth confirming
3. Optional enrichment fields
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

from backend.schema.canonical import CanonicalPlanSchema
from backend.schema.provenance import ProvenanceField

from backend.policy.field_registry import (
    CONFIRM_TEMPLATES,
    FIELD_GROUPS,
    OPTIONAL_TEMPLATES,
    QUESTION_TEMPLATES,
    FieldGroup,
)
from backend.policy.rules import EXCLUSION_CHECKS

FIELD_FRIENDLY_NAMES: dict[str, str] = {
    "client.name": "your name",
    "client.birth_year": "your birth year",
    "location.state": "your state",
    "location.city": "your city",
    "income.current_gross_annual": "your annual income",
    "retirement_philosophy.success_probability_target": "your success target",
    "retirement_philosophy.legacy_goal_total_real": "your legacy goal",
    "client.retirement_window": "your retirement age range",
    "accounts.retirement_balance": "your retirement balance",
    "accounts.has_employer_plan": "whether you have an employer retirement plan",
    "accounts.employer_match_percent": "your employer match percentage",
    "accounts.employee_contribution_percent": "your contribution percentage",
    "accounts.savings_rate_percent": "your savings rate",
    "spending.retirement_monthly_real": "your monthly retirement spending",
    "social_security.combined_at_67_monthly": "your Social Security estimate at age 67",
    "social_security.combined_at_70_monthly": "your Social Security estimate at age 70",
    "monte_carlo.required_success_rate": "your minimum success rate",
    "monte_carlo.horizon_age": "your planning horizon age",
    "monte_carlo.legacy_floor": "your minimum ending balance target",
    "housing.status": "your housing status",
    "accounts.investment_strategy_id": "your investment strategy",
    "social_security.claiming_preference": "your Social Security claiming age",
}


def _friendly_field_name(path: str) -> str:
    return FIELD_FRIENDLY_NAMES.get(path, "that value")


class PolicyDecision(BaseModel):
    """Result of the policy engine's next-question selection."""

    next_question: str | None = None
    target_field: str | None = None
    missing_fields: list[str] = []
    reason: str = ""
    interview_complete: bool = False


def _resolve_field(schema: CanonicalPlanSchema, path: str) -> Any:
    """Walk a dot-delimited path on the schema, returning the leaf value."""
    segments = path.split(".")
    current: Any = schema
    for seg in segments:
        if isinstance(current, BaseModel):
            current = getattr(current, seg, None)
        elif isinstance(current, dict):
            current = current.get(seg)
        else:
            return None
        if current is None:
            return None
    return current


def _is_populated(value: Any) -> bool:
    """Return True if the field has a meaningful value."""
    if value is None:
        return False
    if isinstance(value, ProvenanceField):
        v = value.value
        if v is None:
            return False
        if isinstance(v, str) and v.strip() == "":
            return False
        # Explicitly handle booleans before int check (bool is subclass of int)
        if isinstance(v, bool):
            return True  # Both True and False are valid populated values
        if isinstance(v, (int, float)) and v == 0:
            return False
        return True
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def _is_low_confidence(value: Any, threshold: float = 0.7) -> bool:
    """Return True if a populated field has confidence below *threshold*."""
    if isinstance(value, ProvenanceField) and value.value is not None:
        return value.confidence < threshold
    return False


def find_missing_required_fields(
    schema: CanonicalPlanSchema,
) -> list[str]:
    """Return paths of all required fields that are not yet populated."""
    missing: list[str] = []
    for group in sorted(FIELD_GROUPS, key=lambda g: g.priority):
        if not group.required:
            continue
        for field_path in group.fields:
            exclusion_fn = EXCLUSION_CHECKS.get(field_path)
            if exclusion_fn is not None and exclusion_fn(schema):
                continue
            value = _resolve_field(schema, field_path)
            if not _is_populated(value):
                missing.append(field_path)
    return missing


def find_low_confidence_fields(
    schema: CanonicalPlanSchema,
    threshold: float = 0.7,
) -> list[tuple[str, float]]:
    """Return (path, confidence) for populated fields below *threshold*."""
    low: list[tuple[str, float]] = []
    for group in sorted(FIELD_GROUPS, key=lambda g: g.priority):
        for field_path in group.fields:
            value = _resolve_field(schema, field_path)
            if isinstance(value, ProvenanceField) and _is_low_confidence(
                value, threshold
            ):
                low.append((field_path, value.confidence))
    return low


def find_missing_optional_fields(
    schema: CanonicalPlanSchema,
) -> list[str]:
    """Return paths of optional fields that haven't been answered."""
    missing: list[str] = []
    for group in sorted(FIELD_GROUPS, key=lambda g: g.priority):
        if group.required:
            continue
        for field_path in group.fields:
            exclusion_fn = EXCLUSION_CHECKS.get(field_path)
            if exclusion_fn is not None and exclusion_fn(schema):
                continue
            value = _resolve_field(schema, field_path)
            if not _is_populated(value):
                missing.append(field_path)
    return missing


def select_next_question(
    schema: CanonicalPlanSchema,
    *,
    confidence_threshold: float = 0.7,
) -> PolicyDecision:
    """Deterministically select the next question to ask the user."""

    missing = find_missing_required_fields(schema)
    if missing:
        for group in sorted(FIELD_GROUPS, key=lambda g: g.priority):
            if not group.required:
                continue
            group_missing = [f for f in group.fields if f in missing]
            if group_missing:
                target = group_missing[0]
                question = QUESTION_TEMPLATES.get(
                    target, f"Please share {_friendly_field_name(target)}."
                )
                
                # Dynamic question for employee contribution with match context
                if target == "accounts.employee_contribution_percent":
                    match_field = _resolve_field(schema, "accounts.employer_match_percent")
                    if isinstance(match_field, ProvenanceField) and match_field.value:
                        match_pct = match_field.value
                        # Calculate minimum contribution to get full match
                        # Assuming typical 50% match, minimum is 2x the match
                        min_for_full_match = int(match_pct * 2)
                        question = (
                            f"What percentage of your income do you contribute to your retirement plan? "
                            f"Your employer matches up to {match_pct}%. "
                            f"Contributing at least {min_for_full_match}% captures the full match."
                        )
                
                return PolicyDecision(
                    next_question=question,
                    target_field=target,
                    missing_fields=group_missing,
                    reason=f"Required group '{group.name}' incomplete",
                )

    low_confidence = find_low_confidence_fields(schema, confidence_threshold)
    if low_confidence:
        field_path, confidence = low_confidence[0]
        value = _resolve_field(schema, field_path)
        display_value = value.value if isinstance(value, ProvenanceField) else value
        template = CONFIRM_TEMPLATES.get(
            field_path,
            f"I have {_friendly_field_name(field_path)} as {{value}}. Can you confirm?",
        )
        try:
            question = template.format(value=display_value)
        except (KeyError, ValueError):
            question = f"Can you confirm {_friendly_field_name(field_path)}?"
        return PolicyDecision(
            next_question=question,
            target_field=field_path,
            missing_fields=[],
            reason=f"Field '{field_path}' has confidence {confidence:.2f}",
        )

    optional_missing = find_missing_optional_fields(schema)
    if optional_missing:
        target = optional_missing[0]
        return PolicyDecision(
            next_question=OPTIONAL_TEMPLATES.get(
                target,
                QUESTION_TEMPLATES.get(
                    target, f"Would you like to share {_friendly_field_name(target)}?"
                ),
            ),
            target_field=target,
            missing_fields=[],
            reason="Optional enrichment",
        )

    return PolicyDecision(
        next_question=None,
        reason="Interview complete",
        interview_complete=True,
    )
