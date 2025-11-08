"""
Pydantic schemas for document-related API endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from complianceguard.schemas.base import BaseSchema, TimestampMixin


class DocumentUploadResponse(BaseSchema, TimestampMixin):
    """Response after uploading a document."""

    id: UUID = Field(..., description="Unique document identifier")
    file_name: str = Field(..., description="Original file name")
    doc_type: str = Field(..., description="Document type (ciso_report, sec_filing)")
    doc_category: Optional[str] = Field(None, description="Document category")
    file_size_bytes: int = Field(..., description="File size in bytes")
    extraction_status: str = Field(..., description="Text extraction status")
    uploaded_by: Optional[str] = Field(None, description="Email of uploader")
    file_url: Optional[str] = Field(None, description="Presigned S3 URL for document access")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "CISO_Report_October_2024.pdf",
                "doc_type": "ciso_report",
                "doc_category": "Incident_Report",
                "file_size_bytes": 2457600,
                "extraction_status": "pending",
                "uploaded_by": "security@company.com",
                "created_at": "2025-11-07T14:32:00Z",
                "updated_at": "2025-11-07T14:32:00Z",
            }
        }


class DocumentSummary(BaseSchema, TimestampMixin):
    """Summary view of a document for list endpoints."""

    id: UUID = Field(..., description="Unique document identifier")
    file_name: str = Field(..., description="Original file name")
    doc_type: str = Field(..., description="Document type")
    doc_category: Optional[str] = Field(None, description="Document category")
    extraction_status: str = Field(..., description="Extraction status")
    file_size_bytes: int = Field(..., description="File size in bytes")
    uploaded_by: Optional[str] = Field(None, description="Uploader email")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "Form_8K_Draft.docx",
                "doc_type": "sec_filing",
                "doc_category": "Form_8K",
                "extraction_status": "completed",
                "file_size_bytes": 1024000,
                "uploaded_by": "legal@company.com",
                "created_at": "2025-11-07T14:45:00Z",
                "updated_at": "2025-11-07T14:46:30Z",
            }
        }


class DocumentDetail(DocumentSummary):
    """Detailed view of a document including extracted content."""

    file_path: str = Field(..., description="Storage path in MinIO")
    file_hash: str = Field(..., description="SHA-256 hash of file")
    mime_type: str = Field(..., description="MIME type")
    extracted_text: Optional[str] = Field(None, description="Extracted text content")
    extraction_error: Optional[str] = Field(None, description="Extraction error message")
    extraction_metadata: dict = Field(default_factory=dict, description="Extraction metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "CISO_Report_October_2024.pdf",
                "doc_type": "ciso_report",
                "doc_category": "Incident_Report",
                "extraction_status": "completed",
                "file_size_bytes": 2457600,
                "uploaded_by": "security@company.com",
                "file_path": "documents/550e8400-e29b-41d4-a716-446655440000/original.pdf",
                "file_hash": "a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2",
                "mime_type": "application/pdf",
                "extracted_text": "On October 27, 2024, TechVest Corp identified a cybersecurity incident...",
                "extraction_error": None,
                "extraction_metadata": {
                    "num_pages": 12,
                    "tables_found": 3,
                    "text_length": 45230,
                    "processing_time_ms": 3420,
                    "language": "en",
                    "confidence_score": 0.98,
                },
                "created_at": "2025-11-07T14:32:00Z",
                "updated_at": "2025-11-07T14:33:30Z",
            }
        }


class DocumentListFilters(BaseSchema):
    """Filters for document list endpoint."""

    doc_type: Optional[str] = Field(None, description="Filter by document type")
    extraction_status: Optional[str] = Field(None, description="Filter by extraction status")
    uploaded_by: Optional[str] = Field(None, description="Filter by uploader email")
    search: Optional[str] = Field(None, description="Search in file names")

    class Config:
        json_schema_extra = {
            "example": {
                "doc_type": "ciso_report",
                "extraction_status": "completed",
                "uploaded_by": "security@company.com",
                "search": "October",
            }
        }


class DocumentUpdateRequest(BaseSchema):
    """Request to update document metadata."""

    doc_type: Optional[str] = Field(None, description="Update document type")
    doc_category: Optional[str] = Field(None, description="Update document category")

    class Config:
        json_schema_extra = {
            "example": {
                "doc_type": "sec_filing",
                "doc_category": "Form_10K",
            }
        }


class DocumentStatsResponse(BaseSchema):
    """Document statistics."""

    total_documents: int = Field(..., description="Total number of documents")
    by_type: dict = Field(..., description="Count by document type")
    by_status: dict = Field(..., description="Count by extraction status")
    total_size_mb: float = Field(..., description="Total storage used in MB")

    class Config:
        json_schema_extra = {
            "example": {
                "total_documents": 157,
                "by_type": {
                    "ciso_report": 89,
                    "sec_filing": 68,
                },
                "by_status": {
                    "completed": 145,
                    "pending": 8,
                    "processing": 3,
                    "failed": 1,
                },
                "total_size_mb": 2847.5,
            }
        }


# Document Chunk Schemas


class ChunkBoundingBox(BaseSchema):
    """Bounding box coordinates for a chunk."""

    left: Optional[int] = Field(None, description="Left coordinate in pixels")
    top: Optional[int] = Field(None, description="Top coordinate in pixels")
    right: Optional[int] = Field(None, description="Right coordinate in pixels")
    bottom: Optional[int] = Field(None, description="Bottom coordinate in pixels")

    class Config:
        json_schema_extra = {
            "example": {
                "left": 100,
                "top": 200,
                "right": 500,
                "bottom": 300,
            }
        }


class DocumentChunkResponse(BaseSchema, TimestampMixin):
    """Response for a document chunk."""

    id: UUID = Field(..., description="Unique chunk ID")
    document_id: UUID = Field(..., description="Parent document ID")
    chunk_id: str = Field(..., description="Landing AI chunk ID")
    chunk_type: str = Field(..., description="Type: text, table, figure, etc.")
    chunk_order: int = Field(..., description="Order in document (0-indexed)")
    content: str = Field(..., description="Markdown content")
    page_number: int = Field(..., description="Page number (1-indexed)")
    bounding_box: dict = Field(..., description="Bounding box coordinates")
    split_identifier: Optional[str] = Field(None, description="Split/section identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "650e8400-e29b-41d4-a716-446655440000",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "chunk_id": "chunk-abc-123",
                "chunk_type": "table",
                "chunk_order": 5,
                "content": "| Incident Date | Description | Impact |\n|---|---|---|\n| 2024-10-27 | Data breach | High |",
                "page_number": 3,
                "bounding_box": {
                    "left": 100,
                    "top": 200,
                    "right": 500,
                    "bottom": 300,
                },
                "split_identifier": "Item_1C",
                "created_at": "2025-11-07T14:33:30Z",
                "updated_at": "2025-11-07T14:33:30Z",
            }
        }


class ChunkStatsResponse(BaseSchema):
    """Chunk statistics for a document."""

    total: int = Field(..., description="Total number of chunks")
    by_type: dict = Field(..., description="Count by chunk type")
    by_page: dict = Field(..., description="Count by page number")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 45,
                "by_type": {
                    "text": 30,
                    "table": 12,
                    "figure": 3,
                },
                "by_page": {
                    "1": 5,
                    "2": 8,
                    "3": 10,
                },
            }
        }


# Document Split Schemas


class DocumentSplitResponse(BaseSchema, TimestampMixin):
    """Response for a document split/section."""

    id: UUID = Field(..., description="Unique split ID")
    document_id: UUID = Field(..., description="Parent document ID")
    class_: str = Field(..., alias="class", description="Split class: section, chapter, etc.")
    identifier: str = Field(..., description="Section identifier: Item_1C, Risk_Factors, etc.")
    pages: list[int] = Field(..., description="Array of page numbers")
    markdown: Optional[str] = Field(None, description="Combined markdown content")
    chunk_ids: list[str] = Field(..., description="Array of chunk IDs in this split")
    split_order: int = Field(..., description="Order in document (0-indexed)")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "750e8400-e29b-41d4-a716-446655440000",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "class": "section",
                "identifier": "Item_1C",
                "pages": [5, 6, 7],
                "markdown": "# Item 1C. Cybersecurity\n\nOn October 27, 2024...",
                "chunk_ids": ["chunk-abc-123", "chunk-def-456"],
                "split_order": 2,
                "created_at": "2025-11-07T14:33:30Z",
                "updated_at": "2025-11-07T14:33:30Z",
            }
        }


class SplitStatsResponse(BaseSchema):
    """Split statistics for a document."""

    total: int = Field(..., description="Total number of splits")
    by_class: dict = Field(..., description="Count by split class")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 8,
                "by_class": {
                    "section": 6,
                    "chapter": 2,
                },
            }
        }
