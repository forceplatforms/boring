"""
Compliance scan API endpoints with database integration.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.crud import scan_job as scan_job_crud
from complianceguard.database import get_async_db
from complianceguard.models.scan_job import ScanJob
from complianceguard.schemas.base import PaginatedResponse, SuccessResponse
from complianceguard.schemas.scan import (
    ScanListFilters,
    ScanResultsResponse,
    ScanStatsResponse,
    ScanStatusResponse,
    ScanSummary,
    ScanTriggerRequest,
    ScanTriggerResponse,
)

router = APIRouter(prefix="/scans")


def _scan_to_trigger_response(scan: ScanJob) -> ScanTriggerResponse:
    """Convert ScanJob model to ScanTriggerResponse."""
    # Calculate estimated duration (15 seconds per document)
    estimated_duration = scan.document_count * 15

    return ScanTriggerResponse(
        id=scan.id,
        framework=scan.framework,
        scan_type=scan.scan_type,
        status=scan.status,
        document_count=scan.document_count,
        estimated_duration_seconds=estimated_duration,
        created_at=scan.created_at,
        updated_at=scan.updated_at,
    )


def _scan_to_status_response(scan: ScanJob) -> ScanStatusResponse:
    """Convert ScanJob model to ScanStatusResponse."""
    documents_processed = None
    if scan.results:
        documents_processed = scan.results.get("documents_processed")

    return ScanStatusResponse(
        id=scan.id,
        framework=scan.framework,
        scan_type=scan.scan_type,
        status=scan.status,
        document_count=scan.document_count,
        documents_processed=documents_processed,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        duration_seconds=scan.duration_seconds,
        violations_found=scan.violations_found,
        error_message=scan.error_message,
        created_at=scan.created_at,
        updated_at=scan.updated_at,
    )


def _scan_to_results_response(scan: ScanJob) -> ScanResultsResponse:
    """Convert ScanJob model to ScanResultsResponse."""
    documents_processed = scan.document_count
    documents_failed = 0
    violations_by_severity = {}
    processing_stats = {}

    if scan.results:
        documents_processed = scan.results.get("documents_processed", scan.document_count)
        documents_failed = scan.results.get("documents_failed", 0)
        violations_by_severity = {
            "critical": scan.results.get("critical_count", 0),
            "high": scan.results.get("high_count", 0),
            "medium": scan.results.get("medium_count", 0),
            "low": scan.results.get("low_count", 0),
        }
        if "processing_stats" in scan.results:
            processing_stats = scan.results["processing_stats"]

    # Convert violation_ids from strings to UUIDs if needed
    violation_ids = []
    if scan.results and "violation_ids" in scan.results:
        violation_ids = [
            UUID(vid) if isinstance(vid, str) else vid
            for vid in scan.results["violation_ids"]
        ]

    return ScanResultsResponse(
        id=scan.id,
        framework=scan.framework,
        scan_type=scan.scan_type,
        status=scan.status,
        document_count=scan.document_count,
        documents_processed=documents_processed,
        documents_failed=documents_failed,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        duration_seconds=scan.duration_seconds,
        violations_found=scan.violations_found,
        violation_ids=violation_ids,
        violations_by_severity=violations_by_severity,
        processing_stats=processing_stats,
        created_at=scan.created_at,
        updated_at=scan.updated_at,
    )


def _scan_to_summary(scan: ScanJob) -> ScanSummary:
    """Convert ScanJob model to ScanSummary."""
    return ScanSummary(
        id=scan.id,
        framework=scan.framework,
        scan_type=scan.scan_type,
        status=scan.status,
        document_count=scan.document_count,
        violations_found=scan.violations_found,
        duration_seconds=scan.duration_seconds,
        triggered_by=scan.triggered_by_email,
        created_at=scan.created_at,
        updated_at=scan.updated_at,
    )


@router.post(
    "/trigger",
    response_model=ScanTriggerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Scan",
    description="Trigger a compliance scan for documents",
    responses={
        201: {"description": "Scan triggered successfully"},
        400: {"description": "Invalid request or no documents ready"},
    },
)
async def trigger_scan(
    request: ScanTriggerRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Trigger a compliance scan.

    **Request Body:**
    - **framework**: Compliance framework (SEC_CYBER, SOX, etc.)
    - **scan_type**: Type of scan (initial, incremental, rescan, targeted)
    - **document_ids**: Specific documents to scan (optional, defaults to all)
    - **configuration**: Additional scan configuration (optional)

    The scan will analyze documents in the background and detect compliance violations.
    Use the `/scans/{id}/status` endpoint to check progress.

    **Estimated Duration:**
    - Small scan (1-10 docs): 30-60 seconds
    - Medium scan (10-50 docs): 2-5 minutes
    - Large scan (50+ docs): 5-15 minutes
    """
    # Create scan job in database
    scan = await scan_job_crud.create_scan_job(
        db=db,
        framework=request.framework,
        scan_type=request.scan_type,
        document_ids=request.document_ids or [],
        configuration=request.configuration or {},
        triggered_by_email="analyst@company.com",  # In production, get from auth context
        triggered_by_name="Analyst",
        trigger_source="api",
    )

    return _scan_to_trigger_response(scan)


