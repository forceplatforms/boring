import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { violationsApi } from "@/lib/api/violations";
import type {
  Violation,
  ViolationListParams,
  ViolationStats,
} from "@/lib/types/api";

// Query keys
export const violationKeys = {
  all: ["violations"] as const,
  lists: () => [...violationKeys.all, "list"] as const,
  list: (params: ViolationListParams) =>
    [...violationKeys.lists(), params] as const,
  details: () => [...violationKeys.all, "detail"] as const,
  detail: (id: string) => [...violationKeys.details(), id] as const,
  stats: () => [...violationKeys.all, "stats"] as const,
};

// Fetch violations list
export function useViolations(params: ViolationListParams = {}) {
  return useQuery({
    queryKey: violationKeys.list(params),
    queryFn: () => violationsApi.list(params),
    staleTime: 30000, // 30 seconds
  });
}

// Fetch single violation
export function useViolation(id: string) {
  return useQuery({
    queryKey: violationKeys.detail(id),
    queryFn: () => violationsApi.get(id),
    enabled: !!id,
  });
}

// Fetch violation stats
export function useViolationStats() {
  return useQuery({
    queryKey: violationKeys.stats(),
    queryFn: () => violationsApi.stats(),
    staleTime: 60000, // 1 minute
  });
}

// Update violation mutation
export function useUpdateViolation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      updates,
    }: {
      id: string;
      updates: Partial<Violation>;
    }) => violationsApi.update(id, updates),
    onSuccess: (_, variables) => {
      // Invalidate the specific violation and lists
      queryClient.invalidateQueries({
        queryKey: violationKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: violationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: violationKeys.stats() });
    },
  });
}

// Acknowledge violation mutation
export function useAcknowledgeViolation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => violationsApi.acknowledge(id),
    onSuccess: (_, id) => {
      // Invalidate the specific violation and lists
      queryClient.invalidateQueries({ queryKey: violationKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: violationKeys.lists() });
      queryClient.invalidateQueries({ queryKey: violationKeys.stats() });
    },
  });
}
