"""Question catalog and templates for the interview wizard.

Re-exports the question templates from the policy field registry and
provides helper functions for building conversational prompts.
"""

from __future__ import annotations

from backend.policy.field_registry import (
    CONFIRM_TEMPLATES,
    OPTIONAL_TEMPLATES,
    QUESTION_TEMPLATES,
)


def welcome_message() -> str:
    return (
        "Hi, I'm Sage — your retirement planning assistant. "
        "I'll walk you through a few questions to build a personalized "
        "plan. Let's get started!"
    )


def completion_message() -> str:
    return (
        "Great — I have all the information I need to build your "
        "retirement plan! I'm ready to run Monte Carlo simulations "
        "and generate your personalized projections. When you're "
        "ready, click **Run Analysis** below to see your results."
    )


def question_for_field(field_path: str) -> str:
    """Return the question template for a given field path."""
    return QUESTION_TEMPLATES.get(
        field_path,
        f"Could you provide information about {field_path.replace('.', ' ')}?",
    )
