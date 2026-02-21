import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import ChartCard from "../components/charts/ChartCard";
import DataTable from "../components/reports/DataTable";
import RecommendationCard from "../components/reports/RecommendationCard";
import { useRunPipeline } from "../api/hooks";
import { formatCurrency, formatPercent } from "../lib/utils";
import type { PipelineResult } from "../types/api";

export default function DashboardPage() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const runPipeline = useRunPipeline();
  const [result, setResult] = useState<PipelineResult | null>(null);

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

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
          <p className="mt-1 text-sm text-gray-500">
            Plan: {planId?.slice(0, 8)}...
          </p>
        </div>
        <div className="flex gap-3">
          <button className="btn-secondary" onClick={handleRun} disabled={runPipeline.isPending}>
            {runPipeline.isPending ? "Running..." : result ? "Re-run Pipeline" : "Run Pipeline"}
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
        <div className="mb-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Pipeline failed: {runPipeline.error?.message}
        </div>
      )}

      {result && (
        <>
          {/* Key Metrics */}
          <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              label="Recommended Age"
              value={String(metrics.recommended_retirement_age ?? "—")}
            />
            <MetricCard
              label="Success Probability"
              value={
                metrics.recommended_age_success_probability != null
                  ? formatPercent(Number(metrics.recommended_age_success_probability))
                  : "—"
              }
            />
            <MetricCard
              label="Median Terminal Balance"
              value={
                metrics.recommended_age_terminal_p50 != null
                  ? formatCurrency(Number(metrics.recommended_age_terminal_p50))
                  : "—"
              }
            />
            <MetricCard
              label="Pipeline Duration"
              value={`${metrics.total_duration_ms ?? 0}ms`}
            />
          </div>

          {/* Charts */}
          {charts.length > 0 && (
            <div className="mb-8">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">
                Charts
              </h2>
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {charts
                  .filter((c) => c.section === "dashboard")
                  .map((chart) => (
                    <ChartCard key={chart.id} spec={chart} />
                  ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          <div className="mb-8">
            <RecommendationCard recommendations={recommendations} />
          </div>

          {/* Tables */}
          {tables.length > 0 && (
            <div className="mb-8 space-y-6">
              <h2 className="text-lg font-semibold text-gray-900">
                Detailed Tables
              </h2>
              {tables.map((table) => (
                <DataTable key={table.id} spec={table} />
              ))}
            </div>
          )}

          {/* Appendix Charts */}
          {charts.filter((c) => c.section === "appendix").length > 0 && (
            <div className="mb-8">
              <h2 className="mb-4 text-lg font-semibold text-gray-900">
                Appendix Charts
              </h2>
              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                {charts
                  .filter((c) => c.section === "appendix")
                  .map((chart) => (
                    <ChartCard key={chart.id} spec={chart} />
                  ))}
              </div>
            </div>
          )}
        </>
      )}

      {!result && !runPipeline.isPending && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-16">
          <p className="mb-4 text-gray-500">
            Run the pipeline to see your retirement projections.
          </p>
          <button className="btn-primary" onClick={handleRun}>
            Run Pipeline
          </button>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card text-center">
      <p className="text-sm font-medium text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{value}</p>
    </div>
  );
}
