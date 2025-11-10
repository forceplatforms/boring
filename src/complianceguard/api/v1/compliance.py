"""
Compliance Check API endpoints.
Triggers and manages compliance analysis jobs.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.crud import scan_job as scan_job_crud
from complianceguard.database import get_async_db
from complianceguard.services.compliance_analyzer import analyze_compliance

router = APIRouter(prefix="/compliance", tags=["Compliance Analysis"])


class ComplianceCheckRequest(BaseModel):
    """Request to run compliance check."""

    framework_id: UUID = Field(..., description="UUID of the compliance framework to use")
    document_ids: list[UUID] = Field(
        ..., min_items=1, description="List of document UUIDs to check against framework"
    )
    triggered_by_email: Optional[str] = Field(None, description="Email of user triggering the scan")
    triggered_by_name: Optional[str] = Field(None, description="Name of user triggering the scan")

    class Config:
        json_schema_extra = {
            "example": {
                "framework_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_ids": [
                    "660e8400-e29b-41d4-a716-446655440001",
                    "660e8400-e29b-41d4-a716-446655440002",
                ],
                "triggered_by_email": "user@example.com",
                "triggered_by_name": "John Doe",
            }
        }


class ComplianceCheckResponse(BaseModel):
    """Response from compliance check request."""

    scan_job_id: UUID = Field(..., description="UUID of the created scan job")
    message: str = Field(..., description="Status message")
    framework_id: UUID = Field(..., description="UUID of the framework being used")
    document_count: int = Field(..., description="Number of documents being analyzed")

    class Config:
        json_schema_extra = {
            "example": {
                "scan_job_id": "770e8400-e29b-41d4-a716-446655440000",
                "message": "Compliance check started successfully",
                "framework_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_count": 2,
            }
        }


class ScanJobStatusResponse(BaseModel):
    """Scan job status response."""

    id: UUID
    framework: str
    scan_type: str
    status: str
    document_count: int
    violations_found: int
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_seconds: Optional[int]
    error_message: Optional[str]
    results: dict
    triggered_by: Optional[str]
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440000",
                "framework": "SOC 2 Type II",
                "scan_type": "targeted",
                "status": "completed",
                "document_count": 2,
                "violations_found": 3,
                "started_at": "2025-11-10T14:32:00Z",
                "completed_at": "2025-11-10T14:35:00Z",
                "duration_seconds": 180,
                "error_message": None,
                "results": {
                    "violations_found": 3,
                    "documents_processed": 2,
                    "documents_failed": 0,
                },
                "triggered_by": "user@example.com",
                "created_at": "2025-11-10T14:32:00Z",
            }
        }


@router.post(
    "/check",
    response_model=ComplianceCheckResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run compliance check",
    description="Start a compliance analysis job to check documents against a framework",
)
async def run_compliance_check(
    request: ComplianceCheckRequest,
    db: AsyncSession = Depends(get_async_db),
) -> ComplianceCheckResponse:
    """
    Run compliance check for documents against a framework.

    This endpoint:
    1. Creates a scan job to track the analysis
    2. Asynchronously analyzes each compliance requirement in the framework
    3. Compares user documents against framework documents
    4. Creates violation records for non-compliant findings

    **Process**:
    - For each compliance todo in the framework:
      - Queries both framework and user document indexes semantically
      - Extracts text from top matching pages
      - Analyzes compliance using Gemini AI
      - Creates violation if non-compliant

    **Returns**: Scan job ID to track progress

    **Example request body**:
    ```json
    {
        "framework_id": "550e8400-e29b-41d4-a716-446655440000",
        "document_ids": [
            "660e8400-e29b-41d4-a716-446655440001"
        ],
        "triggered_by_email": "user@example.com"
    }
    ```

    Use the `/compliance/status/{scan_job_id}` endpoint to check progress.
    """
    try:
        # Run compliance analysis (this is async but returns immediately with a job ID)
        scan_job_id = await analyze_compliance(
            db=db,
            framework_id=request.framework_id,
            document_ids=request.document_ids,
            triggered_by_email=request.triggered_by_email,
            triggered_by_name=request.triggered_by_name,
        )

        return ComplianceCheckResponse(
            scan_job_id=scan_job_id,
            message="Compliance check started successfully",
            framework_id=request.framework_id,
            document_count=len(request.document_ids),
        )

    except ValueError as e:
        # Framework not found or inactive
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        # Other errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start compliance check: {str(e)}",
        )


@router.get(
    "/status/{scan_job_id}",
    response_model=ScanJobStatusResponse,
    summary="Get compliance check status",
    description="Get the status and results of a compliance check scan job",
)
async def get_compliance_status(
    scan_job_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> ScanJobStatusResponse:
    """
    Get compliance check status.

    Use this endpoint to:
    - Check if the scan is still running
    - Get the number of violations found
    - Retrieve error messages if the scan failed
    - View detailed results once completed

    **Scan statuses**:
    - `pending`: Job created but not started
    - `running`: Analysis in progress
    - `completed`: Successfully completed
    - `failed`: Failed with errors
    - `partial`: Partially completed (some documents failed)
    """
    scan_job = await scan_job_crud.get_scan_job(db, scan_job_id)
    if not scan_job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan job {scan_job_id} not found",
        )

    return ScanJobStatusResponse(
        id=scan_job.id,
        framework=scan_job.framework,
        scan_type=scan_job.scan_type,
        status=scan_job.status,
        document_count=scan_job.document_count,
        violations_found=scan_job.violations_found,
        started_at=scan_job.started_at.isoformat() if scan_job.started_at else None,
        completed_at=scan_job.completed_at.isoformat() if scan_job.completed_at else None,
        duration_seconds=scan_job.duration_seconds,
        error_message=scan_job.error_message,
        results=scan_job.results or {},
        triggered_by=scan_job.triggered_by_email,
        created_at=scan_job.created_at.isoformat() if scan_job.created_at else None,
    )


@router.get(
    "/jobs",
    response_model=list[ScanJobStatusResponse],
    summary="List compliance check jobs",
    description="Get a list of compliance check scan jobs with optional filtering",
)
async def list_compliance_jobs(
    framework: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_async_db),
) -> list[ScanJobStatusResponse]:
    """
    List compliance check jobs.

    **Query parameters**:
    - `framework`: Filter by framework name
    - `status`: Filter by status (pending, running, completed, failed, partial)
    - `limit`: Maximum number of jobs to return (default: 20)
    """
    scan_jobs, _ = await scan_job_crud.list_scan_jobs(
        db=db,
        framework=framework,
        status=status,
        limit=limit,
    )

    return [
        ScanJobStatusResponse(
            id=job.id,
            framework=job.framework,
            scan_type=job.scan_type,
            status=job.status,
            document_count=job.document_count,
            violations_found=job.violations_found,
            started_at=job.started_at.isoformat() if job.started_at else None,
            completed_at=job.completed_at.isoformat() if job.completed_at else None,
            duration_seconds=job.duration_seconds,
            error_message=job.error_message,
            results=job.results or {},
            triggered_by=job.triggered_by_email,
            created_at=job.created_at.isoformat() if job.created_at else None,
        )
        for job in scan_jobs
    ]
