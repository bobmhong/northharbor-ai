"""FastAPI pipeline and report endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.deps import get_plan, get_snapshot_store, store_plan
from backend.pipelines.contracts import PipelineRequest, PipelineResult, PipelineStage
from backend.pipelines.runner import run_pipeline
from backend.rendering.chart_specs import build_chart_specs
from backend.rendering.contracts import ReportArtifact
from backend.rendering.metrics import build_metrics_summary
from backend.rendering.tables import build_table_specs
from backend.schema.snapshots import create_snapshot

router = APIRouter(prefix="/api", tags=["pipelines"])

_reports: dict[str, ReportArtifact] = {}
_pipeline_results: dict[str, PipelineResult] = {}


class RunPipelineRequest(BaseModel):
    plan_id: str
    owner_id: str = "anonymous"
    seed: int = 42
    stages: list[PipelineStage] = Field(
        default_factory=lambda: list(PipelineStage)
    )


class PlanSummary(BaseModel):
    plan_id: str
    owner_id: str
    status: str
    created_at: str
    updated_at: str


@router.post("/pipelines/run", response_model=PipelineResult)
async def run_pipeline_endpoint(req: RunPipelineRequest) -> PipelineResult:
    """Run the computation pipeline for a plan."""
    schema = get_plan(req.plan_id)
    if schema is None:
        raise HTTPException(status_code=404, detail="Plan not found")

    snapshot = create_snapshot(schema)
    snapshot_store = get_snapshot_store()
    await snapshot_store.save(snapshot)

    pipeline_req = PipelineRequest(
        plan_id=req.plan_id,
        owner_id=req.owner_id,
        schema_snapshot_id=snapshot.snapshot_id,
        stages=req.stages,
        seed=req.seed,
    )

    result = await run_pipeline(pipeline_req, schema)
    _pipeline_results[result.pipeline_id] = result

    report = ReportArtifact(
        report_id=result.pipeline_id,
        plan_id=req.plan_id,
        pipeline_id=result.pipeline_id,
        metrics=build_metrics_summary(result),
        tables=build_table_specs(result.outputs.tables),
        chart_specs=build_chart_specs(result.outputs.chart_specs),
        recommendations=result.outputs.recommendations,
    )
    _reports[report.report_id] = report

    return result


@router.get("/reports/{report_id}", response_model=ReportArtifact)
async def get_report(report_id: str) -> ReportArtifact:
    """Get a generated report by ID."""
    report = _reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.get("/plans", response_model=list[PlanSummary])
async def list_plans(owner_id: str = "anonymous") -> list[PlanSummary]:
    """List all plans for an owner."""
    from backend.api.deps import list_plans as _list_plans

    plans = _list_plans(owner_id)
    return [
        PlanSummary(
            plan_id=p.plan_id,
            owner_id=p.owner_id,
            status=p.status,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )
        for p in plans
    ]


@router.get("/plans/{plan_id}")
async def get_plan_detail(plan_id: str) -> dict[str, Any]:
    """Get full plan details."""
    schema = get_plan(plan_id)
    if schema is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    return schema.model_dump(mode="json")
