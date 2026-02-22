"""Field metadata, dependency groups, and question templates.

Every field in the canonical schema is registered here with its group,
priority, required/optional status, and the question template used when
the policy engine selects it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FieldGroup:
    """Logically related fields that are asked together."""

    name: str
    priority: int
    fields: list[str]
    required: bool = True


FIELD_GROUPS: list[FieldGroup] = [
    FieldGroup(
        "identity",
        priority=1,
        fields=["client.name", "client.birth_year"],
    ),
    FieldGroup(
        "location",
        priority=2,
        fields=["location.state", "location.city"],
    ),
    FieldGroup(
        "income",
        priority=3,
        fields=["income.current_gross_annual"],
    ),
    FieldGroup(
        "retirement_goals",
        priority=4,
        fields=[
            "retirement_philosophy.success_probability_target",
            "retirement_philosophy.legacy_goal_total_real",
            "client.retirement_window",
        ],
    ),
    FieldGroup(
        "accounts",
        priority=5,
        fields=[
            "accounts.retirement_balance",
            "accounts.has_employer_plan",
            "accounts.employer_match_percent",
            "accounts.employee_contribution_percent",
        ],
    ),
    FieldGroup(
        "spending",
        priority=6,
        fields=["spending.retirement_monthly_real"],
    ),
    FieldGroup(
        "social_security",
        priority=7,
        fields=[
            "social_security.combined_at_67_monthly",
            "social_security.combined_at_70_monthly",
        ],
    ),
    FieldGroup(
        "monte_carlo_params",
        priority=8,
        fields=[
            "monte_carlo.required_success_rate",
            "monte_carlo.horizon_age",
            "monte_carlo.legacy_floor",
        ],
    ),
    FieldGroup(
        "housing_details",
        priority=9,
        fields=["housing.status"],
        required=False,
    ),
    FieldGroup(
        "investment_strategy",
        priority=10,
        fields=["accounts.investment_strategy_id"],
        required=False,
    ),
    FieldGroup(
        "social_security_claiming",
        priority=11,
        fields=["social_security.claiming_preference"],
        required=False,
    ),
]


QUESTION_TEMPLATES: dict[str, str] = {
    "client.name": "Great to meet you. What should I call you?",
    "client.birth_year": "What year were you born?",
    "location.state": "Which state are you currently living in?",
    "location.city": "And what city are you in?",
    "income.current_gross_annual": "Could you share your current gross annual income?",
    "retirement_philosophy.success_probability_target": (
        "What level of plan success would help you feel comfortable? "
        "(for example, 90% or 95%)"
    ),
    "retirement_philosophy.legacy_goal_total_real": (
        "Would you like to leave a specific amount behind as a legacy "
        "(in today's dollars)?"
    ),
    "client.retirement_window": (
        "What retirement age are you aiming for? "
        "A single age or a range (like 62 to 67) both work."
    ),
    "accounts.retirement_balance": (
        "About how much do you currently have saved across retirement accounts?"
    ),
    "accounts.has_employer_plan": (
        "Does your employer offer a retirement savings plan like a 401(k)?"
    ),
    "accounts.employer_match_percent": (
        "How much does your employer match? "
        "For example, if they match 50% up to 6%, that is effectively 3%."
    ),
    "accounts.employee_contribution_percent": (
        "What percent of your income are you currently contributing?"
    ),
    "accounts.savings_rate_percent": (
        "Overall, what percent of your income are you saving for retirement?"
    ),
    "spending.retirement_monthly_real": (
        "Roughly how much do you expect to spend each month in retirement "
        "(in today's dollars)?"
    ),
    "social_security.combined_at_67_monthly": (
        "What do you expect your combined monthly Social Security to be at age 67?"
    ),
    "social_security.combined_at_70_monthly": (
        "And what would that monthly Social Security amount be at age 70?"
    ),
    "monte_carlo.required_success_rate": (
        "What minimum success rate would you consider acceptable for your plan?"
    ),
    "monte_carlo.horizon_age": (
        "Up to what age should we model your plan? (for example, 95)"
    ),
    "monte_carlo.legacy_floor": (
        "At the end of the plan horizon, what minimum balance would you like to preserve?"
    ),
    "housing.status": "Do you currently rent or own your home?",
    "accounts.investment_strategy_id": (
        "How would you describe your investment style today "
        "(for example: conservative, moderate, or aggressive)?"
    ),
    "social_security.claiming_preference": (
        "At what age are you planning to claim Social Security? "
        "For most people, full retirement age is around 67 (claiming range: 62-70)."
    ),
}

CONFIRM_TEMPLATES: dict[str, str] = {
    "client.name": "I have your name as {value}. Is that correct?",
    "client.birth_year": "I have your birth year as {value}. Is that right?",
    "income.current_gross_annual": (
        "I have your gross annual income as ${value:,}. Can you confirm?"
    ),
    "accounts.retirement_balance": (
        "I have your retirement balance as ${value:,}. Does that sound right?"
    ),
    "spending.retirement_monthly_real": (
        "I have your expected monthly retirement spending as ${value:,}. Correct?"
    ),
    "retirement_philosophy.success_probability_target": (
        "I have your plan success target set to {value:.0%}. "
        "This means your plan should have at least a {value:.0%} chance of "
        "lasting through retirement without running out of money. "
        "Does that sound right?"
    ),
}

OPTIONAL_TEMPLATES: dict[str, str] = {
    "housing.status": "Do you currently rent or own your home?",
    "accounts.investment_strategy_id": (
        "How would you describe your investment style today "
        "(for example: conservative, moderate, or aggressive)?"
    ),
    "social_security.claiming_preference": (
        "At what age are you planning to claim Social Security? "
        "For most people, full retirement age is around 67 (claiming range: 62-70)."
    ),
}


def all_required_fields() -> list[str]:
    """Return all required field paths in priority order."""
    fields: list[str] = []
    for group in sorted(FIELD_GROUPS, key=lambda g: g.priority):
        if group.required:
            fields.extend(group.fields)
    return fields


def all_optional_fields() -> list[str]:
    """Return all optional field paths in priority order."""
    fields: list[str] = []
    for group in sorted(FIELD_GROUPS, key=lambda g: g.priority):
        if not group.required:
            fields.extend(group.fields)
    return fields
