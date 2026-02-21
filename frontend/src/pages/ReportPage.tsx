import { useParams } from "react-router-dom";
import { usePlan, useReport } from "../api/hooks";
import ChartCard from "../components/charts/ChartCard";
import DataTable from "../components/reports/DataTable";
import RecommendationCard from "../components/reports/RecommendationCard";
import { formatDate } from "../lib/utils";

export default function ReportPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const { data: report, isLoading, isError, error } = useReport(reportId);
  const { data: plan } = usePlan(report?.plan_id);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex items-center gap-3 text-sage-500">
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span>Loading report...</span>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-5 shadow-soft">
        <p className="font-medium text-red-700">Failed to load report</p>
        <p className="mt-1 text-sm text-red-600/80">{error?.message}</p>
      </div>
    );
  }

  if (!report) return null;
  const displayName =
    typeof plan?.display_name === "string" ? plan.display_name : report.plan_id;

  return (
    <div>
      <div className="mb-6 sm:mb-8">
        <h1 className="page-title">Report</h1>
        <p className="page-subtitle">
          Generated {formatDate(report.generated_at)} &middot; Plan: {displayName}
        </p>
      </div>

      {report.ai_analysis && (
        <div className="card-elevated mb-10 border-l-4 border-l-harbor-500">
          <div className="flex items-center gap-2 mb-4">
            <div className="rounded-lg bg-harbor-100 p-2">
              <svg className="h-5 w-5 text-harbor-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <h2 className="section-title">AI Analysis</h2>
          </div>
          <div className="prose prose-sm max-w-none text-harbor-800">
            <p className="leading-relaxed">{report.ai_analysis.interpretation}</p>
          </div>
          {report.ai_analysis.key_tradeoffs.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-harbor-900 mb-3">
                Key Tradeoffs
              </h3>
              <ul className="space-y-2">
                {report.ai_analysis.key_tradeoffs.map((t, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-harbor-700">
                    <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-harbor-400 shrink-0" />
                    {t}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {report.ai_analysis.suggested_next_steps.length > 0 && (
            <div className="mt-6">
              <h3 className="text-sm font-semibold text-harbor-900 mb-3">
                Suggested Next Steps
              </h3>
              <ul className="space-y-2">
                {report.ai_analysis.suggested_next_steps.map((s, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-harbor-700">
                    <span className="mt-1 flex h-5 w-5 items-center justify-center rounded-full bg-harbor-100 text-xs font-medium text-harbor-600 shrink-0">
                      {i + 1}
                    </span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <p className="mt-6 text-xs italic text-sage-500 border-t border-sage-200 pt-4">
            {report.ai_analysis.disclaimer}
          </p>
        </div>
      )}

      {report.chart_specs.length > 0 && (
        <section className="mb-10">
          <h2 className="section-title mb-5">Visualizations</h2>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {report.chart_specs.map((chart) => (
              <ChartCard key={chart.id} spec={chart} />
            ))}
          </div>
        </section>
      )}

      <section className="mb-10">
        <RecommendationCard recommendations={report.recommendations} />
      </section>

      {report.tables.length > 0 && (
        <section className="space-y-6">
          <h2 className="section-title">Data Tables</h2>
          {report.tables.map((table) => (
            <DataTable key={table.id} spec={table} />
          ))}
        </section>
      )}
    </div>
  );
}
