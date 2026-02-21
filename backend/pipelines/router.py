"""FastAPI pipeline and report endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.api.deps import delete_plan as delete_plan_store, get_plan, get_snapshot_store, list_plans as list_owner_plans, store_plan
from backend.schema.canonical import CanonicalPlanSchema
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
    display_name: str
    client_name: str
    scenario_name: str
    owner_id: str
    status: str
    created_at: str
    updated_at: str


class CopyPlanRequest(BaseModel):
    owner_id: str = "anonymous"
    scenario_name: str | None = None


def _plan_client_name(plan: CanonicalPlanSchema) -> str:
    value = plan.client.name.value
    if isinstance(value, str) and value.strip():
        return value.strip()
    return "Client"


def _plan_display_name(plan: CanonicalPlanSchema) -> str:
    return f"{_plan_client_name(plan)} - {plan.scenario_name}"


def _next_copy_scenario_name(owner_id: str, client_name: str) -> str:
    existing_names = {
        p.scenario_name
        for p in list_owner_plans(owner_id)
        if _plan_client_name(p) == client_name
    }
    if "Scenario Copy" not in existing_names:
        return "Scenario Copy"
    n = 2
    while f"Scenario Copy {n}" in existing_names:
        n += 1
    return f"Scenario Copy {n}"


def _ensure_distinct_scenario_name(
    owner_id: str, client_name: str, desired_name: str
) -> str:
    base = desired_name.strip() or "Scenario"
    existing_names = {
        p.scenario_name
        for p in list_owner_plans(owner_id)
        if _plan_client_name(p) == client_name
    }
    if base not in existing_names:
        return base
    n = 2
    while f"{base} ({n})" in existing_names:
        n += 1
    return f"{base} ({n})"


def _to_summary(plan: CanonicalPlanSchema) -> PlanSummary:
    return PlanSummary(
        plan_id=plan.plan_id,
        display_name=_plan_display_name(plan),
        client_name=_plan_client_name(plan),
        scenario_name=plan.scenario_name,
        owner_id=plan.owner_id,
        status=plan.status,
        created_at=plan.created_at.isoformat(),
        updated_at=plan.updated_at.isoformat(),
    )


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
    return [_to_summary(p) for p in list_owner_plans(owner_id)]


@router.get("/plans/{plan_id}")
async def get_plan_detail(plan_id: str) -> dict[str, Any]:
    """Get full plan details."""
    schema = get_plan(plan_id)
    if schema is None:
        raise HTTPException(status_code=404, detail="Plan not found")
    payload = schema.model_dump(mode="json")
    payload["display_name"] = _plan_display_name(schema)
    payload["client_name"] = _plan_client_name(schema)
    return payload


class DeletePlanRequest(BaseModel):
    owner_id: str = "anonymous"


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: str, req: DeletePlanRequest) -> dict[str, bool]:
    """Delete a plan by ID."""
    plan = get_plan(plan_id)
    if plan is None or plan.owner_id != req.owner_id:
        raise HTTPException(status_code=404, detail="Plan not found")
    deleted = delete_plan_store(plan_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"deleted": True}


@router.post("/plans/{plan_id}/copy", response_model=PlanSummary)
async def copy_plan(plan_id: str, req: CopyPlanRequest) -> PlanSummary:
    """Create a new scenario by copying an existing plan."""
    source = get_plan(plan_id)
    if source is None or source.owner_id != req.owner_id:
        raise HTTPException(status_code=404, detail="Plan not found")

    client_name = _plan_client_name(source)
    scenario_name = (
        req.scenario_name.strip()
        if isinstance(req.scenario_name, str) and req.scenario_name.strip()
        else _next_copy_scenario_name(req.owner_id, client_name)
    )
    scenario_name = _ensure_distinct_scenario_name(
        req.owner_id, client_name, scenario_name
    )

    now = datetime.now(timezone.utc)
    copied = source.model_copy(deep=True)
    copied.plan_id = str(uuid.uuid4())
    copied.base_plan_id = source.plan_id
    copied.scenario_name = scenario_name
    copied.created_at = now
    copied.updated_at = now

    store_plan(copied)
    return _to_summary(copied)
