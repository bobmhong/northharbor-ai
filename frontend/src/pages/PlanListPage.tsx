import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCopyPlan, useDeletePlan, usePlans } from "../api/hooks";
import { formatDate } from "../lib/utils";
import ConfirmModal from "../components/ui/ConfirmModal";
import CopyScenarioModal from "../components/ui/CopyScenarioModal";
import { useInterviewStore } from "../stores/interviewStore";

const STATUS_BADGES: Record<string, string> = {
  intake_in_progress: "badge-warning",
  intake_complete: "badge-info",
  analysis_ready: "badge-success",
  review: "bg-purple-50 text-purple-700 ring-1 ring-purple-200",
  finalized: "badge-neutral",
};

interface PlanToDelete {
  planId: string;
  displayName: string;
}

interface PlanToCopy {
  planId: string;
  scenarioName: string;
}

export default function PlanListPage() {
  const navigate = useNavigate();
  const copyPlan = useCopyPlan();
  const deletePlan = useDeletePlan();
  const { data: plans, isLoading, isError } = usePlans();
  const [planToDelete, setPlanToDelete] = useState<PlanToDelete | null>(null);
  const [planToCopy, setPlanToCopy] = useState<PlanToCopy | null>(null);
  
  // Get interview store to check if deleted plan is the active interview
  const { planId: activeInterviewPlanId, reset: resetInterview } = useInterviewStore();

  const existingScenarioNames = (plans ?? []).map((p) => p.scenario_name);

  async function handleCopyConfirm(scenarioName: string) {
    if (!planToCopy) return;
    try {
      const copied = await copyPlan.mutateAsync({
        planId: planToCopy.planId,
        scenarioName: scenarioName || undefined,
      });
      setPlanToCopy(null);
      navigate(`/dashboard/${copied.plan_id}`);
    } catch {
      // handled by react-query state in UI below
    }
  }

  async function handleDeleteConfirm() {
    if (!planToDelete) return;
    try {
      await deletePlan.mutateAsync({ planId: planToDelete.planId });
      
      // If the deleted plan was the active interview, reset the interview store
      if (activeInterviewPlanId === planToDelete.planId) {
        resetInterview();
      }
      
      setPlanToDelete(null);
    } catch {
      // Error is shown via deletePlan.isError
    }
  }

  return (
    <div>
      {plans && plans.length > 0 && (
        <div className="mb-6 sm:mb-8 flex justify-end">
          <button
            className="btn-primary"
            onClick={() => navigate("/interview")}
          >
            New Plan
          </button>
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-16">
          <div className="flex items-center gap-3 text-sage-500">
            <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span>Loading plans...</span>
          </div>
        </div>
      )}

      {isError && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 shadow-soft">
          <p className="font-medium">Failed to load plans</p>
          <p className="mt-1 text-red-600/80">Please try refreshing the page.</p>
        </div>
      )}
      {copyPlan.isError && (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 shadow-soft">
          <p className="font-medium">Failed to copy plan</p>
          <p className="mt-1 text-red-600/80">{copyPlan.error?.message}</p>
        </div>
      )}
      {deletePlan.isError && (
        <div className="mb-6 rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 shadow-soft">
          <p className="font-medium">Failed to delete plan</p>
          <p className="mt-1 text-red-600/80">{deletePlan.error?.message}</p>
        </div>
      )}

      {plans && plans.length === 0 && (
        <div className="flex flex-col items-center justify-center rounded-2xl bg-gradient-to-br from-harbor-50 to-sage-50 border border-sage-200 py-16 px-8 text-center shadow-soft">
          <div className="mb-6 rounded-full bg-white p-5 shadow-card">
            <svg className="h-12 w-12 text-harbor-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-semibold text-harbor-900 mb-2">
            Welcome to NorthHarbor Sage
          </h2>
          <p className="text-sage-600 mb-2 max-w-md">
            Let's create your personalized retirement plan. Our AI assistant will guide you through a simple conversation to understand your goals and situation.
          </p>
          <p className="text-sm text-sage-500 mb-8">
            It only takes about 5-10 minutes to get started.
          </p>
          <button
            className="btn-primary text-base px-8 py-3"
            onClick={() => navigate("/interview")}
          >
            Create Your First Plan
          </button>
        </div>
      )}

      {plans && plans.length > 0 && (
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {plans.map((plan) => {
            const isInProgress = plan.status === "intake_in_progress";
            const targetPath = isInProgress
              ? `/interview?plan_id=${plan.plan_id}`
              : `/dashboard/${plan.plan_id}`;
            
            return (
              <Link
                key={plan.plan_id}
                to={targetPath}
                className="card-hover group"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <svg className="h-4 w-4 text-sage-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                      </svg>
                      <h3 className="truncate font-semibold text-harbor-900 group-hover:text-harbor-700">
                        {plan.client_name}
                      </h3>
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <svg className="h-4 w-4 text-sage-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <p className="text-sm text-sage-600">
                        {plan.scenario_name}
                      </p>
                    </div>
                  </div>
                  <span
                    className={`badge shrink-0 ${
                      STATUS_BADGES[plan.status] ?? "badge-neutral"
                    }`}
                  >
                    {plan.status.replace(/_/g, " ")}
                  </span>
                </div>
                
                {isInProgress && (
                  <div className="mt-3 flex items-center gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-xs text-amber-700">
                    <svg className="h-4 w-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Interview in progress — click to continue</span>
                  </div>
                )}
                
                <div className="mt-4 space-y-1 text-sm text-sage-500">
                  <p>Created {formatDate(plan.created_at)}</p>
                  <p>Updated {formatDate(plan.updated_at)}</p>
                </div>
                <div className="mt-4 flex gap-2">
                  <button
                    type="button"
                    className="flex-1 rounded-lg border border-sage-200 bg-sage-50/50 px-3 py-2 text-xs font-medium text-harbor-600 transition-colors hover:bg-sage-100 hover:border-sage-300"
                    onClick={(e) => {
                      e.preventDefault();
                      setPlanToCopy({ planId: plan.plan_id, scenarioName: plan.scenario_name });
                    }}
                  >
                    Copy
                  </button>
                  <button
                    type="button"
                    className="rounded-lg border border-red-200 bg-red-50/50 px-3 py-2 text-xs font-medium text-red-600 transition-colors hover:bg-red-100 hover:border-red-300"
                    aria-label={`Delete ${plan.display_name}`}
                    title={`Delete ${plan.display_name}`}
                    onClick={(e) => {
                      e.preventDefault();
                      setPlanToDelete({ planId: plan.plan_id, displayName: plan.display_name });
                    }}
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </Link>
            );
          })}
        </div>
      )}

      <ConfirmModal
        isOpen={planToDelete !== null}
        title="Delete Plan"
        message={`Are you sure you want to delete "${planToDelete?.displayName}"? This action cannot be undone and will remove all associated data.`}
        confirmLabel="Delete Plan"
        cancelLabel="Cancel"
        variant="danger"
        isLoading={deletePlan.isPending}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setPlanToDelete(null)}
      />

      <CopyScenarioModal
        isOpen={planToCopy !== null}
        onClose={() => setPlanToCopy(null)}
        onConfirm={handleCopyConfirm}
        existingNames={existingScenarioNames}
        defaultName={planToCopy ? `${planToCopy.scenarioName} (Copy)` : ""}
        isPending={copyPlan.isPending}
      />
    </div>
  );
}
