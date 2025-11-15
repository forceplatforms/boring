import apiClient from "./client";
import type {
  ComplianceCheckRequest,
  ComplianceCheckResponse,
  ScanJob,
  PaginatedResponse,
  UUID,
} from "@/lib/types/api";

export const complianceApi = {
  // Trigger a compliance check
  check: async (
    request: ComplianceCheckRequest
  ): Promise<ComplianceCheckResponse> => {
    const { data } = await apiClient.post("/compliance/check", request);
    return data;
  },

  // Get scan job status
  getJobStatus: async (jobId: UUID): Promise<ScanJob> => {
    const { data } = await apiClient.get(`/compliance/jobs/${jobId}`);
    return data;
  },

  // List all scan jobs
  listJobs: async (params?: {
    limit?: number;
    offset?: number;
    status?: string;
    framework_id?: UUID;
  }): Promise<PaginatedResponse<ScanJob>> => {
    const { data } = await apiClient.get("/compliance/jobs", { params });
    return data;
  },

  // Get scan job statistics
  stats: async (): Promise<{
    total_scans: number;
    by_status: Record<string, number>;
    average_duration_seconds: number;
  }> => {
    const { data } = await apiClient.get("/compliance/stats/summary");
    return data;
  },
};
