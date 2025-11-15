import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { complianceApi } from "@/lib/api/compliance";
import type { ComplianceCheckRequest } from "@/lib/types/api";

// Query keys
export const complianceKeys = {
  all: ["compliance"] as const,
  jobs: () => [...complianceKeys.all, "jobs"] as const,
  job: (jobId: string) => [...complianceKeys.all, "job", jobId] as const,
  stats: () => [...complianceKeys.all, "stats"] as const,
};

// Fetch compliance jobs list
export function useComplianceJobs() {
  return useQuery({
    queryKey: complianceKeys.jobs(),
    queryFn: () => complianceApi.listJobs(),
    staleTime: 30000, // 30 seconds
    refetchInterval: 5000, // Refetch every 5 seconds for real-time updates
  });
}

// Fetch single job status
export function useComplianceJob(jobId: string, enabled: boolean = true) {
  return useQuery({
    queryKey: complianceKeys.job(jobId),
    queryFn: () => complianceApi.getJobStatus(jobId),
    enabled: enabled && !!jobId,
    refetchInterval: (query) => {
      // Refetch every 2 seconds if job is pending or running
      const status = query.state.data?.status;
      return status === "pending" || status === "running" ? 2000 : false;
    },
  });
}

// Fetch compliance stats
export function useComplianceStats() {
  return useQuery({
    queryKey: complianceKeys.stats(),
    queryFn: () => complianceApi.stats(),
    staleTime: 60000, // 1 minute
  });
}

// Trigger compliance check mutation
export function useComplianceCheck() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ComplianceCheckRequest) => complianceApi.check(data),
    onSuccess: () => {
      // Invalidate jobs list to show the new job
      queryClient.invalidateQueries({ queryKey: complianceKeys.jobs() });
      queryClient.invalidateQueries({ queryKey: complianceKeys.stats() });
    },
  });
}
