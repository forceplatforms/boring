// Base types
export type UUID = string;

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

// Document types
export interface IngestedDocument {
  id: UUID;
  filename: string;
  doc_type: string | null;
  doc_category: string | null;
  file_size: number;
  file_size_mb: number;
  indexing_status: "pending" | "processing" | "indexing" | "completed" | "failed";
  index_name: string | null;
  num_pages: number | null;
  indexed_at: string | null;
  error_message: string | null;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface IngestResponse {
  total: number;
  successful: number;
  failed: number;
  duplicates: number;
  results: Array<{
    filename: string;
    success: boolean;
    document: IngestedDocument | null;
    error: string | null;
    duplicate: boolean;
  }>;
}

// Framework types
export interface ComplianceFramework {
  id: UUID;
  name: string;
  description: string;
  version: string;
  framework_document_id: UUID | null;
  framework_index_name: string;
  compliance_todos: string[];
  metadata: Record<string, any>;
  is_active: boolean;
  created_by_email: string;
  updated_by_email: string | null;
  todo_count: number;
  is_complete: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateFrameworkRequest {
  name: string;
  description: string;
  version: string;
  framework_index_name: string;
  compliance_todos: string[];
  metadata?: Record<string, any>;
  framework_document_id?: UUID;
  is_active?: boolean;
  created_by_email?: string;
}

export interface UpdateFrameworkRequest {
  name?: string;
  description?: string;
  version?: string;
  framework_document_id?: UUID;
  compliance_todos?: string[];
  metadata?: Record<string, any>;
  is_active?: boolean;
  updated_by_email?: string;
}

// Violation types
export type ViolationSeverity = "critical" | "high" | "medium" | "low";
export type ViolationStatus = "open" | "assigned" | "in_progress" | "remediated" | "false_positive";

export interface Violation {
  id: UUID;
  severity: ViolationSeverity;
  status: ViolationStatus;
  violation_type: string;
  finding_summary: string;
  rule_citation: string;
  confidence_score: number | null;
  source_document_name: string;
  target_document_name: string;
  assigned_to: string | null;
  created_at: string;
  updated_at: string;
  // Optional detailed fields (only present in detail view)
  framework?: string;
  explanation?: string;
  evidence?: {
    source_quote: string;
    target_quote: string;
    source_page?: number;
    source_section?: string;
    target_page?: number;
    target_section?: string;
  };
  recommendations?: Array<{
    priority: string;
    description: string;
    timeline: string;
    responsible_party: string;
  }>;
  ai_metadata?: {
    model: string;
    model_version: string;
    confidence_score: number;
    processing_time_ms: number;
  };
  resolved_at?: string | null;
  resolution_notes?: string | null;
}

export interface UpdateViolationRequest {
  status?: ViolationStatus;
  assigned_to_email?: string;
  assigned_to_name?: string;
  resolution_notes?: string;
}

// Scan job types
export type ScanJobStatus = "pending" | "running" | "completed" | "failed" | "partial";

export interface ScanJob {
  id: UUID;
  framework: string;
  scan_type: string;
  status: ScanJobStatus;
  document_count: number;
  violations_found: number;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  error_message: string | null;
  results: Record<string, any>;
  triggered_by: string | null;
  created_at: string;
}

export interface ComplianceCheckRequest {
  framework_id: UUID;
  document_ids?: UUID[];
  document_index_name?: string;
  triggered_by_email?: string;
  triggered_by_name?: string;
}

export interface ComplianceCheckResponse {
  scan_job_id: UUID;
  message: string;
  framework_id: UUID;
  document_count: number;
}

// Search/Query types
export interface SearchResult {
  rank: number;
  score: number;
  page_number: number;
  filename: string;
  page_image_url: string;
  document_id: UUID;
  doc_type: string;
  metadata: Record<string, any>;
}

export interface SearchResponse {
  query: string;
  results_count: number;
  total_documents_in_index: number;
  results: SearchResult[];
}

// Statistics types
export interface FrameworkStats {
  total_frameworks: number;
  active_frameworks: number;
  inactive_frameworks: number;
}

export interface ViolationStats {
  total_violations: number;
  by_severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  by_status: {
    open: number;
    assigned: number;
    in_progress: number;
    remediated: number;
    false_positive: number;
  };
}

// Search/Query types
export interface QueryRequest {
  query: string;
  k?: number;
  min_threshold?: number;
  index_name?: string;
}

export interface QueryResultItem {
  rank: number;
  score: number;
  page_number: number;
  filepath: string;
  filename: string;
  page_image_url: string | null;
  document_id: UUID | null;
  doc_type: string | null;
  doc_category: string | null;
  metadata: Record<string, any>;
}

export interface QueryResponse {
  query: string;
  k: number;
  min_threshold: number;
  index_name: string;
  total_documents_in_index: number;
  results_count: number;
  results: QueryResultItem[];
}

// Error types
export interface ApiError {
  success: false;
  error: string;
  message: string;
  details?: string;
}
