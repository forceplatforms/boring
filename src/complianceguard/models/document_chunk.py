"""
DocumentChunk model for storing individual content chunks from parsed documents.
Enables chunk-level queries, spatial searches, and precise evidence linking.
"""

from enum import Enum
from uuid import UUID

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from complianceguard.models.base import BaseModel


class ChunkType(str, Enum):
    """Types of content chunks identified by Landing AI."""

    TEXT = "text"
    TABLE = "table"
    FIGURE = "figure"
    FORM = "form"
    TITLE = "title"
    KEY_VALUE = "keyValue"
    LOGO = "logo"
    CARD = "card"
    ATTESTATION = "attestation"
    SCAN_CODE = "scanCode"
    MARGINALIA = "marginalia"
    PAGE_HEADER = "pageHeader"
    PAGE_FOOTER = "pageFooter"
    PAGE_NUMBER = "pageNumber"
    TABLE_CELL = "tableCell"
    OTHER = "other"


class DocumentChunk(BaseModel):
    """
    Individual content chunk from a parsed document.

    Stores each piece of content (text block, table, figure, etc.) with its
    type, position, and spatial coordinates for precise evidence linking.
    """

    __tablename__ = "document_chunks"

    # Parent document
    document_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent document ID",
    )

    # Chunk identification
    chunk_id = Column(
        String(100),
        unique=True,
        nullable=False,
        comment="Unique chunk ID from Landing AI (e.g., 'chunk-abc-123')",
    )
    chunk_type = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Type of chunk: text, table, figure, form, etc.",
    )
    chunk_order = Column(
        Integer,
        nullable=False,
        comment="Order of chunk in original document (0-indexed)",
    )

    # Content
    content = Column(
        Text,
        nullable=False,
        comment="Markdown content of this chunk",
    )

    # Spatial information
    page_number = Column(
        Integer,
        nullable=False,
        index=True,
        comment="Page number where this chunk appears (1-indexed)",
    )
    bounding_box = Column(
        JSONB,
        nullable=False,
        comment="""
        Bounding box coordinates in pixels:
        {
            "left": 100,
            "top": 200,
            "right": 500,
            "bottom": 300
        }
        """,
    )

    # Section/Split association
    split_identifier = Column(
        String(100),
        nullable=True,
        index=True,
        comment="Identifier of the split/section this chunk belongs to",
    )

    # Relationship to parent document
    document = relationship("Document", back_populates="chunks")

    # Composite indexes for common queries
    __table_args__ = (
        # Query chunks by document and type
        Index("idx_chunks_document_type", "document_id", "chunk_type"),
        # Query chunks by document and page
        Index("idx_chunks_document_page", "document_id", "page_number"),
        # Query chunks by document and split
        Index("idx_chunks_document_split", "document_id", "split_identifier"),
        # Query chunks by type and page (cross-document)
        Index("idx_chunks_type_page", "chunk_type", "page_number"),
        # GIN index for bounding box queries
        Index("idx_chunks_bbox_gin", "bounding_box", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<DocumentChunk(id={self.id}, chunk_id={self.chunk_id}, "
            f"type={self.chunk_type}, page={self.page_number})>"
        )

    @property
    def bbox_dict(self) -> dict:
        """Get bounding box as dictionary."""
        return self.bounding_box or {}

    @property
    def bbox_coordinates(self) -> tuple[int, int, int, int]:
        """Get bounding box coordinates as tuple (left, top, right, bottom)."""
        bbox = self.bbox_dict
        return (
            bbox.get("left", 0),
            bbox.get("top", 0),
            bbox.get("right", 0),
            bbox.get("bottom", 0),
        )

    @property
    def bbox_width(self) -> int:
        """Calculate bounding box width."""
        left, _, right, _ = self.bbox_coordinates
        return right - left

    @property
    def bbox_height(self) -> int:
        """Calculate bounding box height."""
        _, top, _, bottom = self.bbox_coordinates
        return bottom - top

    @property
    def bbox_area(self) -> int:
        """Calculate bounding box area in square pixels."""
        return self.bbox_width * self.bbox_height

    def is_on_page(self, page_number: int) -> bool:
        """Check if chunk is on specified page."""
        return self.page_number == page_number

    def is_type(self, chunk_type: str) -> bool:
        """Check if chunk is of specified type."""
        return self.chunk_type == chunk_type

    def overlaps_with(self, other_bbox: dict) -> bool:
        """
        Check if this chunk's bounding box overlaps with another.

        Args:
            other_bbox: Dictionary with left, top, right, bottom keys

        Returns:
            True if bounding boxes overlap
        """
        left1, top1, right1, bottom1 = self.bbox_coordinates
        left2 = other_bbox.get("left", 0)
        top2 = other_bbox.get("top", 0)
        right2 = other_bbox.get("right", 0)
        bottom2 = other_bbox.get("bottom", 0)

        # Check if rectangles overlap
        return not (
            right1 < left2 or  # bbox1 is left of bbox2
            left1 > right2 or  # bbox1 is right of bbox2
            bottom1 < top2 or  # bbox1 is above bbox2
            top1 > bottom2  # bbox1 is below bbox2
        )

    def to_dict(self) -> dict:
        """Convert chunk to dictionary for API responses."""
        return {
            "id": str(self.id),
            "chunk_id": self.chunk_id,
            "chunk_type": self.chunk_type,
            "chunk_order": self.chunk_order,
            "content": self.content,
            "page_number": self.page_number,
            "bounding_box": self.bounding_box,
            "split_identifier": self.split_identifier,
            "document_id": str(self.document_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
