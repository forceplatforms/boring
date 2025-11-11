"""
Database models for ComplianceGuard.

Implements a denormalized design pattern to optimize for read performance
and minimize JOIN operations.
"""

from complianceguard.models.base import BaseModel
from complianceguard.models.document import (
    Document,
    DocumentType,
    DocumentCategory,
    ExtractionStatus,
)
from complianceguard.models.document_chunk import (
    DocumentChunk,
    ChunkType,
)
from complianceguard.models.document_split import (
    DocumentSplit,
)
from complianceguard.models.violation import (
    Violation,
    ViolationSeverity,
    ViolationType,
    ViolationStatus,
)
from complianceguard.models.compliance_framework import (
    ComplianceFramework,
)
from complianceguard.models.scan_job import (
    ScanJob,
    ScanType,
    ScanStatus,
)
from complianceguard.models.ingested_document import (
    IngestedDocument,
)

__all__ = [
    # Base
    "BaseModel",
    # Document
    "Document",
    "DocumentType",
    "DocumentCategory",
    "ExtractionStatus",
    # Document Chunks
    "DocumentChunk",
    "ChunkType",
    # Document Splits
    "DocumentSplit",
    # Violation
    "Violation",
    "ViolationSeverity",
    "ViolationType",
    "ViolationStatus",
    "ComplianceFramework",
    # ScanJob
    "ScanJob",
    "ScanType",
    "ScanStatus",
    # Ingested Document
    "IngestedDocument",
]