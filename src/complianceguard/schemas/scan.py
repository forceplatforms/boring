"""
Pydantic schemas for scan job-related API endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from complianceguard.schemas.base import BaseSchema, TimestampMixin


class ScanTriggerRequest(BaseSchema):
    """Request to trigger a compliance scan."""

    framework: str = Field(
        default="SEC_CYBER", description="Compliance framework to use"
    )
    scan_type: str = Field(
        default="initial", description="Type of scan (initial, incremental, rescan)"
    )
    document_ids: Optional[list[UUID]] = Field(
        default=None, description="Specific document IDs to scan (empty = all)"
    )
    configuration: Optional[dict] = Field(
        default=None, description="Additional scan configuration"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "framework": "SEC_CYBER",
                "scan_type": "initial",
                "document_ids": [
                    "550e8400-e29b-41d4-a716-446655440000",
                    "551e8400-e29b-41d4-a716-446655440001",
                ],
                "configuration": {
                    "severity_threshold": "medium",
                    "confidence_threshold": 0.8,
                },
            }
        }


class ScanTriggerResponse(BaseSchema, TimestampMixin):
    """Response after triggering a scan."""

    id: UUID = Field(..., description="Scan job identifier")
    framework: str = Field(..., description="Compliance framework")
    scan_type: str = Field(..., description="Type of scan")
    status: str = Field(..., description="Current status")
    document_count: int = Field(..., description="Number of documents to scan")
    estimated_duration_seconds: int = Field(
        ..., description="Estimated completion time"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "750e8400-e29b-41d4-a716-446655440002",
                "framework": "SEC_CYBER",
                "scan_type": "initial",
                "status": "pending",
                "document_count": 12,
                "estimated_duration_seconds": 180,
                "created_at": "2025-11-07T17:00:00Z",
                "updated_at": "2025-11-07T17:00:00Z",
            }
        }


class ScanStatusResponse(BaseSchema, TimestampMixin):
    """Scan job status response."""

    id: UUID = Field(..., description="Scan job identifier")
    framework: str = Field(..., description="Compliance framework")
    scan_type: str = Field(..., description="Type of scan")
    status: str = Field(..., description="Current status")
    document_count: int = Field(..., description="Total documents")
    documents_processed: Optional[int] = Field(
        None, description="Documents processed so far"
    )
    started_at: Optional[datetime] = Field(None, description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    duration_seconds: Optional[int] = Field(None, description="Total duration")
    violations_found: Optional[int] = Field(None, description="Violations detected")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "750e8400-e29b-41d4-a716-446655440002",
                "framework": "SEC_CYBER",
                "scan_type": "initial",
                "status": "running",
                "document_count": 12,
                "documents_processed": 7,
                "started_at": "2025-11-07T17:00:05Z",
                "completed_at": None,
                "duration_seconds": None,
                "violations_found": 3,
                "error_message": None,
                "created_at": "2025-11-07T17:00:00Z",
                "updated_at": "2025-11-07T17:01:45Z",
            }
        }


class ScanResultsResponse(BaseSchema, TimestampMixin):
    """Detailed scan results after completion."""

    id: UUID = Field(..., description="Scan job identifier")
    framework: str = Field(..., description="Compliance framework")
    scan_type: str = Field(..., description="Type of scan")
    status: str = Field(..., description="Final status")
    document_count: int = Field(..., description="Total documents scanned")
    documents_processed: int = Field(..., description="Documents successfully processed")
    documents_failed: int = Field(..., description="Documents that failed")
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: datetime = Field(..., description="Completion timestamp")
    duration_seconds: int = Field(..., description="Total duration")
    violations_found: int = Field(..., description="Total violations detected")
    violation_ids: list[UUID] = Field(..., description="List of violation IDs")
    violations_by_severity: dict = Field(..., description="Violations grouped by severity")
    processing_stats: dict = Field(..., description="Processing statistics")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "750e8400-e29b-41d4-a716-446655440002",
                "framework": "SEC_CYBER",
                "scan_type": "initial",
                "status": "completed",
                "document_count": 12,
                "documents_processed": 12,
                "documents_failed": 0,
                "started_at": "2025-11-07T17:00:05Z",
                "completed_at": "2025-11-07T17:03:15Z",
                "duration_seconds": 190,
                "violations_found": 8,
                "violation_ids": [
                    "650e8400-e29b-41d4-a716-446655440001",
                    "651e8400-e29b-41d4-a716-446655440002",
                ],
                "violations_by_severity": {
                    "critical": 3,
                    "high": 4,
                    "medium": 1,
                    "low": 0,
                },
                "processing_stats": {
                    "total_tokens_used": 45000,
                    "total_cost_usd": 0.576,
                    "avg_processing_time_ms": 3200,
                },
                "created_at": "2025-11-07T17:00:00Z",
                "updated_at": "2025-11-07T17:03:15Z",
            }
        }


class ScanSummary(BaseSchema, TimestampMixin):
    """Summary view of a scan for list endpoints."""

    id: UUID = Field(..., description="Scan job identifier")
    framework: str = Field(..., description="Compliance framework")
    scan_type: str = Field(..., description="Type of scan")
    status: str = Field(..., description="Current status")
    document_count: int = Field(..., description="Total documents")
    violations_found: Optional[int] = Field(None, description="Violations detected")
    duration_seconds: Optional[int] = Field(None, description="Duration")
    triggered_by: Optional[str] = Field(None, description="User who triggered scan")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "750e8400-e29b-41d4-a716-446655440002",
                "framework": "SEC_CYBER",
                "scan_type": "initial",
                "status": "completed",
                "document_count": 12,
                "violations_found": 8,
                "duration_seconds": 190,
                "triggered_by": "analyst@company.com",
                "created_at": "2025-11-07T17:00:00Z",
                "updated_at": "2025-11-07T17:03:15Z",
            }
        }


class ScanListFilters(BaseSchema):
    """Filters for scan list endpoint."""

    status: Optional[str] = Field(None, description="Filter by status")
    framework: Optional[str] = Field(None, description="Filter by framework")
    scan_type: Optional[str] = Field(None, description="Filter by scan type")
    triggered_by: Optional[str] = Field(None, description="Filter by user")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "completed",
                "framework": "SEC_CYBER",
                "scan_type": "initial",
            }
        }


class ScanStatsResponse(BaseSchema):
    """Scan job statistics."""

    total_scans: int = Field(..., description="Total number of scans")
    by_status: dict = Field(..., description="Count by status")
    by_framework: dict = Field(..., description="Count by framework")
    total_violations_detected: int = Field(..., description="Total violations across all scans")
    avg_scan_duration_seconds: float = Field(..., description="Average scan duration")
    total_documents_scanned: int = Field(..., description="Total documents scanned")

    class Config:
        json_schema_extra = {
            "example": {
                "total_scans": 23,
                "by_status": {
                    "completed": 18,
                    "running": 2,
                    "failed": 2,
                    "pending": 1,
                },
                "by_framework": {
                    "SEC_CYBER": 20,
                    "SOX": 3,
                },
                "total_violations_detected": 67,
                "avg_scan_duration_seconds": 185.5,
                "total_documents_scanned": 276,
            }
        }
