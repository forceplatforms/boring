import apiClient from "./client";
import type {
  Violation,
  UpdateViolationRequest,
  PaginatedResponse,
  ViolationStats,
  ViolationSeverity,
  ViolationStatus,
  UUID,
} from "@/lib/types/api";

export const violationsApi = {
  // List violations with pagination and filters
  list: async (params?: {
    limit?: number;
    offset?: number;
    severity?: ViolationSeverity;
    status?: ViolationStatus;
    framework?: string;
    assigned_to_email?: string;
    search?: string;
  }): Promise<PaginatedResponse<Violation>> => {
    const { data } = await apiClient.get("/violations/", { params });
    return data;
  },

  // Get single violation by ID
  get: async (id: UUID): Promise<Violation> => {
    const { data } = await apiClient.get(`/violations/${id}`);
    return data;
  },

  // Update violation
  update: async (
    id: UUID,
    updates: UpdateViolationRequest
  ): Promise<Violation> => {
    const { data } = await apiClient.patch(`/violations/${id}`, updates);
    return data;
  },

  // Acknowledge violation
  acknowledge: async (id: UUID): Promise<Violation> => {
    const { data } = await apiClient.post(`/violations/${id}/acknowledge`);
    return data;
  },

  // Get violation statistics
  stats: async (): Promise<ViolationStats> => {
    const { data } = await apiClient.get("/violations/stats/summary");
    return data;
  },
};
