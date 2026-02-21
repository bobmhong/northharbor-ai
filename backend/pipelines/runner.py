"""Pipeline runner -- orchestrates validate -> normalize -> compute -> render.

Each stage receives the accumulated outputs from prior stages and the
original schema snapshot. Failures halt the pipeline.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

from backend.pipelines.contracts import (
    PipelineOutputs,
    PipelineRequest,
    PipelineResult,
    PipelineStage,
    StageResult,
)
from backend.pipelines.stages.backtest import run_backtest
from backend.pipelines.stages.charts import generate_chart_specs
from backend.pipelines.stages.derive import compute_derived_fields
from backend.pipelines.stages.monte_carlo import run_monte_carlo
from backend.pipelines.stages.normalize import normalize_inputs
from backend.pipelines.stages.recommend import build_recommendations
from backend.pipelines.stages.tables import generate_tables
from backend.pipelines.stages.validate import validate_schema
from backend.pipelines.stages.what_if import run_what_if
from backend.schema.canonical import CanonicalPlanSchema


def _elapsed_ms(start: float) -> int:
    return int((time.monotonic() - start) * 1000)


async def run_pipeline(
    request: PipelineRequest,
    schema: CanonicalPlanSchema,
) -> PipelineResult:
    """Execute the full computation pipeline.

    Stages run in order.  Each receives accumulated outputs from prior
    stages.  A failing stage halts the pipeline.
    """
    pipeline_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc)
    results: list[StageResult] = []
    outputs: dict[str, Any] = {}

    requested = {s.value for s in request.stages}

    stage_sequence: list[tuple[PipelineStage, str]] = [
        (PipelineStage.VALIDATE, "validate"),
        (PipelineStage.NORMALIZE, "normalize"),
        (PipelineStage.DERIVE, "derive"),
        (PipelineStage.MONTE_CARLO, "monte_carlo"),
        (PipelineStage.BACKTEST, "backtest"),
        (PipelineStage.WHAT_IF, "what_if"),
        (PipelineStage.RECOMMEND, "recommend"),
        (PipelineStage.TABLES, "tables"),
        (PipelineStage.CHARTS, "charts"),
    ]

    for stage_enum, stage_key in stage_sequence:
        if stage_key not in requested:
            results.append(StageResult(stage=stage_enum, status="skipped"))
            continue

        start = time.monotonic()
        try:
            if stage_key == "validate":
                validation = validate_schema(schema)
                outputs["validate"] = validation
                if not validation["valid"]:
                    results.append(StageResult(
                        stage=stage_enum,
                        status="failed",
                        duration_ms=_elapsed_ms(start),
                        errors=validation["errors"],
                    ))
                    break

            elif stage_key == "normalize":
                outputs["normalize"] = normalize_inputs(schema)

            elif stage_key == "derive":
                inputs = outputs.get("normalize", {})
                outputs["derive"] = compute_derived_fields(inputs)

            elif stage_key == "monte_carlo":
                inputs = outputs.get("normalize", {})
                derived = outputs.get("derive", {})
                outputs["monte_carlo"] = run_monte_carlo(
                    inputs, derived, seed=request.seed
                )

            elif stage_key == "backtest":
                inputs = outputs.get("normalize", {})
                derived = outputs.get("derive", {})
                mc = outputs.get("monte_carlo", {})
                outputs["backtest"] = run_backtest(inputs, derived, mc)

            elif stage_key == "what_if":
                inputs = outputs.get("normalize", {})
                derived = outputs.get("derive", {})
                mc = outputs.get("monte_carlo", {})
                outputs["what_if"] = run_what_if(
                    inputs, derived, mc, seed=request.seed
                )

            elif stage_key == "recommend":
                inputs = outputs.get("normalize", {})
                mc = outputs.get("monte_carlo", {})
                outputs["recommend"] = build_recommendations(inputs, mc)

            elif stage_key == "tables":
                inputs = outputs.get("normalize", {})
                derived = outputs.get("derive", {})
                mc = outputs.get("monte_carlo", {})
                bt = outputs.get("backtest", {})
                outputs["tables"] = generate_tables(inputs, derived, mc, bt)

            elif stage_key == "charts":
                inputs = outputs.get("normalize", {})
                derived = outputs.get("derive", {})
                mc = outputs.get("monte_carlo", {})
                bt = outputs.get("backtest", {})
                outputs["charts"] = generate_chart_specs(
                    inputs, derived, mc, bt
                )

            results.append(StageResult(
                stage=stage_enum,
                status="success",
                duration_ms=_elapsed_ms(start),
            ))

        except Exception as exc:
            results.append(StageResult(
                stage=stage_enum,
                status="failed",
                duration_ms=_elapsed_ms(start),
                errors=[str(exc)],
            ))
            break

    pipeline_outputs = PipelineOutputs(
        derived_fields=outputs.get("derive", {}),
        monte_carlo_results=outputs.get("monte_carlo", {}),
        backtest_results=outputs.get("backtest", {}),
        what_if_results=outputs.get("what_if", {}),
        recommendations=outputs.get("recommend", []),
        tables=outputs.get("tables", []),
        chart_specs=outputs.get("charts", []),
        metrics=_build_metrics(outputs),
    )

    return PipelineResult(
        pipeline_id=pipeline_id,
        plan_id=request.plan_id,
        owner_id=request.owner_id,
        schema_snapshot_id=request.schema_snapshot_id,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        stages=results,
        outputs=pipeline_outputs,
    )


def _build_metrics(outputs: dict[str, Any]) -> dict[str, Any]:
    """Extract top-level metrics from pipeline outputs."""
    mc = outputs.get("monte_carlo", {})
    assessment = mc.get("assessment", {})
    base_results = mc.get("base_results", [])

    recommended_age = assessment.get("recommended_retirement_age")
    recommended_row = next(
        (r for r in base_results if r.get("retirement_age") == recommended_age),
        None,
    )

    metrics: dict[str, Any] = {
        "recommended_retirement_age": recommended_age,
        "target_success_probability": assessment.get(
            "minimum_success_probability_target"
        ),
        "all_ages_meet_target": assessment.get("all_retirement_ages_meet_target"),
    }

    if recommended_row:
        metrics["recommended_age_success_probability"] = recommended_row.get(
            "success_probability"
        )
        metrics["recommended_age_terminal_p50"] = (
            recommended_row.get("terminal_balance_percentiles_real", {}).get("p50")
        )

    return metrics
