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
      <h3 className="mb-4 text-base font-semibold text-gray-900">
        Recommendations
      </h3>
      <ul className="space-y-3">
        {recommendations.map((rec, i) => (
          <li key={i} className="flex gap-3">
            <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-harbor-100 text-xs font-medium text-harbor-700">
              {i + 1}
            </span>
            <div>
              <p className="text-sm text-gray-900">{rec.message}</p>
              <p className="mt-0.5 text-xs text-gray-400">{rec.rule_id}</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
