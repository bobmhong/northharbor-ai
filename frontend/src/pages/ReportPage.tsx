import { useParams } from "react-router-dom";
import { useReport } from "../api/hooks";
import ChartCard from "../components/charts/ChartCard";
import DataTable from "../components/reports/DataTable";
import RecommendationCard from "../components/reports/RecommendationCard";
import { formatDate } from "../lib/utils";

export default function ReportPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const { data: report, isLoading, isError, error } = useReport(reportId);

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <p className="text-gray-500">Loading report...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
        Failed to load report: {error?.message}
      </div>
    );
  }

  if (!report) return null;

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Report</h1>
        <p className="mt-1 text-sm text-gray-500">
          Generated {formatDate(report.generated_at)} &middot; Plan:{" "}
          {report.plan_id.slice(0, 8)}...
        </p>
      </div>

      {/* AI Analysis */}
      {report.ai_analysis && (
        <div className="card mb-8">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">
            AI Analysis
          </h2>
          <div className="prose prose-sm max-w-none text-gray-700">
            <p>{report.ai_analysis.interpretation}</p>
          </div>
          {report.ai_analysis.key_tradeoffs.length > 0 && (
            <>
              <h3 className="mt-4 text-sm font-semibold text-gray-900">
                Key Tradeoffs
              </h3>
              <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-gray-700">
                {report.ai_analysis.key_tradeoffs.map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </>
          )}
          {report.ai_analysis.suggested_next_steps.length > 0 && (
            <>
              <h3 className="mt-4 text-sm font-semibold text-gray-900">
                Suggested Next Steps
              </h3>
              <ul className="mt-2 list-inside list-disc space-y-1 text-sm text-gray-700">
                {report.ai_analysis.suggested_next_steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </>
          )}
          <p className="mt-4 text-xs italic text-gray-400">
            {report.ai_analysis.disclaimer}
          </p>
        </div>
      )}

      {/* Charts */}
      {report.chart_specs.length > 0 && (
        <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {report.chart_specs.map((chart) => (
            <ChartCard key={chart.id} spec={chart} />
          ))}
        </div>
      )}

      {/* Recommendations */}
      <div className="mb-8">
        <RecommendationCard recommendations={report.recommendations} />
      </div>

      {/* Tables */}
      {report.tables.length > 0 && (
        <div className="space-y-6">
          {report.tables.map((table) => (
            <DataTable key={table.id} spec={table} />
          ))}
        </div>
      )}
    </div>
  );
}
