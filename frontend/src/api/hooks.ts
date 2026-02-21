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
    mutationFn: (ownerId?: string) => api.startInterview(ownerId),
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
