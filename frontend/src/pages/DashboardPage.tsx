import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ChartCard from "../components/charts/ChartCard";
import DataTable from "../components/reports/DataTable";
import RecommendationCard from "../components/reports/RecommendationCard";
import CopyScenarioModal from "../components/ui/CopyScenarioModal";
import { useCopyPlan, usePlan, usePlans, useRunPipeline } from "../api/hooks";
import { formatCurrency, formatPercent } from "../lib/utils";
import type { PipelineResult } from "../types/api";

export default function DashboardPage() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const runPipeline = useRunPipeline();
  const copyPlan = useCopyPlan();
  const { data: plan } = usePlan(planId);
  const { data: allPlans } = usePlans();
  const [result, setResult] = useState<PipelineResult | null>(null);
  const [showCopyModal, setShowCopyModal] = useState(false);

  async function handleRun() {
    if (!planId) return;
    try {
      const res = await runPipeline.mutateAsync({ planId });
      setResult(res);
    } catch {
      // handled by react-query
    }
  }

  const metrics = result?.outputs.metrics ?? {};
  const charts = result?.outputs.chart_specs ?? [];
  const tables = result?.outputs.tables ?? [];
  const recommendations = result?.outputs.recommendations ?? [];
  const displayName = typeof plan?.display_name === "string" ? plan.display_name : planId ?? "Plan";
  const currentScenarioName = typeof plan?.scenario_name === "string" ? plan.scenario_name : "Default";
  
  const existingScenarioNames = (allPlans ?? []).map((p) => p.scenario_name);

  async function handleCopyConfirm(scenarioName: string) {
    if (!planId) return;
    try {
      const copied = await copyPlan.mutateAsync({
        planId,
        scenarioName: scenarioName || undefined,
      });
      setShowCopyModal(false);
      navigate(`/dashboard/${copied.plan_id}`);
    } catch {
      // handled by error banner
    }
  }

  return (
    <>
      <CopyScenarioModal
        isOpen={showCopyModal}
        onClose={() => setShowCopyModal(false)}
        onConfirm={handleCopyConfirm}
        existingNames={existingScenarioNames}
        defaultName={`${currentScenarioName} (Copy)`}
        isPending={copyPlan.isPending}
      />
      <div>
      <div className="mb-6 sm:mb-8 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">{displayName}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            className="btn-ghost"
            onClick={() => navigate(`/interview?plan_id=${planId}`)}
            disabled={!planId}
          >
            Update Responses
          </button>
          <button
            className="btn-ghost"
            onClick={() => setShowCopyModal(true)}
            disabled={!planId}
          >
            Copy Scenario
          </button>
          <button className="btn-secondary" onClick={handleRun} disabled={runPipeline.isPending}>
            {runPipeline.isPending ? (
              <span className="flex items-center gap-2">
                <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Running...
              </span>
            ) : result ? "Re-run Pipeline" : "Run Pipeline"}
          </button>
          {result && (
            <button
              className="btn-primary"
              onClick={() => navigate(`/report/${result.pipeline_id}`)}
            >
              View Report
            </button>
          )}
        </div>
      </div>

      {runPipeline.isError && (
        <div className="mb-8 rounded-2xl border border-red-200 bg-red-50 p-5 shadow-soft">
          <p className="font-medium text-red-700">Pipeline failed</p>
          <p className="mt-1 text-sm text-red-600/80">{runPipeline.error?.message}</p>
        </div>
      )}
      {copyPlan.isError && (
        <div className="mb-8 rounded-2xl border border-red-200 bg-red-50 p-5 shadow-soft">
          <p className="font-medium text-red-700">Copy failed</p>
          <p className="mt-1 text-sm text-red-600/80">{copyPlan.error?.message}</p>
        </div>
      )}

      {result && (
        <>
          <div className="mb-10 grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Recommended Age"
              value={String(metrics.recommended_retirement_age ?? "—")}
              accent="harbor"
            />
            <MetricCard
              label="Success Probability"
              value={
                metrics.recommended_age_success_probability != null
                  ? formatPercent(Number(metrics.recommended_age_success_probability))
                  : "—"
              }
              accent="emerald"
            />
            <MetricCard
              label="Median Terminal Balance"
              value={
                metrics.recommended_age_terminal_p50 != null
                  ? formatCurrency(Number(metrics.recommended_age_terminal_p50))
                  : "—"
              }
              accent="amber"
            />
            <MetricCard
              label="Pipeline Duration"
              value={`${metrics.total_duration_ms ?? 0}ms`}
              accent="sage"
            />
          </div>

          {charts.length > 0 && (
            <section className="mb-10">
              <h2 className="section-title mb-5">Charts</h2>
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {charts
                  .filter((c) => c.section === "dashboard")
                  .map((chart) => (
                    <ChartCard key={chart.id} spec={chart} />
                  ))}
              </div>
            </section>
          )}

          <section className="mb-10">
            <RecommendationCard recommendations={recommendations} />
          </section>

          {tables.length > 0 && (
            <section className="mb-10 space-y-6">
              <h2 className="section-title">Detailed Tables</h2>
              {tables.map((table) => (
                <DataTable key={table.id} spec={table} />
              ))}
            </section>
          )}

          {charts.filter((c) => c.section === "appendix").length > 0 && (
            <section className="mb-10">
              <h2 className="section-title mb-5">Appendix Charts</h2>
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {charts
                  .filter((c) => c.section === "appendix")
                  .map((chart) => (
                    <ChartCard key={chart.id} spec={chart} />
                  ))}
              </div>
            </section>
          )}
        </>
      )}

      {!result && !runPipeline.isPending && (
        <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-sage-300 bg-white/50 py-20">
          <div className="mb-4 rounded-full bg-sage-100 p-4">
            <svg className="h-8 w-8 text-sage-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
          </div>
          <p className="mb-6 text-sage-600">
            Run the pipeline to see your retirement projections.
          </p>
          <button className="btn-primary" onClick={handleRun}>
            Run Pipeline
          </button>
        </div>
      )}
    </div>
    </>
  );
}

const ACCENT_STYLES = {
  harbor: "border-l-harbor-500 bg-gradient-to-br from-harbor-50/50 to-white",
  emerald: "border-l-emerald-500 bg-gradient-to-br from-emerald-50/50 to-white",
  amber: "border-l-amber-500 bg-gradient-to-br from-amber-50/50 to-white",
  sage: "border-l-sage-400 bg-gradient-to-br from-sage-50/50 to-white",
};

function MetricCard({ label, value, accent = "harbor" }: { label: string; value: string; accent?: keyof typeof ACCENT_STYLES }) {
  return (
    <div className={`card border-l-4 text-center ${ACCENT_STYLES[accent]}`}>
      <p className="text-sm font-medium text-sage-600">{label}</p>
      <p className="mt-2 text-2xl font-bold tracking-tight text-harbor-900">{value}</p>
    </div>
  );
}
