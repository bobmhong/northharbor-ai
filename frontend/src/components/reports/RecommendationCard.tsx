import type { Recommendation } from "../../types/api";

interface RecommendationCardProps {
  recommendations: Recommendation[];
}

export default function RecommendationCard({
  recommendations,
}: RecommendationCardProps) {
  if (recommendations.length === 0) return null;

  return (
    <div className="card">
      <div className="flex items-center gap-2 mb-5">
        <div className="rounded-lg bg-amber-100 p-2">
          <svg className="h-5 w-5 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
          </svg>
        </div>
        <h3 className="section-title">Recommendations</h3>
      </div>
      <ul className="space-y-4">
        {recommendations.map((rec, i) => (
          <li key={i} className="flex gap-3 rounded-xl bg-sage-50/50 p-3 transition-colors hover:bg-sage-100/50">
            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-harbor-400 to-harbor-500 text-xs font-semibold text-white shadow-soft">
              {i + 1}
            </span>
            <div className="pt-0.5">
              <p className="text-sm text-harbor-800 leading-relaxed">{rec.message}</p>
              <p className="mt-1.5 text-xs text-sage-500 font-mono">{rec.rule_id}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
