import { useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { usePlan } from "../api/hooks";
import { api } from "../api/client";
import ReviewFieldGroup from "../components/review/ReviewFieldGroup";
import { REVIEW_FIELDS } from "../components/review/fieldConfig";

export default function QuickReviewPage() {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: plan, isLoading, isError } = usePlan(planId);

  const planData = plan as Record<string, unknown> | undefined;
  const clientObj = planData?.client as Record<string, unknown> | undefined;
  const nameField = clientObj?.name as Record<string, unknown> | undefined;
  const clientName = typeof nameField?.value === "string" ? nameField.value : "Your Plan";

  const handleSave = useCallback(
    async (path: string, value: unknown) => {
      if (!planId) return;
      await api.updatePlanFields(planId, [{ path, value }]);
      queryClient.invalidateQueries({ queryKey: ["plan", planId] });
      queryClient.invalidateQueries({ queryKey: ["plans"] });
    },
    [planId, queryClient],
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="flex items-center gap-3 text-sage-500">
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <span>Loading plan...</span>
        </div>
      </div>
    );
  }

  if (isError || !planData) {
    return (
      <div className="rounded-2xl border border-red-200 bg-red-50 p-5 text-sm text-red-700 shadow-soft">
        <p className="font-medium">Failed to load plan</p>
        <p className="mt-1 text-red-600/80">Please try refreshing the page.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="page-title">Review Responses</h1>
          <p className="text-sm text-sage-600 mt-1">
            {clientName} &mdash; click any value to edit
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            className="btn-ghost flex items-center gap-2"
            onClick={() => navigate(`/interview?plan_id=${planId}`)}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            Back to Interview
          </button>
          <button
            className="btn-primary flex items-center gap-2"
            onClick={() => navigate(`/dashboard/${planId}?autorun=true`)}
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Run Analysis
          </button>
        </div>
      </div>

      <div className="space-y-4">
        {REVIEW_FIELDS.map((group) => (
          <ReviewFieldGroup
            key={group.group}
            title={group.group}
            fields={group.fields}
            planData={planData}
            onSave={handleSave}
          />
        ))}
      </div>
    </div>
  );
}
