"""AI Extractor -- converts natural language into structured PatchOps.

The extractor calls an LLM (or a stub in tests) to turn free-text user
responses into ``PatchResponse`` objects, then validates and applies
patches to the canonical schema.
"""

from __future__ import annotations

import json
from typing import Any, Protocol

from backend.ai.guardrails import validate_extractor_output
from backend.ai.prompts.extractor import (
    EXTRACTOR_SYSTEM_PROMPT,
    SCHEMA_CONTEXT_TEMPLATE,
)
from backend.policy.engine import PolicyDecision, select_next_question
from backend.schema.canonical import CanonicalPlanSchema
from backend.schema.patch_ops import PatchOp, PatchResponse, PatchResult, apply_patches


class LLMClient(Protocol):
    """Minimal protocol for LLM completion calls."""

    async def create(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        response_format: dict[str, str] | None,
    ) -> str:
        """Return the raw text content of the LLM response."""
        ...


class StubLLMClient:
    """Stub LLM that returns empty patches -- useful for testing the pipeline."""

    async def create(
        self,
        *,
        model: str = "stub",
        messages: list[dict[str, str]] | None = None,
        temperature: float = 0.0,
        response_format: dict[str, str] | None = None,
    ) -> str:
        return json.dumps(
            {
                "patch_ops": [],
                "next_question": None,
                "missing_fields": [],
                "rationale": "Stub LLM -- no extraction performed.",
            }
        )


async def extract_patches(
    user_message: str,
    schema: CanonicalPlanSchema,
    conversation_history: list[dict[str, str]],
    *,
    llm: LLMClient,
    model: str = "gpt-4o-mini",
) -> PatchResponse:
    """Call the LLM to extract structured patch operations from *user_message*."""
    schema_json = schema.model_dump_json(indent=2)
    context = SCHEMA_CONTEXT_TEMPLATE.format(schema_json=schema_json)

    messages: list[dict[str, str]] = [
        {"role": "system", "content": EXTRACTOR_SYSTEM_PROMPT},
        {"role": "system", "content": context},
        *conversation_history,
        {"role": "user", "content": user_message},
    ]

    raw = await llm.create(
        model=model,
        messages=messages,
        temperature=0.1,
        response_format={"type": "json_object"},
    )

    return validate_extractor_output(raw)


async def extract_and_apply(
    user_message: str,
    schema: CanonicalPlanSchema,
    conversation_history: list[dict[str, str]],
    *,
    llm: LLMClient,
    model: str = "gpt-4o-mini",
) -> tuple[CanonicalPlanSchema, PatchResult, PolicyDecision]:
    """Extract patches from *user_message*, apply them, and decide next question.

    Returns ``(updated_schema, patch_result, policy_decision)``.
    """
    patch_response = await extract_patches(
        user_message, schema, conversation_history, llm=llm, model=model
    )

    updated_schema, patch_result = apply_patches(schema, patch_response.patch_ops)

    policy_decision = select_next_question(updated_schema)

    return updated_schema, patch_result, policy_decision
