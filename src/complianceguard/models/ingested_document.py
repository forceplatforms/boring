"""
IngestedDocument model for storing documents uploaded via ingestion API.

This is a separate model from Document to keep API-based ingestion independent
from the existing document management system.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Column, DateTime, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from complianceguard.models.base import BaseModel


class IngestedDocument(BaseModel):
    """
    Model for documents ingested via the batch ingest API.

    This model stores file metadata, S3 references, Milvus indexing info,
    and flexible JSONB metadata for custom fields.
    """

    __tablename__ = "ingested_documents"

    # File Metadata
    filename = Column(
        String(255),
        nullable=False,
        index=True,
        comment="Original filename",
    )
    file_hash = Column(
        String(64),
        unique=True,
        nullable=False,
        index=True,
        comment="SHA-256 hash for deduplication",
    )
    file_size = Column(
        BigInteger,
        nullable=False,
        comment="File size in bytes",
    )
    mime_type = Column(
        String(100),
        nullable=False,
        comment="MIME type (e.g., application/pdf)",
    )

    # S3 Storage
    s3_key = Column(
        Text,
        nullable=False,
        comment="S3 key for the PDF file (documents/YYYY/MM/DD/XX/hash.pdf)",
    )
    s3_bucket = Column(
        String(255),
        nullable=False,
        comment="S3 bucket name",
    )
    page_image_s3_prefix = Column(
        Text,
        nullable=True,
        comment="S3 prefix for page images (pages/{hash}/{filename}/)",
    )

    # Classification & Metadata
    doc_type = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Document type (contract, invoice, report, etc.)",
    )
    doc_category = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Document category for additional classification",
    )
    doc_metadata = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="""
        Flexible metadata in JSON format. Example:
        {
            "author": "John Doe",
            "date": "2024-01-15",
            "tags": ["legal", "contract"],
            "source": "email",
            "custom_field": "value"
        }
        """,
    )

    # Milvus Indexing Info
    index_name = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Milvus collection/index name",
    )
    num_pages = Column(
        Integer,
        nullable=True,
        comment="Number of pages in the document",
    )
    indexed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp when document was indexed in Milvus",
    )
    indexing_status = Column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
        comment="Indexing status: pending, processing, completed, failed",
    )
    indexing_error = Column(
        Text,
        nullable=True,
        comment="Error message if indexing failed",
    )

    # Define indexes for better query performance
    __table_args__ = (
        Index("idx_ingested_docs_hash", "file_hash"),
        Index("idx_ingested_docs_type", "doc_type"),
        Index("idx_ingested_docs_category", "doc_category"),
        Index("idx_ingested_docs_index_name", "index_name"),
        Index("idx_ingested_docs_status", "indexing_status"),
        Index("idx_ingested_docs_created", "created_at"),
        # GIN index for JSONB metadata queries
        Index(
            "idx_ingested_docs_metadata_gin",
            "doc_metadata",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<IngestedDocument(id={self.id}, filename={self.filename}, status={self.indexing_status})>"

    @property
    def is_indexed(self) -> bool:
        """Check if document has been indexed in Milvus."""
        return self.indexing_status == "completed"

    @property
    def has_error(self) -> bool:
        """Check if indexing failed."""
        return self.indexing_status == "failed"

    @property
    def file_size_mb(self) -> float:
        """Get file size in megabytes."""
        return self.file_size / (1024 * 1024)

    def get_metadata(self, key: str, default: any = None) -> any:
        """
        Get a specific value from metadata.

        Args:
            key: The key to retrieve.
            default: Default value if key not found.

        Returns:
            The value from metadata or default.
        """
        if self.doc_metadata:
            return self.doc_metadata.get(key, default)
        return default

    def set_metadata(self, key: str, value: any) -> None:
        """
        Set a specific value in metadata.

        Args:
            key: The key to set.
            value: The value to set.
        """
        if not self.doc_metadata:
            self.doc_metadata = {}
        self.doc_metadata[key] = value

    def mark_as_indexing(self) -> None:
        """Mark document as being indexed."""
        self.indexing_status = "processing"

    def mark_as_indexed(self, index_name: str, num_pages: int) -> None:
        """
        Mark document as successfully indexed.

        Args:
            index_name: The Milvus collection name.
            num_pages: Number of pages indexed.
        """
        self.indexing_status = "completed"
        self.index_name = index_name
        self.num_pages = num_pages
        self.indexed_at = datetime.now()
        self.indexing_error = None

    def mark_as_failed(self, error_message: str) -> None:
        """
        Mark document indexing as failed.

        Args:
            error_message: The error that occurred.
        """
        self.indexing_status = "failed"
        self.indexing_error = error_message

    def to_summary_dict(self) -> dict:
        """
        Get a summary dictionary for API responses.

        Returns:
            Dictionary with key document information.
        """
        return {
            "id": str(self.id),
            "filename": self.filename,
            "doc_type": self.doc_type,
            "doc_category": self.doc_category,
            "file_size": self.file_size,
            "file_size_mb": round(self.file_size_mb, 2),
            "indexing_status": self.indexing_status,
            "num_pages": self.num_pages,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "metadata": self.doc_metadata,
        }
