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
            "accounts.savings_rate_percent",
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
    "client.name": "What is your full name?",
    "client.birth_year": "What year were you born?",
    "location.state": "Which state do you live in?",
    "location.city": "Which city do you live in?",
    "income.current_gross_annual": "What is your current gross annual income?",
    "retirement_philosophy.success_probability_target": (
        "What success probability target would you like for your retirement plan? "
        "(e.g. 90%, 95%)"
    ),
    "retirement_philosophy.legacy_goal_total_real": (
        "Do you have a legacy goal — an amount you'd like to leave behind "
        "in today's dollars?"
    ),
    "client.retirement_window": (
        "What is your target retirement age range? For example, 62 to 67."
    ),
    "accounts.retirement_balance": (
        "What is the current balance of your retirement accounts?"
    ),
    "accounts.savings_rate_percent": (
        "What percentage of your income do you currently save for retirement?"
    ),
    "spending.retirement_monthly_real": (
        "How much do you expect to spend per month in retirement, "
        "in today's dollars?"
    ),
    "social_security.combined_at_67_monthly": (
        "What is your estimated combined monthly Social Security benefit at age 67?"
    ),
    "social_security.combined_at_70_monthly": (
        "What is your estimated combined monthly Social Security benefit at age 70?"
    ),
    "monte_carlo.required_success_rate": (
        "What minimum success rate would you accept for your retirement plan?"
    ),
    "monte_carlo.horizon_age": (
        "To what age should we model your plan? (e.g. 95)"
    ),
    "monte_carlo.legacy_floor": (
        "What is the minimum balance you'd like to have at the end of the plan?"
    ),
    "housing.status": "Do you currently rent or own your home?",
    "accounts.investment_strategy_id": (
        "What investment strategy best describes your portfolio? "
        "(e.g. conservative, moderate, aggressive)"
    ),
    "social_security.claiming_preference": (
        "At what age do you plan to start claiming Social Security? (62–70)"
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
}

OPTIONAL_TEMPLATES: dict[str, str] = {
    "housing.status": (
        "Would you like to share details about your housing situation? "
        "This helps us model costs more accurately."
    ),
    "accounts.investment_strategy_id": (
        "Would you like to specify your investment strategy? "
        "This helps us choose appropriate return assumptions."
    ),
    "social_security.claiming_preference": (
        "Do you have a preference for when to claim Social Security? "
        "The age you choose significantly affects your monthly benefit."
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
