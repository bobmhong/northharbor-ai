import { Link, useNavigate } from "react-router-dom";
import { usePlans } from "../api/hooks";
import { formatDate } from "../lib/utils";

const STATUS_BADGES: Record<string, string> = {
  intake_in_progress: "bg-yellow-100 text-yellow-800",
  intake_complete: "bg-blue-100 text-blue-800",
  analysis_ready: "bg-green-100 text-green-800",
  review: "bg-purple-100 text-purple-800",
  finalized: "bg-gray-100 text-gray-800",
};

export default function PlanListPage() {
  const navigate = useNavigate();
  const { data: plans, isLoading, isError } = usePlans();

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Your Plans</h1>
          <p className="mt-1 text-sm text-gray-500">
            View existing plans or start a new interview.
          </p>
        </div>
        <button
          className="btn-primary"
          onClick={() => navigate("/interview")}
        >
          New Plan
        </button>
      </div>

      {isLoading && <p className="text-gray-500">Loading plans...</p>}

      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          Failed to load plans.
        </div>
      )}

      {plans && plans.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-xl border-2 border-dashed border-gray-300 py-16">
          <p className="mb-4 text-gray-500">
            No plans yet. Start your first interview to create one.
          </p>
          <button
            className="btn-primary"
            onClick={() => navigate("/interview")}
          >
            Start Interview
          </button>
        </div>
      )}

      {plans && plans.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {plans.map((plan) => (
            <Link
              key={plan.plan_id}
              to={`/dashboard/${plan.plan_id}`}
              className="card transition-shadow hover:shadow-md"
            >
              <div className="flex items-start justify-between">
                <h3 className="font-medium text-gray-900">
                  {plan.plan_id.slice(0, 8)}...
                </h3>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    STATUS_BADGES[plan.status] ?? "bg-gray-100 text-gray-800"
                  }`}
                >
                  {plan.status.replace(/_/g, " ")}
                </span>
              </div>
              <p className="mt-2 text-sm text-gray-500">
                Created {formatDate(plan.created_at)}
              </p>
              <p className="text-sm text-gray-500">
                Updated {formatDate(plan.updated_at)}
              </p>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
