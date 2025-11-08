"""
Document model for storing uploaded files and their extracted content.
Follows a denormalized design to minimize joins and improve query performance.
"""

from enum import Enum
from typing import Optional

from sqlalchemy import BigInteger, Column, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from complianceguard.models.base import BaseModel


class DocumentType(str, Enum):
    """Document type enumeration."""

    CISO_REPORT = "ciso_report"
    SEC_FILING = "sec_filing"
    UNKNOWN = "unknown"


class DocumentCategory(str, Enum):
    """Document category enumeration."""

    FORM_8K = "Form_8K"
    FORM_10K = "Form_10K"
    FORM_10Q = "Form_10Q"
    PROXY_STATEMENT = "Proxy_Statement"
    INCIDENT_REPORT = "Incident_Report"
    VULNERABILITY_ASSESSMENT = "Vulnerability_Assessment"
    AUDIT_REPORT = "Audit_Report"
    OTHER = "Other"


class ExtractionStatus(str, Enum):
    """Document extraction status enumeration."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Document(BaseModel):
    """
    Document model with denormalized structure for efficient querying.

    This model stores everything about a document in a single row,
    including file metadata, extracted content, and processing status.
    """

    __tablename__ = "documents"

    # File Metadata (embedded, no separate table)
    file_name = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Original file name",
    )
    file_path = Column(
        Text,
        nullable=False,
        comment="MinIO storage path (e.g., documents/{uuid}/original.pdf)",
    )
    file_hash = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="SHA-256 hash for deduplication",
    )
    file_size_bytes = Column(
        BigInteger,
        nullable=False,
        comment="File size in bytes",
    )
    mime_type = Column(
        String(100),
        nullable=False,
        comment="MIME type of the file",
    )

    # Classification
    doc_type = Column(
        String(50),
        nullable=False,
        index=True,
        default=DocumentType.UNKNOWN,
        comment="Document type: ciso_report, sec_filing, unknown",
    )
    doc_category = Column(
        String(50),
        nullable=True,
        index=True,
        comment="Document category: Form_8K, Incident_Report, etc.",
    )

    # Extracted Content (denormalized - store directly in row)
    extracted_text = Column(
        Text,
        nullable=True,
        comment="Full extracted text from the document",
    )
    extraction_status = Column(
        String(20),
        default=ExtractionStatus.PENDING,
        nullable=False,
        index=True,
        comment="Extraction status: pending, processing, completed, failed",
    )
    extraction_error = Column(
        Text,
        nullable=True,
        comment="Error message if extraction failed",
    )

    # Extracted Metadata (JSONB - flexible structure)
    extraction_metadata = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="""
        Extraction metadata in JSON format. Example:
        {
            "num_pages": 12,
            "tables_found": 3,
            "extracted_at": "2025-11-07T15:30:00Z",
            "landing_ai_job_id": "abc123",
            "processing_time_ms": 3420,
            "text_length": 45230,
            "language": "en",
            "confidence_score": 0.98
        }
        """,
    )

    # External Service IDs (denormalized)
    gemini_corpus_id = Column(
        String(100),
        nullable=True,
        comment="Google Gemini corpus ID if indexed",
    )
    gemini_document_id = Column(
        String(100),
        nullable=True,
        comment="Google Gemini document ID if indexed",
    )

    # User Context (embedded, no user table needed for MVP)
    uploaded_by_email = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Email of the user who uploaded the document",
    )
    uploaded_by_name = Column(
        String(255),
        nullable=True,
        comment="Name of the user who uploaded the document",
    )

    # Relationships to chunks and splits
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="select",
    )
    splits = relationship(
        "DocumentSplit",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="select",
    )

    # Define indexes for better query performance
    __table_args__ = (
        Index("idx_documents_type_status", "doc_type", "extraction_status"),
        Index("idx_documents_category_status", "doc_category", "extraction_status"),
        Index("idx_documents_uploaded_by", "uploaded_by_email", "created_at"),
        # GIN index for JSONB queries
        Index(
            "idx_documents_metadata_gin",
            "extraction_metadata",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Document(id={self.id}, file_name={self.file_name}, type={self.doc_type})>"

    @property
    def is_processed(self) -> bool:
        """Check if document has been processed."""
        return self.extraction_status == ExtractionStatus.COMPLETED

    @property
    def has_error(self) -> bool:
        """Check if document processing failed."""
        return self.extraction_status == ExtractionStatus.FAILED

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size_bytes / (1024 * 1024)

    def get_extraction_metadata(self, key: str, default: any = None) -> any:
        """
        Get a specific value from extraction metadata.

        Args:
            key: The key to retrieve.
            default: Default value if key not found.

        Returns:
            The value from metadata or default.
        """
        if self.extraction_metadata:
            return self.extraction_metadata.get(key, default)
        return default

    def set_extraction_metadata(self, key: str, value: any) -> None:
        """
        Set a specific value in extraction metadata.

        Args:
            key: The key to set.
            value: The value to set.
        """
        if not self.extraction_metadata:
            self.extraction_metadata = {}
        self.extraction_metadata[key] = value

    def mark_as_processing(self) -> None:
        """Mark document as being processed."""
        self.extraction_status = ExtractionStatus.PROCESSING

    def mark_as_completed(self, extracted_text: str, metadata: Optional[dict] = None) -> None:
        """
        Mark document as successfully processed.

        Args:
            extracted_text: The extracted text content.
            metadata: Additional metadata to store.
        """
        self.extraction_status = ExtractionStatus.COMPLETED
        self.extracted_text = extracted_text
        self.extraction_error = None
        if metadata:
            if not self.extraction_metadata:
                self.extraction_metadata = {}
            self.extraction_metadata.update(metadata)

    def mark_as_failed(self, error_message: str) -> None:
        """
        Mark document as failed processing.

        Args:
            error_message: The error that occurred.
        """
        self.extraction_status = ExtractionStatus.FAILED
        self.extraction_error = error_message

    def to_summary_dict(self) -> dict:
        """
        Get a summary dictionary for API responses.

        Returns:
            Dictionary with key document information.
        """
        return {
            "id": str(self.id),
            "file_name": self.file_name,
            "doc_type": self.doc_type,
            "doc_category": self.doc_category,
            "extraction_status": self.extraction_status,
            "file_size_bytes": self.file_size_bytes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "uploaded_by": self.uploaded_by_email,
        }