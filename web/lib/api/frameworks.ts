import apiClient from "./client";
import type {
  ComplianceFramework,
  CreateFrameworkRequest,
  UpdateFrameworkRequest,
  PaginatedResponse,
  FrameworkStats,
  UUID,
} from "@/lib/types/api";

export const frameworksApi = {
  // List frameworks with pagination and filters
  list: async (params?: {
    limit?: number;
    offset?: number;
    is_active?: boolean;
    search?: string;
  }): Promise<PaginatedResponse<ComplianceFramework>> => {
    const { data } = await apiClient.get("/frameworks/", { params });
    return data;
  },

  // Get single framework by ID
  get: async (id: UUID): Promise<ComplianceFramework> => {
    const { data } = await apiClient.get(`/frameworks/${id}`);
    return data;
  },

  // Create new framework
  create: async (
    framework: CreateFrameworkRequest
  ): Promise<ComplianceFramework> => {
    const { data } = await apiClient.post("/frameworks/", framework);
    return data;
  },

  // Update framework
  update: async (
    id: UUID,
    updates: UpdateFrameworkRequest
  ): Promise<ComplianceFramework> => {
    const { data } = await apiClient.put(`/frameworks/${id}`, updates);
    return data;
  },

  // Update compliance todos
  updateTodos: async (
    id: UUID,
    todos: string[]
  ): Promise<ComplianceFramework> => {
    const { data} = await apiClient.patch(`/frameworks/${id}/todos`, {
      compliance_todos: todos,
    });
    return data;
  },

  // Delete framework
  delete: async (id: UUID): Promise<void> => {
    await apiClient.delete(`/frameworks/${id}`);
  },

  // Get framework statistics
  stats: async (): Promise<FrameworkStats> => {
    const { data } = await apiClient.get("/frameworks/stats/summary");
    return data;
  },
};
