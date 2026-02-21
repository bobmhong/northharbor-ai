"""Output validation and guardrails for AI modules.

Validates that AI-generated content conforms to expected contracts
and flags potential hallucinations.
"""

from __future__ import annotations

import re
from typing import Any

from backend.schema.patch_ops import PatchResponse


def validate_extractor_output(raw_json: str) -> PatchResponse:
    """Parse and validate raw LLM JSON into a ``PatchResponse``.

    Raises ``ValueError`` if the JSON is malformed or doesn't conform
    to the PatchResponse contract.
    """
    return PatchResponse.model_validate_json(raw_json)


def _extract_numbers(text: str) -> set[str]:
    """Extract all numeric literals from *text*."""
    return set(re.findall(r"\b\d+(?:\.\d+)?(?:%|pp)?\b", text))


def verify_no_invented_numbers(
    analysis_text: str,
    context: dict[str, Any],
) -> list[str]:
    """Check that numbers in *analysis_text* appear in *context*.

    Returns a list of warnings for numbers found in the analysis text
    that don't appear anywhere in the serialized context.
    """
    context_str = str(context)
    context_numbers = _extract_numbers(context_str)
    analysis_numbers = _extract_numbers(analysis_text)

    trivial = {"0", "1", "2", "3", "4", "5", "100", "0.0", "1.0", "12"}
    suspicious = analysis_numbers - context_numbers - trivial

    warnings: list[str] = []
    for num in sorted(suspicious):
        warnings.append(
            f"Number '{num}' in analysis not found in pipeline context"
        )
    return warnings
