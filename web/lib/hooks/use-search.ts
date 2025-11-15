import { useMutation } from "@tanstack/react-query";
import { searchApi } from "@/lib/api/search";
import type { QueryRequest, QueryResponse } from "@/lib/types/api";

// Search documents mutation
export function useSearchDocuments() {
  return useMutation<QueryResponse, Error, QueryRequest>({
    mutationFn: (request: QueryRequest) => searchApi.query(request),
  });
}
