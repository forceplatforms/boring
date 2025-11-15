import apiClient from "./client";
import type { QueryRequest, QueryResponse } from "@/lib/types/api";

export const searchApi = {
  // Query documents with semantic search
  query: async (request: QueryRequest): Promise<QueryResponse> => {
    const { data } = await apiClient.post("/query", request);
    return data;
  },
};
