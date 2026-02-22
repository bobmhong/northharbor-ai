import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";

export function usePlans(ownerId = "anonymous") {
  return useQuery({
    queryKey: ["plans", ownerId],
    queryFn: () => api.listPlans(ownerId),
  });
}

export function usePlan(planId: string | undefined) {
  return useQuery({
    queryKey: ["plan", planId],
    queryFn: () => api.getPlan(planId!),
    enabled: !!planId,
  });
}

export function useReport(reportId: string | undefined) {
  return useQuery({
    queryKey: ["report", reportId],
    queryFn: () => api.getReport(reportId!),
    enabled: !!reportId,
  });
}

export function useStartInterview() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (params?: { ownerId?: string; planId?: string }) =>
      api.startInterview(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
    },
  });
}

export function useRespond() {
  return useMutation({
    mutationFn: ({ sessionId, message }: { sessionId: string; message: string }) =>
      api.respond(sessionId, message),
  });
}

export function useRunPipeline() {
  return useMutation({
    mutationFn: ({
      planId,
      ownerId,
      seed,
    }: {
      planId: string;
      ownerId?: string;
      seed?: number;
    }) => api.runPipeline(planId, ownerId, seed),
  });
}

export function useCopyPlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      planId,
      scenarioName,
      ownerId,
    }: {
      planId: string;
      scenarioName?: string;
      ownerId?: string;
    }) => api.copyPlan(planId, scenarioName, ownerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
    },
  });
}

export function useDeletePlan() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      planId,
      ownerId,
    }: {
      planId: string;
      ownerId?: string;
    }) => api.deletePlan(planId, ownerId),
    onSuccess: (_, variables) => {
      // Invalidate and remove all cached data for the deleted plan
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      queryClient.invalidateQueries({ queryKey: ["plan", variables.planId] });
      queryClient.removeQueries({ queryKey: ["plan", variables.planId] });
      // Also invalidate any pipeline results that might reference this plan
      queryClient.invalidateQueries({ queryKey: ["pipeline"] });
    },
  });
}

export function useUpdateScenarioName() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      planId,
      scenarioName,
      ownerId,
    }: {
      planId: string;
      scenarioName: string;
      ownerId?: string;
    }) => api.updateScenarioName(planId, scenarioName, ownerId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      queryClient.invalidateQueries({ queryKey: ["plan", variables.planId] });
    },
  });
}

export function useLLMAnalytics() {
  return useQuery({
    queryKey: ["llm-analytics"],
    queryFn: () => api.getLLMAnalytics(),
    refetchInterval: 30000,
  });
}
