import type {
  LLMAnalyticsResponse,
  PipelineResult,
  PlanSummary,
  ReportArtifact,
  RespondResponse,
  StartInterviewResponse,
} from "../types/api";

const BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  startInterview(params?: { ownerId?: string; planId?: string }) {
    const ownerId = params?.ownerId ?? "anonymous";
    return request<StartInterviewResponse>("/interview/start", {
      method: "POST",
      body: JSON.stringify({
        owner_id: ownerId,
        plan_id: params?.planId ?? null,
      }),
    });
  },

  respond(sessionId: string, message: string) {
    return request<RespondResponse>("/interview/respond", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message }),
    });
  },

  runPipeline(planId: string, ownerId = "anonymous", seed = 42) {
    return request<PipelineResult>("/pipelines/run", {
      method: "POST",
      body: JSON.stringify({ plan_id: planId, owner_id: ownerId, seed }),
    });
  },

  getReport(reportId: string) {
    return request<ReportArtifact>(`/reports/${reportId}`);
  },

  listPlans(ownerId = "anonymous") {
    return request<PlanSummary[]>(`/plans?owner_id=${ownerId}`);
  },

  getPlan(planId: string) {
    return request<Record<string, unknown>>(`/plans/${planId}`);
  },

  copyPlan(planId: string, scenarioName?: string, ownerId = "anonymous") {
    return request<PlanSummary>(`/plans/${planId}/copy`, {
      method: "POST",
      body: JSON.stringify({
        owner_id: ownerId,
        scenario_name: scenarioName ?? null,
      }),
    });
  },

  deletePlan(planId: string, ownerId = "anonymous") {
    return request<{ deleted: boolean }>(`/plans/${planId}`, {
      method: "DELETE",
      body: JSON.stringify({ owner_id: ownerId }),
    });
  },

  updatePlanFields(planId: string, updates: { path: string; value: unknown }[], ownerId = "anonymous") {
    return request<Record<string, unknown>>(`/plans/${planId}/fields`, {
      method: "PATCH",
      body: JSON.stringify({ owner_id: ownerId, updates }),
    });
  },

  updateScenarioName(planId: string, scenarioName: string, ownerId = "anonymous") {
    return request<PlanSummary>(`/plans/${planId}/scenario-name`, {
      method: "PATCH",
      body: JSON.stringify({ owner_id: ownerId, scenario_name: scenarioName }),
    });
  },

  getLLMAnalytics() {
    return request<LLMAnalyticsResponse>("/admin/analytics/llm");
  },
};
