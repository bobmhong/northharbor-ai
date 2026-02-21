"""Validation stage -- ensures the schema snapshot is internally consistent."""

from __future__ import annotations

from typing import Any

from backend.schema.canonical import CanonicalPlanSchema


def validate_schema(schema: CanonicalPlanSchema) -> dict[str, Any]:
    """Validate the canonical schema for pipeline readiness.

    Returns a dict with ``valid`` boolean and any ``errors`` found.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not schema.plan_id:
        errors.append("Missing plan_id")
    if not schema.owner_id:
        errors.append("Missing owner_id")

    if schema.client.birth_year.value == 0:
        errors.append("Birth year not set")
    if schema.accounts.retirement_balance.value == 0:
        warnings.append("Retirement balance is zero")
    if schema.spending.retirement_monthly_real.value == 0:
        warnings.append("Monthly retirement spending is zero")

    rw = schema.client.retirement_window.value
    if rw is not None and hasattr(rw, "min") and hasattr(rw, "max"):
        if rw.min > rw.max:
            errors.append("Retirement window min > max")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
