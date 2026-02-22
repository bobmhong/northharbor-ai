import { useLLMAnalytics } from "../api/hooks";
import type { PeriodMetrics, RecentCall } from "../types/api";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function formatNumber(num: number): string {
  return num.toLocaleString();
}

function formatTimestamp(ts: string): string {
  const date = new Date(ts);
  return date.toLocaleString();
}

function MetricsCard({ metrics, title }: { metrics: PeriodMetrics; title: string }) {
  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-harbor-800 mb-4">{title}</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <p className="text-sm text-sage-600">Total Requests</p>
          <p className="text-2xl font-bold text-harbor-900">{formatNumber(metrics.total_requests)}</p>
        </div>
        <div>
          <p className="text-sm text-sage-600">Est. Tokens</p>
          <p className="text-2xl font-bold text-harbor-900">{formatNumber(metrics.total_tokens)}</p>
        </div>
        <div>
          <p className="text-sm text-sage-600">Request Data</p>
          <p className="text-lg font-semibold text-harbor-700">{formatBytes(metrics.total_request_bytes)}</p>
        </div>
        <div>
          <p className="text-sm text-sage-600">Response Data</p>
          <p className="text-lg font-semibold text-harbor-700">{formatBytes(metrics.total_response_bytes)}</p>
        </div>
      </div>
      {metrics.models_used.length > 0 && (
        <div className="mt-4 pt-4 border-t border-sage-200">
          <p className="text-sm text-sage-600 mb-2">Models Used</p>
          <div className="flex flex-wrap gap-2">
            {metrics.models_used.map((m) => (
              <span
                key={m.model}
                className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-sage-100 text-sm text-sage-700"
              >
                <span className="font-medium">{m.model}</span>
                <span className="text-sage-500">({m.count})</span>
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function RecentCallsTable({ calls }: { calls: RecentCall[] }) {
  if (calls.length === 0) {
    return (
      <div className="card">
        <h3 className="text-lg font-semibold text-harbor-800 mb-4">Recent Calls</h3>
        <p className="text-sage-500 text-center py-8">No LLM calls recorded yet.</p>
      </div>
    );
  }

  return (
    <div className="card overflow-hidden">
      <h3 className="text-lg font-semibold text-harbor-800 mb-4">Recent Calls</h3>
      <div className="overflow-x-auto -mx-5 sm:-mx-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-sage-200 bg-sage-50">
              <th className="px-4 py-3 text-left font-medium text-sage-700">Timestamp</th>
              <th className="px-4 py-3 text-left font-medium text-sage-700">Model</th>
              <th className="px-4 py-3 text-right font-medium text-sage-700">Request</th>
              <th className="px-4 py-3 text-right font-medium text-sage-700">Response</th>
              <th className="px-4 py-3 text-right font-medium text-sage-700">Est. Tokens</th>
            </tr>
          </thead>
          <tbody>
            {calls.map((call, i) => (
              <tr
                key={`${call.timestamp}-${i}`}
                className="border-b border-sage-100 hover:bg-sage-50/50 transition-colors"
              >
                <td className="px-4 py-3 text-sage-600">{formatTimestamp(call.timestamp)}</td>
                <td className="px-4 py-3">
                  <span className="inline-flex px-2 py-0.5 rounded bg-harbor-100 text-harbor-700 font-medium">
                    {call.model}
                  </span>
                </td>
                <td className="px-4 py-3 text-right text-sage-600">{formatBytes(call.request_bytes)}</td>
                <td className="px-4 py-3 text-right text-sage-600">{formatBytes(call.response_bytes)}</td>
                <td className="px-4 py-3 text-right font-medium text-harbor-700">
                  {formatNumber(call.estimated_tokens)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function AdminAnalyticsPage() {
  const { data, isLoading, isError, error } = useLLMAnalytics();

  return (
    <div>
      <div className="mb-6 sm:mb-8">
        <h1 className="page-title">LLM Analytics</h1>
        <p className="text-sage-600 mt-1">Monitor AI usage metrics for NorthHarbor Sage.</p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <div className="flex items-center gap-3 text-sage-500">
            <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>Loading analytics...</span>
          </div>
        </div>
      )}

      {isError && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 shadow-soft">
          <p className="font-medium text-red-700">Failed to load analytics</p>
          <p className="mt-1 text-sm text-red-600/80">{error?.message}</p>
        </div>
      )}

      {data && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <MetricsCard metrics={data.today} title="Today" />
            <MetricsCard metrics={data.last_7_days} title="Last 7 Days" />
            <MetricsCard metrics={data.last_30_days} title="Last 30 Days" />
          </div>

          <RecentCallsTable calls={data.recent_calls} />
        </>
      )}
    </div>
  );
}