@router.get(
    "/{scan_id}/status",
    response_model=ScanStatusResponse,
    summary="Get Scan Status",
    description="Check the status of a running or completed scan",
    responses={
        200: {"description": "Scan status retrieved"},
        404: {"description": "Scan not found"},
    },
)
async def get_scan_status(
    scan_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get the current status of a scan.

    Returns real-time progress information including:
    - Current status (pending, running, completed, failed)
    - Documents processed vs. total
    - Violations found so far
    - Start and completion times
    - Error messages if failed

    **Status Values:**
    - **pending**: Scan queued, waiting to start
    - **running**: Scan in progress
    - **completed**: Scan finished successfully
    - **failed**: Scan encountered errors
    - **cancelled**: Scan was cancelled by user
    """
    scan = await scan_job_crud.get_scan_job(db, scan_id)

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found",
        )

    return _scan_to_status_response(scan)


@router.get(
    "/{scan_id}/results",
    response_model=ScanResultsResponse,
    summary="Get Scan Results",
    description="Get detailed results of a completed scan",
    responses={
        200: {"description": "Scan results retrieved"},
        404: {"description": "Scan not found"},
        425: {"description": "Scan not yet completed"},
    },
)
async def get_scan_results(
    scan_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get detailed results of a completed scan.

    Only available for scans with status 'completed' or 'partial'.

    Returns:
    - Total violations found
    - Violations grouped by severity
    - List of violation IDs
    - Processing statistics (tokens used, cost, duration)
    - Document processing summary
    """
    scan = await scan_job_crud.get_scan_job(db, scan_id)

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found",
        )

    if scan.status not in ["completed", "partial"]:
        raise HTTPException(
            status_code=status.HTTP_425_TOO_EARLY,
            detail=f"Scan is still {scan.status}. Results not yet available.",
        )

    return _scan_to_results_response(scan)


@router.get(
    "",
    response_model=PaginatedResponse[ScanSummary],
    summary="List Scans",
    description="Get paginated list of scans with optional filters",
)
async def list_scans(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    status: Optional[str] = Query(None, description="Filter by status"),
    framework: Optional[str] = Query(None, description="Filter by framework"),
    scan_type: Optional[str] = Query(None, description="Filter by scan type"),
    triggered_by: Optional[str] = Query(None, description="Filter by user"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve a paginated list of scans.

    **Filters:**
    - status: pending, running, completed, failed, cancelled
    - framework: SEC_CYBER, SOX, GDPR, etc.
    - scan_type: initial, incremental, rescan, targeted
    - triggered_by: user email address

    **Pagination:**
    - limit: maximum items per page (1-100)
    - offset: number of items to skip
    """
    scans, total = await scan_job_crud.list_scan_jobs(
        db=db,
        skip=offset,
        limit=limit,
        framework=framework,
        status=status,
        scan_type=scan_type,
        triggered_by_email=triggered_by,
    )

    return PaginatedResponse(
        items=[_scan_to_summary(scan) for scan in scans],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.post(
    "/{scan_id}/cancel",
    response_model=SuccessResponse,
    summary="Cancel Scan",
    description="Cancel a running scan",
    responses={
        200: {"description": "Scan cancelled successfully"},
        404: {"description": "Scan not found"},
        400: {"description": "Scan cannot be cancelled (not running)"},
    },
)
async def cancel_scan(
    scan_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Cancel a running scan.

    Only scans with status 'pending' or 'running' can be cancelled.
    Completed or failed scans cannot be cancelled.

    The scan will be stopped and marked as 'cancelled' with partial results.
    """
    scan = await scan_job_crud.get_scan_job(db, scan_id)

    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan {scan_id} not found",
        )

    if scan.status not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Scan is {scan.status} and cannot be cancelled",
        )

    scan = await scan_job_crud.cancel_scan_job(db, scan_id)

    return SuccessResponse(
        success=True,
        message=f"Scan cancelled successfully",
        data={
            "scan_id": str(scan_id),
            "violations_found": scan.violations_found if scan else 0,
        },
    )


@router.get(
    "/stats/summary",
    response_model=ScanStatsResponse,
    summary="Scan Statistics",
    description="Get aggregated scan statistics",
)
async def get_scan_stats(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get aggregated statistics about all scans.

    Returns:
    - Total scan count
    - Count by status
    - Count by framework
    - Total violations detected
    - Average scan duration
    - Total documents scanned
    """
    stats = await scan_job_crud.get_scan_job_stats(db)

    # Calculate total violations and documents from all scans
    scans, _ = await scan_job_crud.list_scan_jobs(db, skip=0, limit=10000)

    total_violations = 0
    total_documents = 0

    for scan in scans:
        total_violations += scan.violations_found
        total_documents += scan.document_count

    return ScanStatsResponse(
        total_scans=stats["total"],
        by_status=stats["by_status"],
        by_framework=stats["by_framework"],
        total_violations_detected=total_violations,
        avg_scan_duration_seconds=round(stats["average_duration_seconds"], 1),
        total_documents_scanned=total_documents,
    )
