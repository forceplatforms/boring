import apiClient, { createFormDataClient } from "./client";
import type {
  IngestedDocument,
  PaginatedResponse,
  IngestResponse,
  UUID,
} from "@/lib/types/api";

// File upload constraints
export const UPLOAD_CONSTRAINTS = {
  MAX_FILE_SIZE: 100 * 1024 * 1024, // 100MB per file
  MAX_TOTAL_SIZE: 500 * 1024 * 1024, // 500MB total
  MAX_FILE_COUNT: 20,
  ALLOWED_TYPES: ["application/pdf"],
  ALLOWED_EXTENSIONS: [".pdf"],
} as const;

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface UploadOptions {
  onProgress?: (progress: UploadProgress) => void;
  signal?: AbortSignal;
}

export interface FileValidationError {
  file: string;
  error: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: FileValidationError[];
}

// Validate files before upload
export function validateFiles(files: File[]): ValidationResult {
  const errors: FileValidationError[] = [];

  // Check file count
  if (files.length === 0) {
    errors.push({ file: "general", error: "No files selected" });
    return { valid: false, errors };
  }

  if (files.length > UPLOAD_CONSTRAINTS.MAX_FILE_COUNT) {
    errors.push({
      file: "general",
      error: `Maximum ${UPLOAD_CONSTRAINTS.MAX_FILE_COUNT} files allowed`,
    });
  }

  // Check total size
  const totalSize = files.reduce((sum, file) => sum + file.size, 0);
  if (totalSize > UPLOAD_CONSTRAINTS.MAX_TOTAL_SIZE) {
    errors.push({
      file: "general",
      error: `Total size exceeds ${Math.round(UPLOAD_CONSTRAINTS.MAX_TOTAL_SIZE / 1024 / 1024)}MB limit`,
    });
  }

  // Check individual files
  files.forEach((file) => {
    // Check file type
    if (!UPLOAD_CONSTRAINTS.ALLOWED_TYPES.includes(file.type)) {
      errors.push({
        file: file.name,
        error: "Only PDF files are allowed",
      });
    }

    // Check file size
    if (file.size > UPLOAD_CONSTRAINTS.MAX_FILE_SIZE) {
      errors.push({
        file: file.name,
        error: `File exceeds ${Math.round(UPLOAD_CONSTRAINTS.MAX_FILE_SIZE / 1024 / 1024)}MB limit`,
      });
    }

    // Check if file is empty
    if (file.size === 0) {
      errors.push({
        file: file.name,
        error: "File is empty",
      });
    }
  });

  return { valid: errors.length === 0, errors };
}

export const documentsApi = {
  // List documents with pagination and filters
  list: async (params?: {
    limit?: number;
    offset?: number;
    doc_type?: string;
    doc_category?: string;
    indexing_status?: string;
    index_name?: string;
  }): Promise<PaginatedResponse<IngestedDocument>> => {
    const { data } = await apiClient.get("/ingest", { params });
    return data;
  },

  // Get single document by ID
  get: async (id: UUID): Promise<IngestedDocument> => {
    const { data } = await apiClient.get(`/ingest/${id}`);
    return data;
  },

  // Get document status (for polling)
  getStatus: async (id: UUID): Promise<IngestedDocument> => {
    const { data} = await apiClient.get(`/ingest/${id}/status`);
    return data;
  },

  // Upload/ingest documents with progress tracking
  ingest: async (
    files: File[],
    indexName: string,
    options?: UploadOptions
  ): Promise<IngestResponse> => {
    // Validate files first
    const validation = validateFiles(files);
    if (!validation.valid) {
      throw new Error(validation.errors.map((e) => e.error).join(", "));
    }

    const formData = new FormData();
    files.forEach((file) => {
      formData.append("files", file);
    });
    formData.append("index_name", indexName);

    const client = createFormDataClient();
    const { data } = await client.post("/ingest", formData, {
      signal: options?.signal,
      onUploadProgress: options?.onProgress
        ? (progressEvent) => {
            if (progressEvent.total) {
              options.onProgress?.({
                loaded: progressEvent.loaded,
                total: progressEvent.total,
                percentage: Math.round(
                  (progressEvent.loaded / progressEvent.total) * 100
                ),
              });
            }
          }
        : undefined,
    });
    return data;
  },

  // Update document metadata
  update: async (
    id: UUID,
    updates: {
      doc_type?: string;
      doc_category?: string;
      metadata?: Record<string, any>;
    }
  ): Promise<IngestedDocument> => {
    const { data } = await apiClient.patch(`/documents/${id}`, updates);
    return data;
  },

  // Delete document
  delete: async (id: UUID): Promise<void> => {
    await apiClient.delete(`/documents/${id}`);
  },

  // Get document statistics
  stats: async (): Promise<{
    total: number;
    by_status: Record<string, number>;
    by_type: Record<string, number>;
    by_index: Record<string, number>;
    total_size_bytes: number;
    total_size_mb: number;
  }> => {
    const { data } = await apiClient.get("/ingest/stats");
    return data;
  },

  // Get unique index names
  getUniqueIndexes: async (): Promise<string[]> => {
    const { data } = await apiClient.get("/ingest/indexes");
    return data;
  },
};
