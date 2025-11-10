"""
Pydantic schemas for API request/response models.
"""

from complianceguard.schemas.base import (
    BaseSchema,
    ErrorResponse,
    HealthCheckResponse,
    PaginatedResponse,
    PaginationParams,
    SuccessResponse,
    TimestampMixin,
)
from complianceguard.schemas.document import (
    DocumentDetail,
    DocumentListFilters,
    DocumentStatsResponse,
    DocumentSummary,
    DocumentUpdateRequest,
    DocumentUploadResponse,
)
from complianceguard.schemas.scan import (
    ScanListFilters,
    ScanResultsResponse,
    ScanStatsResponse,
    ScanStatusResponse,
    ScanSummary,
    ScanTriggerRequest,
    ScanTriggerResponse,
)
from complianceguard.schemas.violation import (
    ViolationDetail,
    ViolationEvidence,
    ViolationListFilters,
    ViolationRecommendation,
    ViolationStatsResponse,
    ViolationSummary,
    ViolationUpdateRequest,
)
from complianceguard.schemas.ingested_document import (
    BatchIngestResponse,
    BatchIngestResult,
    IngestDocumentResponse,
    IngestedDocumentStatsResponse,
    IngestedDocumentSummary,
    QueryRequest,
    QueryResponse,
    QueryResultItem,
)

__all__ = [
    # Base
    "BaseSchema",
    "TimestampMixin",
    "PaginationParams",
    "PaginatedResponse",
    "SuccessResponse",
    "ErrorResponse",
    "HealthCheckResponse",
    # Document
    "DocumentUploadResponse",
    "DocumentSummary",
    "DocumentDetail",
    "DocumentListFilters",
    "DocumentUpdateRequest",
    "DocumentStatsResponse",
    # Violation
    "ViolationEvidence",
    "ViolationRecommendation",
    "ViolationSummary",
    "ViolationDetail",
    "ViolationListFilters",
    "ViolationUpdateRequest",
    "ViolationStatsResponse",
    # Scan
    "ScanTriggerRequest",
    "ScanTriggerResponse",
    "ScanStatusResponse",
    "ScanResultsResponse",
    "ScanSummary",
    "ScanListFilters",
    "ScanStatsResponse",
    # Ingested Document
    "IngestDocumentResponse",
    "BatchIngestResult",
    "BatchIngestResponse",
    "QueryRequest",
    "QueryResponse",
    "QueryResultItem",
    "IngestedDocumentSummary",
    "IngestedDocumentStatsResponse",
]
