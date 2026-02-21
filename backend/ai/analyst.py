"""AI Analyst module -- reads deterministic pipeline outputs and produces
human-readable interpretation with guardrails.

The analyst ONLY reads from pipeline outputs and schema snapshots.
It never performs computation itself.
"""

from __future__ import annotations

import json
from typing import Any

from backend.ai.extractor import LLMClient
from backend.ai.guardrails import verify_no_invented_numbers
from backend.ai.prompts.analyst import ANALYST_SYSTEM_PROMPT
from backend.pipelines.contracts import PipelineResult
from backend.rendering.contracts import AIAnalysis
from backend.schema.canonical import CanonicalPlanSchema


def _extract_mc_summary(result: PipelineResult) -> dict[str, Any]:
    """Extract a compact Monte Carlo summary for the analyst prompt."""
    mc = result.outputs.monte_carlo_results
    assessment = mc.get("assessment", {})
    base_results = mc.get("base_results", [])

    summary: dict[str, Any] = {
        "recommended_retirement_age": assessment.get("recommended_retirement_age"),
        "target_success_probability": assessment.get("minimum_success_probability_target"),
        "all_ages_meet_target": assessment.get("all_retirement_ages_meet_target"),
    }

    for r in base_results:
        age = r.get("retirement_age")
        summary[f"age_{age}_success"] = r.get("success_probability")
        summary[f"age_{age}_terminal_p50"] = (
            r.get("terminal_balance_percentiles_real", {}).get("p50")
        )

    return summary


def _extract_stress_summary(result: PipelineResult) -> dict[str, Any]:
    """Extract sensitivity/stress test summary."""
    mc = result.outputs.monte_carlo_results
    sensitivity = mc.get("sensitivity_results", {})

    summary: dict[str, Any] = {}
    for scenario_name, results in sensitivity.items():
        scenario_summary = {}
        for r in results:
            age = r.get("retirement_age")
            scenario_summary[f"age_{age}"] = r.get("success_probability")
        summary[scenario_name] = scenario_summary

    return summary


def build_analyst_context(
    schema: CanonicalPlanSchema,
    result: PipelineResult,
) -> dict[str, Any]:
    """Build the context dict passed to the analyst LLM."""
    return {
        "plan_id": schema.plan_id,
        "metrics": result.outputs.metrics,
        "recommendations": result.outputs.recommendations,
        "monte_carlo_summary": _extract_mc_summary(result),
        "stress_test_summary": _extract_stress_summary(result),
        "backtest_summary": result.outputs.backtest_results,
        "what_if_summary": result.outputs.what_if_results,
    }


async def analyze_pipeline_outputs(
    schema: CanonicalPlanSchema,
    result: PipelineResult,
    *,
    llm: LLMClient,
    model: str = "gpt-4o",
) -> AIAnalysis:
    """Produce an AI analysis of deterministic pipeline outputs.

    The analyst reads ONLY from pipeline outputs (no direct computation).
    A guardrail checks for hallucinated numbers after generation.
    """
    context = build_analyst_context(schema, result)

    raw = await llm.create(
        model=model,
        messages=[
            {"role": "system", "content": ANALYST_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(context, default=str)},
        ],
        temperature=0.2,
        response_format={"type": "json_object"},
    )

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return AIAnalysis(
            interpretation="Unable to parse analyst response.",
            confidence_notes=["Analyst response was not valid JSON."],
        )

    analysis = AIAnalysis(
        interpretation=parsed.get("interpretation", ""),
        key_tradeoffs=parsed.get("key_tradeoffs", []),
        suggested_next_steps=parsed.get("suggested_next_steps", []),
        confidence_notes=parsed.get("confidence_notes", []),
        disclaimer=parsed.get(
            "disclaimer",
            "Analysis is based on modeled projections, not guarantees.",
        ),
    )

    hallucination_warnings = verify_no_invented_numbers(
        analysis.interpretation, context
    )
    if hallucination_warnings:
        analysis.confidence_notes.extend(hallucination_warnings)

    return analysis


def build_template_analysis(
    result: PipelineResult,
) -> AIAnalysis:
    """Fallback template-based analysis when LLM is not available.

    Uses only data from the pipeline result — no AI calls.
    """
    metrics = result.outputs.metrics
    recommended_age = metrics.get("recommended_retirement_age", "N/A")
    success_prob = metrics.get("recommended_age_success_probability")
    terminal_p50 = metrics.get("recommended_age_terminal_p50")
    target = metrics.get("target_success_probability", 0.95)

    interpretation_parts = [
        f"Based on the analysis, the recommended retirement age is {recommended_age}.",
    ]
    if success_prob is not None:
        interpretation_parts.append(
            f"At this age, the Monte Carlo simulation shows a "
            f"{success_prob * 100:.1f}% probability of success "
            f"against the {float(target) * 100:.1f}% target."
        )
    if terminal_p50 is not None:
        interpretation_parts.append(
            f"The median terminal balance at this age is "
            f"${terminal_p50:,.0f}."
        )

    tradeoffs: list[str] = []
    if success_prob is not None and success_prob < float(target):
        tradeoffs.append(
            "Current plan does not meet the target success probability. "
            "Consider increasing savings or delaying retirement."
        )

    recs = result.outputs.recommendations
    next_steps = [r.get("message", "") for r in recs[:3] if r.get("message")]

    return AIAnalysis(
        interpretation=" ".join(interpretation_parts),
        key_tradeoffs=tradeoffs,
        suggested_next_steps=next_steps,
        confidence_notes=[
            "This is a template-based analysis. Enable the AI analyst "
            "for more detailed interpretation."
        ],
    )
