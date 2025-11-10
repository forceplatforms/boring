"""
Pydantic schemas for ComplianceFramework API endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field, field_validator

from complianceguard.schemas.base import BaseSchema, TimestampMixin


# Request Schemas

class ComplianceFrameworkCreate(BaseSchema):
    """Schema for creating a compliance framework."""

    name: str = Field(..., min_length=1, max_length=200, description="Framework name (e.g., 'SOC 2 Type II')")
    description: Optional[str] = Field(None, description="Framework description")
    version: Optional[str] = Field(None, max_length=50, description="Framework version (e.g., '2023.1')")
    framework_document_id: Optional[UUID] = Field(None, description="Reference to framework document in documents table")
    framework_index_name: str = Field(..., min_length=3, max_length=100, description="Milvus collection name for framework documents")
    compliance_todos: list[str] = Field(..., min_items=1, description="List of compliance requirements to check")
    metadata: dict = Field(default_factory=dict, description="Additional framework metadata")
    is_active: bool = Field(default=True, description="Whether framework is active")
    created_by_email: Optional[str] = Field(None, max_length=255, description="Email of creator")

    @field_validator("compliance_todos")
    @classmethod
    def validate_todos(cls, v):
        """Validate todos are not empty strings."""
        if not v:
            raise ValueError("compliance_todos must contain at least one requirement")
        for todo in v:
            if not todo or not todo.strip():
                raise ValueError("compliance_todos cannot contain empty strings")
        return [todo.strip() for todo in v]

    class Config:
        json_schema_extra = {
            "example": {
                "name": "SOC 2 Type II",
                "description": "System and Organization Controls 2 Trust Service Criteria",
                "version": "2023.1",
                "framework_index_name": "framework_soc2",
                "compliance_todos": [
                    "Verify access control policies are documented and enforced",
                    "Confirm encryption standards meet AES-256 requirements",
                    "Validate incident response procedures are in place"
                ],
                "metadata": {
                    "category": "security",
                    "jurisdiction": "US",
                    "applies_to": ["cloud_services", "data_processing"]
                },
                "is_active": True
            }
        }


class ComplianceFrameworkUpdate(BaseSchema):
    """Schema for updating a compliance framework."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    version: Optional[str] = Field(None, max_length=50)
    framework_document_id: Optional[UUID] = None
    framework_index_name: Optional[str] = Field(None, min_length=3, max_length=100)
    compliance_todos: Optional[list[str]] = None
    metadata: Optional[dict] = None
    is_active: Optional[bool] = None
    updated_by_email: Optional[str] = Field(None, max_length=255)

    @field_validator("compliance_todos")
    @classmethod
    def validate_todos(cls, v):
        """Validate todos are not empty strings."""
        if v is not None:
            if not v:
                raise ValueError("compliance_todos must contain at least one requirement if provided")
            for todo in v:
                if not todo or not todo.strip():
                    raise ValueError("compliance_todos cannot contain empty strings")
            return [todo.strip() for todo in v]
        return v


class ComplianceTodosUpdate(BaseSchema):
    """Schema for updating just the compliance todos list."""

    compliance_todos: list[str] = Field(..., min_items=1, description="Updated list of compliance requirements")
    updated_by_email: Optional[str] = Field(None, max_length=255)

    @field_validator("compliance_todos")
    @classmethod
    def validate_todos(cls, v):
        """Validate todos are not empty strings."""
        if not v:
            raise ValueError("compliance_todos must contain at least one requirement")
        for todo in v:
            if not todo or not todo.strip():
                raise ValueError("compliance_todos cannot contain empty strings")
        return [todo.strip() for todo in v]


# Response Schemas

class ComplianceFrameworkResponse(BaseSchema, TimestampMixin):
    """Schema for compliance framework response."""

    id: UUID
    name: str
    description: Optional[str]
    version: Optional[str]
    framework_document_id: Optional[UUID]
    framework_index_name: str
    compliance_todos: list[str]
    metadata: dict
    is_active: bool
    created_by_email: Optional[str]
    updated_by_email: Optional[str]

    # Computed fields
    todo_count: int = Field(..., description="Number of compliance requirements")
    is_complete: bool = Field(..., description="Whether framework has all required fields")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "SOC 2 Type II",
                "description": "System and Organization Controls 2 Trust Service Criteria",
                "version": "2023.1",
                "framework_document_id": "660e8400-e29b-41d4-a716-446655440000",
                "framework_index_name": "framework_soc2",
                "compliance_todos": [
                    "Verify access control policies are documented",
                    "Confirm encryption standards meet requirements"
                ],
                "metadata": {"category": "security", "jurisdiction": "US"},
                "is_active": True,
                "todo_count": 2,
                "is_complete": True,
                "created_by_email": "admin@example.com",
                "updated_by_email": None,
                "created_at": "2025-11-10T14:32:00Z",
                "updated_at": "2025-11-10T14:32:00Z"
            }
        }


class ComplianceFrameworkListResponse(BaseSchema):
    """Schema for paginated list of compliance frameworks."""

    items: list[ComplianceFrameworkResponse]
    total: int = Field(..., description="Total number of frameworks")
    limit: int
    offset: int
    has_more: bool = Field(..., description="Whether there are more results")

    class Config:
        json_schema_extra = {
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "name": "SOC 2 Type II",
                        "version": "2023.1",
                        "framework_index_name": "framework_soc2",
                        "is_active": True,
                        "todo_count": 15,
                        "is_complete": True
                    }
                ],
                "total": 5,
                "limit": 20,
                "offset": 0,
                "has_more": False
            }
        }


class ComplianceFrameworkStatsResponse(BaseSchema):
    """Schema for compliance framework statistics."""

    total_frameworks: int
    active_frameworks: int
    inactive_frameworks: int

    class Config:
        json_schema_extra = {
            "example": {
                "total_frameworks": 12,
                "active_frameworks": 10,
                "inactive_frameworks": 2
            }
        }
