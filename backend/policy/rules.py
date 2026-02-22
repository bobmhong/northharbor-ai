"""Suitability rules, field dependencies, and branching logic.

These rules control which questions are gated behind prior answers
and which fields should be skipped based on plan state.
"""

from __future__ import annotations

from typing import Any

from backend.schema.canonical import CanonicalPlanSchema
from backend.schema.provenance import ProvenanceField


def _pf_value(pf: ProvenanceField | None) -> Any:
    if pf is None:
        return None
    return pf.value


def should_skip_mortgage_fields(schema: CanonicalPlanSchema) -> bool:
    """Skip mortgage-related questions if client rents."""
    status = _pf_value(schema.housing.status)
    if isinstance(status, str) and status.lower() in ("rent", "renting", "renter"):
        return True
    return False


def should_skip_employer_match(schema: CanonicalPlanSchema) -> bool:
    """Skip employer match questions if no employer plan."""
    has_plan = _pf_value(schema.accounts.has_employer_plan)
    # Skip if they explicitly said no to having an employer plan
    if has_plan is False or (isinstance(has_plan, str) and has_plan.lower() in ("no", "false")):
        return True
    # Also skip if account type indicates self-employed
    acct_type = _pf_value(schema.accounts.retirement_type)
    if isinstance(acct_type, str) and acct_type.lower() in (
        "ira",
        "roth_ira",
        "self_employed",
    ):
        return True
    return False


GATED_FIELDS: dict[str, str] = {
    "housing.mortgage_balance": "housing.status",
    "housing.mortgage_rate": "housing.status",
    "housing.mortgage_term_years": "housing.status",
    "housing.mortgage_payment_monthly": "housing.status",
    "accounts.employer_match_percent": "accounts.retirement_type",
    "accounts.employer_non_elective_percent": "accounts.retirement_type",
}


EXCLUSION_CHECKS: dict[str, Any] = {
    "housing.mortgage_balance": should_skip_mortgage_fields,
    "housing.mortgage_rate": should_skip_mortgage_fields,
    "housing.mortgage_term_years": should_skip_mortgage_fields,
    "housing.mortgage_payment_monthly": should_skip_mortgage_fields,
    "accounts.employer_match_percent": should_skip_employer_match,
    "accounts.employee_contribution_percent": should_skip_employer_match,
    "accounts.employer_non_elective_percent": should_skip_employer_match,
}
