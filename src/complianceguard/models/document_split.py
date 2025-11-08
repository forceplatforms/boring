"""
DocumentSplit model for storing document sections/splits.
Enables section-level analysis and navigation of document structure.
"""

from uuid import UUID

from sqlalchemy import ARRAY, Column, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship

from complianceguard.models.base import BaseModel


class DocumentSplit(BaseModel):
    """
    Document section/split from parsed document.

    Stores logical sections of a document (e.g., "Item 1C - Cybersecurity",
    "Risk Factors") with their content and associated chunks for structured
    navigation and section-level comparison.
    """

    __tablename__ = "document_splits"

    # Parent document
    document_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent document ID",
    )

    # Split classification
    class_ = Column(
        "class",  # 'class' is reserved keyword, use 'class_' in Python
        String(50),
        nullable=False,
        comment="Class of split: section, chapter, etc.",
    )
    identifier = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Section identifier: Item_1C, Risk_Factors, etc.",
    )

    # Pages covered
    pages = Column(
        ARRAY(Integer),
        nullable=False,
        comment="Array of page numbers covered by this split",
    )

    # Content
    markdown = Column(
        Text,
        nullable=True,
        comment="Combined markdown content of this section",
    )

    # Associated chunks
    chunk_ids = Column(
        ARRAY(String),
        nullable=True,
        comment="Array of chunk IDs that belong to this split",
    )

    # Order in document
    split_order = Column(
        Integer,
        nullable=False,
        comment="Order of split in document (0-indexed)",
    )

    # Relationship to parent document
    document = relationship("Document", back_populates="splits")

    # Composite indexes
    __table_args__ = (
        # Query splits by document and identifier
        Index("idx_splits_document_identifier", "document_id", "identifier"),
        # Query splits by identifier across documents
        Index("idx_splits_identifier", "identifier"),
        # GIN index for pages array
        Index("idx_splits_pages_gin", "pages", postgresql_using="gin"),
        # GIN index for chunk_ids array
        Index("idx_splits_chunks_gin", "chunk_ids", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<DocumentSplit(id={self.id}, identifier={self.identifier}, "
            f"pages={self.pages})>"
        )

    @property
    def page_count(self) -> int:
        """Get number of pages in this split."""
        return len(self.pages) if self.pages else 0

    @property
    def chunk_count(self) -> int:
        """Get number of chunks in this split."""
        return len(self.chunk_ids) if self.chunk_ids else 0

    @property
    def start_page(self) -> int | None:
        """Get first page number of this split."""
        return min(self.pages) if self.pages else None

    @property
    def end_page(self) -> int | None:
        """Get last page number of this split."""
        return max(self.pages) if self.pages else None

    def contains_page(self, page_number: int) -> bool:
        """Check if split contains specified page."""
        return page_number in (self.pages or [])

    def contains_chunk(self, chunk_id: str) -> bool:
        """Check if split contains specified chunk."""
        return chunk_id in (self.chunk_ids or [])

    def overlaps_with(self, other_split: "DocumentSplit") -> bool:
        """
        Check if this split overlaps with another split (shares pages).

        Args:
            other_split: Another DocumentSplit instance

        Returns:
            True if splits share any pages
        """
        if not self.pages or not other_split.pages:
            return False

        self_pages = set(self.pages)
        other_pages = set(other_split.pages)
        return bool(self_pages & other_pages)

    def get_page_range_str(self) -> str:
        """Get human-readable page range."""
        if not self.pages:
            return "No pages"

        if len(self.pages) == 1:
            return f"Page {self.pages[0]}"

        start = self.start_page
        end = self.end_page
        return f"Pages {start}-{end}"

    def to_dict(self) -> dict:
        """Convert split to dictionary for API responses."""
        return {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "class": self.class_,
            "identifier": self.identifier,
            "pages": self.pages,
            "page_count": self.page_count,
            "page_range": self.get_page_range_str(),
            "markdown": self.markdown,
            "chunk_ids": self.chunk_ids,
            "chunk_count": self.chunk_count,
            "split_order": self.split_order,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_summary_dict(self) -> dict:
        """Convert to summary dictionary (without full content)."""
        return {
            "id": str(self.id),
            "identifier": self.identifier,
            "class": self.class_,
            "pages": self.pages,
            "page_range": self.get_page_range_str(),
            "chunk_count": self.chunk_count,
            "split_order": self.split_order,
        }
