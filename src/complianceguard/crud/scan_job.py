"""
CRUD operations for ScanJob model.
Handles database operations for compliance scan job management.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.models.scan_job import ScanJob


async def create_scan_job(
    db: AsyncSession,
    framework: str,
    scan_type: str,
    document_ids: list[UUID],
    configuration: dict,
    triggered_by_email: Optional[str] = None,
    triggered_by_name: Optional[str] = None,
    trigger_source: Optional[str] = "api",
) -> ScanJob:
    """
    Create a new scan job.

    Args:
        db: Database session
        framework: Compliance framework
        scan_type: Type of scan
        document_ids: List of document UUIDs to scan
        configuration: Scan configuration (JSONB)
        triggered_by_email: Triggerer email
        triggered_by_name: Triggerer name
        trigger_source: Source of trigger

    Returns:
        Created scan job instance
    """
    scan_job = ScanJob(
        id=uuid4(),
        framework=framework,
        scan_type=scan_type,
        document_ids=document_ids,
        status="pending",
        results={},
        configuration=configuration,
        triggered_by_email=triggered_by_email,
        triggered_by_name=triggered_by_name,
        trigger_source=trigger_source,
    )

    db.add(scan_job)
    await db.commit()
    await db.refresh(scan_job)

    return scan_job


async def get_scan_job(db: AsyncSession, scan_job_id: UUID) -> Optional[ScanJob]:
    """
    Get scan job by ID.

    Args:
        db: Database session
        scan_job_id: Scan job UUID

    Returns:
        Scan job instance or None if not found
    """
    result = await db.execute(select(ScanJob).where(ScanJob.id == scan_job_id))
    return result.scalar_one_or_none()


async def list_scan_jobs(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    framework: Optional[str] = None,
    status: Optional[str] = None,
    scan_type: Optional[str] = None,
    triggered_by_email: Optional[str] = None,
) -> tuple[list[ScanJob], int]:
    """
    List scan jobs with filtering and pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        framework: Filter by framework
        status: Filter by status
        scan_type: Filter by scan type
        triggered_by_email: Filter by triggerer email

    Returns:
        Tuple of (list of scan jobs, total count)
    """
    # Build query
    query = select(ScanJob)

    # Apply filters
    if framework:
        query = query.where(ScanJob.framework == framework)
    if status:
        query = query.where(ScanJob.status == status)
    if scan_type:
        query = query.where(ScanJob.scan_type == scan_type)
    if triggered_by_email:
        query = query.where(ScanJob.triggered_by_email == triggered_by_email)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination and ordering
    query = query.order_by(ScanJob.created_at.desc()).offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    scan_jobs = list(result.scalars().all())

    return scan_jobs, total


async def update_scan_job_status(
    db: AsyncSession,
    scan_job_id: UUID,
    status: str,
    results: Optional[dict] = None,
    error_message: Optional[str] = None,
    error_details: Optional[dict] = None,
) -> Optional[ScanJob]:
    """
    Update scan job status and results.

    Args:
        db: Database session
        scan_job_id: Scan job UUID
        status: New status
        results: Optional scan results
        error_message: Optional error message
        error_details: Optional error details

    Returns:
        Updated scan job or None if not found
    """
    scan_job = await get_scan_job(db, scan_job_id)
    if not scan_job:
        return None

    scan_job.status = status

    if status == "running" and not scan_job.started_at:
        scan_job.started_at = datetime.now(timezone.utc)

    if status in ["completed", "failed", "cancelled"]:
        scan_job.completed_at = datetime.now(timezone.utc)
        if scan_job.started_at:
            duration = (scan_job.completed_at - scan_job.started_at).total_seconds()
            scan_job.duration_seconds = int(duration)

    if results is not None:
        scan_job.results = results

    if error_message is not None:
        scan_job.error_message = error_message

    if error_details is not None:
        scan_job.error_details = error_details

    scan_job.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(scan_job)

    return scan_job


async def cancel_scan_job(db: AsyncSession, scan_job_id: UUID) -> Optional[ScanJob]:
    """
    Cancel a scan job.

    Args:
        db: Database session
        scan_job_id: Scan job UUID

    Returns:
        Updated scan job or None if not found
    """
    return await update_scan_job_status(
        db, scan_job_id, status="cancelled", error_message="Scan cancelled by user"
    )


async def delete_scan_job(db: AsyncSession, scan_job_id: UUID) -> bool:
    """
    Delete scan job by ID.

    Args:
        db: Database session
        scan_job_id: Scan job UUID

    Returns:
        True if deleted, False if not found
    """
    scan_job = await get_scan_job(db, scan_job_id)
    if not scan_job:
        return False

    await db.delete(scan_job)
    await db.commit()

    return True


async def get_scan_job_stats(db: AsyncSession) -> dict:
    """
    Get scan job statistics.

    Args:
        db: Database session

    Returns:
        Dictionary with statistics
    """
    # Total scans
    total_result = await db.execute(select(func.count(ScanJob.id)))
    total = total_result.scalar_one()

    # By status
    status_result = await db.execute(
        select(ScanJob.status, func.count(ScanJob.id))
        .group_by(ScanJob.status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    # By framework
    framework_result = await db.execute(
        select(ScanJob.framework, func.count(ScanJob.id))
        .group_by(ScanJob.framework)
    )
    by_framework = {row[0]: row[1] for row in framework_result.all()}

    # Average duration
    avg_duration_result = await db.execute(
        select(func.avg(ScanJob.duration_seconds)).where(
            ScanJob.duration_seconds.isnot(None)
        )
    )
    avg_duration = avg_duration_result.scalar_one() or 0

    return {
        "total": total,
        "by_status": by_status,
        "by_framework": by_framework,
        "average_duration_seconds": float(avg_duration),
    }
