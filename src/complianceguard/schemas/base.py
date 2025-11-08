"""
Base Pydantic schemas for common patterns across the API.
"""

from datetime import datetime
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# Type variable for generic responses
T = TypeVar("T")


class BaseSchema(BaseModel):
    """Base schema with common configuration."""

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
    )


class TimestampMixin(BaseModel):
    """Mixin for models with timestamps."""

    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class PaginationParams(BaseModel):
    """Common pagination parameters."""

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of items to return",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip",
    )


class PaginatedResponse(BaseSchema, Generic[T]):
    """Generic paginated response wrapper."""

    items: List[T] = Field(..., description="List of items")
    total: int = Field(..., description="Total number of items")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Number of items skipped")
    has_more: bool = Field(..., description="Whether there are more items")


class SuccessResponse(BaseSchema):
    """Generic success response."""

    success: bool = Field(default=True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[dict] = Field(default=None, description="Additional data")


class ErrorResponse(BaseSchema):
    """Generic error response."""

    success: bool = Field(default=False, description="Operation success status")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(default=None, description="Additional error details")


class HealthCheckResponse(BaseSchema):
    """Health check response."""

    status: str = Field(..., description="Overall health status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Check timestamp")
    services: dict = Field(..., description="Service statuses")
