import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { frameworksApi } from "@/lib/api/frameworks";
import type {
  ComplianceFramework,
  FrameworkListParams,
  CreateFrameworkRequest,
} from "@/lib/types/api";

// Query keys
export const frameworkKeys = {
  all: ["frameworks"] as const,
  lists: () => [...frameworkKeys.all, "list"] as const,
  list: (params: FrameworkListParams) =>
    [...frameworkKeys.lists(), params] as const,
  details: () => [...frameworkKeys.all, "detail"] as const,
  detail: (id: string) => [...frameworkKeys.details(), id] as const,
  stats: () => [...frameworkKeys.all, "stats"] as const,
};

// Fetch frameworks list
export function useFrameworks(params: FrameworkListParams = {}) {
  return useQuery({
    queryKey: frameworkKeys.list(params),
    queryFn: () => frameworksApi.list(params),
    staleTime: 60000, // 1 minute
  });
}

// Fetch single framework
export function useFramework(id: string) {
  return useQuery({
    queryKey: frameworkKeys.detail(id),
    queryFn: () => frameworksApi.get(id),
    enabled: !!id,
  });
}

// Fetch framework stats
export function useFrameworkStats() {
  return useQuery({
    queryKey: frameworkKeys.stats(),
    queryFn: () => frameworksApi.stats(),
    staleTime: 60000, // 1 minute
  });
}

// Create framework mutation
export function useCreateFramework() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateFrameworkRequest) => frameworksApi.create(data),
    onSuccess: () => {
      // Invalidate frameworks list and stats
      queryClient.invalidateQueries({ queryKey: frameworkKeys.lists() });
      queryClient.invalidateQueries({ queryKey: frameworkKeys.stats() });
    },
  });
}

// Update framework mutation
export function useUpdateFramework() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      updates,
    }: {
      id: string;
      updates: Partial<ComplianceFramework>;
    }) => frameworksApi.update(id, updates),
    onSuccess: (_, variables) => {
      // Invalidate the specific framework and lists
      queryClient.invalidateQueries({
        queryKey: frameworkKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: frameworkKeys.lists() });
    },
  });
}

// Update framework todos mutation
export function useUpdateFrameworkTodos() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, todos }: { id: string; todos: string[] }) =>
      frameworksApi.updateTodos(id, todos),
    onSuccess: (_, variables) => {
      // Invalidate the specific framework
      queryClient.invalidateQueries({
        queryKey: frameworkKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: frameworkKeys.lists() });
    },
  });
}

// Delete framework mutation
export function useDeleteFramework() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => frameworksApi.delete(id),
    onSuccess: () => {
      // Invalidate all framework queries
      queryClient.invalidateQueries({ queryKey: frameworkKeys.all });
    },
  });
}
