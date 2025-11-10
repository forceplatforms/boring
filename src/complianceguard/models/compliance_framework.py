"""
Compliance Framework model for storing regulatory frameworks and their requirements.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import relationship

from complianceguard.models.base import BaseModel


class ComplianceFramework(BaseModel):
    """
    Compliance framework model storing regulatory frameworks and their requirements.

    A compliance framework represents a regulatory standard (e.g., SOC 2, HIPAA, GDPR)
    with associated requirements/todos that need to be checked against documents.

    Example:
        >>> framework = ComplianceFramework(
        ...     name="SOC 2 Type II",
        ...     description="System and Organization Controls 2 Trust Service Criteria",
        ...     version="2023.1",
        ...     framework_document_id=doc_id,
        ...     framework_index_name="framework_soc2",
        ...     compliance_todos=[
        ...         "Verify access control policies are documented",
        ...         "Confirm encryption standards meet requirements",
        ...     ],
        ...     is_active=True
        ... )
    """

    __tablename__ = "compliance_frameworks"

    # Basic information
    name = Column(String(200), unique=True, nullable=False, index=True)
    description = Column(Text)
    version = Column(String(50))

    # Document references
    framework_document_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=True,  # Optional if framework is just metadata
        index=True
    )

    # Milvus index for semantic search
    framework_index_name = Column(String(100), nullable=False, index=True)

    # Compliance requirements checklist
    compliance_todos = Column(
        JSONB,
        nullable=False,
        default=[],
        server_default="[]",
        comment="Array of compliance requirement strings to check"
    )

    # Additional metadata
    framework_metadata = Column(
        JSONB,
        nullable=False,
        default={},
        server_default="{}",
        comment="Additional framework metadata (category, jurisdiction, etc.)"
    )

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Audit fields
    created_by_email = Column(String(255))
    updated_by_email = Column(String(255))

    # Relationships
    framework_document = relationship(
        "Document",
        foreign_keys=[framework_document_id],
        backref="compliance_frameworks"
    )

    # Indexes
    __table_args__ = (
        # Composite index for active frameworks
        {"comment": "Compliance frameworks for regulatory standards"},
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<ComplianceFramework(name='{self.name}', version='{self.version}', is_active={self.is_active})>"

    @property
    def todo_count(self) -> int:
        """Number of compliance requirements to check."""
        if isinstance(self.compliance_todos, list):
            return len(self.compliance_todos)
        return 0

    @property
    def is_complete(self) -> bool:
        """Check if framework has all required fields."""
        return bool(
            self.name
            and self.framework_index_name
            and self.compliance_todos
            and len(self.compliance_todos) > 0
        )

    def add_todo(self, todo: str) -> None:
        """
        Add a compliance requirement to the checklist.

        Args:
            todo: Compliance requirement string
        """
        if not isinstance(self.compliance_todos, list):
            self.compliance_todos = []
        if todo not in self.compliance_todos:
            self.compliance_todos.append(todo)

    def remove_todo(self, todo: str) -> bool:
        """
        Remove a compliance requirement from the checklist.

        Args:
            todo: Compliance requirement string to remove

        Returns:
            True if removed, False if not found
        """
        if isinstance(self.compliance_todos, list) and todo in self.compliance_todos:
            self.compliance_todos.remove(todo)
            return True
        return False

    def get_metadata_value(self, key: str, default=None):
        """
        Get a value from the framework_metadata JSONB field.

        Args:
            key: Metadata key
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        if isinstance(self.framework_metadata, dict):
            return self.framework_metadata.get(key, default)
        return default

    def set_metadata_value(self, key: str, value) -> None:
        """
        Set a value in the framework_metadata JSONB field.

        Args:
            key: Metadata key
            value: Value to set
        """
        if not isinstance(self.framework_metadata, dict):
            self.framework_metadata = {}
        self.framework_metadata[key] = value
