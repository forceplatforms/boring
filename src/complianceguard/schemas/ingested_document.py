"""
Pydantic schemas for document ingestion and query API endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from complianceguard.schemas.base import BaseSchema, TimestampMixin


# Ingest API Schemas


class IngestDocumentResponse(BaseSchema, TimestampMixin):
    """Response after ingesting a single document."""

    id: UUID = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    file_hash: str = Field(..., description="SHA-256 hash for deduplication")
    file_size: int = Field(..., description="File size in bytes")
    file_size_mb: float = Field(..., description="File size in megabytes")
    mime_type: str = Field(..., description="MIME type")
    doc_type: Optional[str] = Field(None, description="Document type")
    doc_category: Optional[str] = Field(None, description="Document category")
    indexing_status: str = Field(..., description="Indexing status: pending, processing, completed, failed")
    s3_key: str = Field(..., description="S3 key for the document")
    s3_bucket: str = Field(..., description="S3 bucket name")
    metadata: dict = Field(default_factory=dict, description="Custom metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "contract_2024.pdf",
                "file_hash": "a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2",
                "file_size": 2457600,
                "file_size_mb": 2.34,
                "mime_type": "application/pdf",
                "doc_type": "contract",
                "doc_category": "legal",
                "indexing_status": "pending",
                "s3_key": "documents/2025/11/10/a7/a7b8c9d0e1f2g3h4.pdf",
                "s3_bucket": "complianceguard-documents",
                "metadata": {
                    "author": "John Doe",
                    "date": "2024-01-15",
                    "tags": ["legal", "contract"]
                },
                "created_at": "2025-11-10T14:32:00Z",
                "updated_at": "2025-11-10T14:32:00Z",
            }
        }


class BatchIngestResult(BaseSchema):
    """Result for a single document in a batch ingest operation."""

    filename: str = Field(..., description="Original filename")
    success: bool = Field(..., description="Whether the ingest was successful")
    document: Optional[IngestDocumentResponse] = Field(None, description="Document details if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    duplicate: bool = Field(default=False, description="Whether this was a duplicate file")

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "contract_2024.pdf",
                "success": True,
                "document": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "filename": "contract_2024.pdf",
                    "file_hash": "a7b8c9d0e1f2g3h4i5j6k7l8m9n0o1p2q3r4s5t6u7v8w9x0y1z2",
                    "file_size": 2457600,
                    "file_size_mb": 2.34,
                    "mime_type": "application/pdf",
                    "doc_type": "contract",
                    "doc_category": "legal",
                    "indexing_status": "pending",
                    "s3_key": "documents/2025/11/10/a7/a7b8c9d0e1f2g3h4.pdf",
                    "s3_bucket": "complianceguard-documents",
                    "metadata": {},
                    "created_at": "2025-11-10T14:32:00Z",
                    "updated_at": "2025-11-10T14:32:00Z",
                },
                "error": None,
                "duplicate": False,
            }
        }


class BatchIngestResponse(BaseSchema):
    """Response for batch document ingest operation."""

    total: int = Field(..., description="Total number of files submitted")
    successful: int = Field(..., description="Number of successful ingests")
    failed: int = Field(..., description="Number of failed ingests")
    duplicates: int = Field(..., description="Number of duplicate files")
    results: list[BatchIngestResult] = Field(..., description="Results for each file")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 3,
                "successful": 2,
                "failed": 1,
                "duplicates": 0,
                "results": [
                    {
                        "filename": "contract_2024.pdf",
                        "success": True,
                        "document": {
                            "id": "550e8400-e29b-41d4-a716-446655440000",
                            "filename": "contract_2024.pdf",
                            "file_size": 2457600,
                            "indexing_status": "pending"
                        },
                        "error": None,
                        "duplicate": False
                    },
                    {
                        "filename": "invalid.txt",
                        "success": False,
                        "document": None,
                        "error": "Invalid file type. Only PDFs are supported.",
                        "duplicate": False
                    }
                ]
            }
        }


# Query API Schemas


class QueryRequest(BaseSchema):
    """Request for document search query."""

    query: str = Field(..., description="Search query string", min_length=1)
    k: int = Field(default=5, ge=1, le=50, description="Number of top results to return")
    min_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    index_name: Optional[str] = Field(None, description="Milvus index name to search (defaults to configured index)")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the contract termination clause?",
                "k": 5,
                "min_threshold": 0.5,
                "index_name": "ingested_documents"
            }
        }


class QueryResultItem(BaseSchema):
    """Single result item from a query."""

    rank: int = Field(..., description="Result ranking (1-indexed)")
    score: float = Field(..., description="Similarity score (0-1)")
    page_number: int = Field(..., description="Page number in document")
    filepath: str = Field(..., description="Original document filepath")
    filename: str = Field(..., description="Original document filename")
    page_image_url: Optional[str] = Field(None, description="S3 URL for page image")
    document_id: Optional[UUID] = Field(None, description="Document ID if available")
    doc_type: Optional[str] = Field(None, description="Document type")
    doc_category: Optional[str] = Field(None, description="Document category")
    metadata: dict = Field(default_factory=dict, description="Document metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "rank": 1,
                "score": 0.87,
                "page_number": 5,
                "filepath": "/path/to/contract_2024.pdf",
                "filename": "contract_2024.pdf",
                "page_image_url": "https://s3.amazonaws.com/complianceguard-page-images/pages/abc123/contract_2024.pdf/page_0005.png",
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "doc_type": "contract",
                "doc_category": "legal",
                "metadata": {
                    "author": "John Doe",
                    "date": "2024-01-15"
                }
            }
        }


class QueryResponse(BaseSchema):
    """Response for document search query."""

    query: str = Field(..., description="Original search query")
    k: int = Field(..., description="Number of results requested")
    min_threshold: float = Field(..., description="Minimum score threshold applied")
    index_name: str = Field(..., description="Milvus index searched")
    total_documents_in_index: int = Field(..., description="Total documents in the index")
    results_count: int = Field(..., description="Number of results returned")
    results: list[QueryResultItem] = Field(..., description="Search results")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is the contract termination clause?",
                "k": 5,
                "min_threshold": 0.5,
                "index_name": "ingested_documents",
                "total_documents_in_index": 124,
                "results_count": 3,
                "results": [
                    {
                        "rank": 1,
                        "score": 0.87,
                        "page_number": 5,
                        "filepath": "/path/to/contract_2024.pdf",
                        "filename": "contract_2024.pdf",
                        "page_image_url": "https://s3.amazonaws.com/...",
                        "document_id": "550e8400-e29b-41d4-a716-446655440000",
                        "doc_type": "contract",
                        "doc_category": "legal",
                        "metadata": {}
                    }
                ]
            }
        }


# Document List/Stats Schemas


class IngestedDocumentSummary(BaseSchema, TimestampMixin):
    """Summary view of an ingested document for list endpoints."""

    id: UUID = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    doc_type: Optional[str] = Field(None, description="Document type")
    doc_category: Optional[str] = Field(None, description="Document category")
    file_size: int = Field(..., description="File size in bytes")
    file_size_mb: float = Field(..., description="File size in megabytes")
    indexing_status: str = Field(..., description="Indexing status")
    index_name: Optional[str] = Field(None, description="Milvus collection name")
    num_pages: Optional[int] = Field(None, description="Number of pages")
    indexed_at: Optional[datetime] = Field(None, description="When document was indexed")
    metadata: dict = Field(default_factory=dict, description="Custom metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "filename": "contract_2024.pdf",
                "doc_type": "contract",
                "doc_category": "legal",
                "file_size": 2457600,
                "file_size_mb": 2.34,
                "indexing_status": "completed",
                "num_pages": 12,
                "indexed_at": "2025-11-10T14:35:00Z",
                "metadata": {"author": "John Doe"},
                "created_at": "2025-11-10T14:32:00Z",
                "updated_at": "2025-11-10T14:35:00Z",
            }
        }


class IngestedDocumentStatsResponse(BaseSchema):
    """Statistics for ingested documents."""

    total: int = Field(..., description="Total number of documents")
    by_type: dict = Field(..., description="Count by document type")
    by_status: dict = Field(..., description="Count by indexing status")
    by_index: dict = Field(..., description="Count by Milvus index")
    total_size_bytes: int = Field(..., description="Total storage used in bytes")
    total_size_mb: float = Field(..., description="Total storage used in MB")

    class Config:
        json_schema_extra = {
            "example": {
                "total": 124,
                "by_type": {
                    "contract": 45,
                    "invoice": 67,
                    "report": 12
                },
                "by_status": {
                    "completed": 120,
                    "pending": 3,
                    "failed": 1
                },
                "by_index": {
                    "ingested_documents": 124
                },
                "total_size_bytes": 305175040,
                "total_size_mb": 291.0
            }
        }
