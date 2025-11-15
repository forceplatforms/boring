import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { documentsApi } from "@/lib/api/documents";
import type {
  IngestedDocument,
  DocumentListParams,
  IngestResponse,
  DocumentStats,
} from "@/lib/types/api";

// Query keys
export const documentKeys = {
  all: ["documents"] as const,
  lists: () => [...documentKeys.all, "list"] as const,
  list: (params: DocumentListParams) =>
    [...documentKeys.lists(), params] as const,
  details: () => [...documentKeys.all, "detail"] as const,
  detail: (id: string) => [...documentKeys.details(), id] as const,
  stats: () => [...documentKeys.all, "stats"] as const,
};

// Fetch documents list
export function useDocuments(
  params: DocumentListParams = {},
  options?: {
    refetchInterval?: number | ((query: any) => number | false);
  }
) {
  return useQuery({
    queryKey: documentKeys.list(params),
    queryFn: () => documentsApi.list(params),
    staleTime: 30000, // 30 seconds
    refetchInterval: options?.refetchInterval,
  });
}

// Fetch single document
export function useDocument(id: string) {
  return useQuery({
    queryKey: documentKeys.detail(id),
    queryFn: () => documentsApi.get(id),
    enabled: !!id,
  });
}

// Poll document status (for background processing)
export function useDocumentStatus(id: string | null, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: [...documentKeys.detail(id || ""), "status"] as const,
    queryFn: () => documentsApi.getStatus(id!),
    enabled: !!id && (options?.enabled !== false),
    refetchInterval: (query) => {
      const data = query.state.data;
      // Stop polling if status is completed or failed
      if (data?.indexing_status === "completed" || data?.indexing_status === "failed") {
        return false;
      }
      // Poll every 2 seconds while processing
      return 2000;
    },
    refetchOnWindowFocus: false, // Don't refetch on window focus
    staleTime: 0, // Always consider stale to enable polling
  });
}

// Fetch document stats
export function useDocumentStats() {
  return useQuery({
    queryKey: documentKeys.stats(),
    queryFn: () => documentsApi.stats(),
    staleTime: 60000, // 1 minute
  });
}

// Fetch unique index names
export function useUniqueIndexes() {
  return useQuery({
    queryKey: [...documentKeys.all, "indexes"] as const,
    queryFn: () => documentsApi.getUniqueIndexes(),
    staleTime: 60000, // 1 minute
  });
}

// Ingest documents mutation with progress tracking
export function useIngestDocuments() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      files,
      indexName,
      onProgress,
      signal,
    }: {
      files: File[];
      indexName: string;
      onProgress?: (progress: import("@/lib/api/documents").UploadProgress) => void;
      signal?: AbortSignal;
    }) => documentsApi.ingest(files, indexName, { onProgress, signal }),
    onSuccess: () => {
      // Invalidate documents list and stats
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
      queryClient.invalidateQueries({ queryKey: documentKeys.stats() });
    },
    retry: false, // Don't retry file uploads automatically
  });
}

// Update document mutation
export function useUpdateDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      id,
      updates,
    }: {
      id: string;
      updates: Partial<IngestedDocument>;
    }) => documentsApi.update(id, updates),
    onSuccess: (_, variables) => {
      // Invalidate the specific document and lists
      queryClient.invalidateQueries({
        queryKey: documentKeys.detail(variables.id),
      });
      queryClient.invalidateQueries({ queryKey: documentKeys.lists() });
    },
  });
}

// Delete document mutation
export function useDeleteDocument() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => documentsApi.delete(id),
    onSuccess: () => {
      // Invalidate all document queries
      queryClient.invalidateQueries({ queryKey: documentKeys.all });
    },
  });
}
