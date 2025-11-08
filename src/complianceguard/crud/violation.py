"""
CRUD operations for Violation model.
Handles database operations for compliance violation management.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.models.violation import Violation


async def create_violation(
    db: AsyncSession,
    source_document_id: UUID,
    source_document_data: dict,
    target_document_id: UUID,
    target_document_data: dict,
    framework: str,
    rule_citation: str,
    severity: str,
    violation_type: str,
    finding_summary: str,
    explanation: str,
    evidence: dict,
    ai_metadata: dict,
    recommendations: dict,
    status: str = "open",
    assigned_to_email: Optional[str] = None,
    assigned_to_name: Optional[str] = None,
) -> Violation:
    """
    Create a new violation.

    Args:
        db: Database session
        source_document_id: Source document UUID
        source_document_data: Denormalized source document data
        target_document_id: Target document UUID
        target_document_data: Denormalized target document data
        framework: Compliance framework
        rule_citation: Rule citation
        severity: Severity level
        violation_type: Type of violation
        finding_summary: Summary of finding
        explanation: Detailed explanation
        evidence: Evidence data (JSONB)
        ai_metadata: AI processing metadata (JSONB)
        recommendations: Recommendations (JSONB)
        status: Violation status
        assigned_to_email: Assigned user email
        assigned_to_name: Assigned user name

    Returns:
        Created violation instance
    """
    violation = Violation(
        id=uuid4(),
        source_document_id=source_document_id,
        source_document_data=source_document_data,
        target_document_id=target_document_id,
        target_document_data=target_document_data,
        framework=framework,
        rule_citation=rule_citation,
        severity=severity,
        violation_type=violation_type,
        finding_summary=finding_summary,
        explanation=explanation,
        evidence=evidence,
        ai_metadata=ai_metadata,
        recommendations=recommendations,
        status=status,
        assigned_to_email=assigned_to_email,
        assigned_to_name=assigned_to_name,
    )

    db.add(violation)
    await db.commit()
    await db.refresh(violation)

    return violation


async def get_violation(db: AsyncSession, violation_id: UUID) -> Optional[Violation]:
    """
    Get violation by ID.

    Args:
        db: Database session
        violation_id: Violation UUID

    Returns:
        Violation instance or None if not found
    """
    result = await db.execute(select(Violation).where(Violation.id == violation_id))
    return result.scalar_one_or_none()


async def list_violations(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    framework: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    violation_type: Optional[str] = None,
    assigned_to_email: Optional[str] = None,
    source_document_id: Optional[UUID] = None,
    target_document_id: Optional[UUID] = None,
) -> tuple[list[Violation], int]:
    """
    List violations with filtering and pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        framework: Filter by framework
        severity: Filter by severity
        status: Filter by status
        violation_type: Filter by violation type
        assigned_to_email: Filter by assignee email
        source_document_id: Filter by source document
        target_document_id: Filter by target document

    Returns:
        Tuple of (list of violations, total count)
    """
    # Build query
    query = select(Violation)

    # Apply filters
    if framework:
        query = query.where(Violation.framework == framework)
    if severity:
        query = query.where(Violation.severity == severity)
    if status:
        query = query.where(Violation.status == status)
    if violation_type:
        query = query.where(Violation.violation_type == violation_type)
    if assigned_to_email:
        query = query.where(Violation.assigned_to_email == assigned_to_email)
    if source_document_id:
        query = query.where(Violation.source_document_id == source_document_id)
    if target_document_id:
        query = query.where(Violation.target_document_id == target_document_id)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination and ordering
    query = query.order_by(Violation.created_at.desc()).offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    violations = list(result.scalars().all())

    return violations, total


async def update_violation(
    db: AsyncSession,
    violation_id: UUID,
    status: Optional[str] = None,
    assigned_to_email: Optional[str] = None,
    assigned_to_name: Optional[str] = None,
    resolution_notes: Optional[str] = None,
) -> Optional[Violation]:
    """
    Update violation fields.

    Args:
        db: Database session
        violation_id: Violation UUID
        status: Optional new status
        assigned_to_email: Optional assignee email
        assigned_to_name: Optional assignee name
        resolution_notes: Optional resolution notes

    Returns:
        Updated violation or None if not found
    """
    violation = await get_violation(db, violation_id)
    if not violation:
        return None

    # Update fields if provided
    if status is not None:
        violation.status = status
        if status in ["resolved", "closed"]:
            violation.resolved_at = datetime.utcnow()
    if assigned_to_email is not None:
        violation.assigned_to_email = assigned_to_email
    if assigned_to_name is not None:
        violation.assigned_to_name = assigned_to_name
    if resolution_notes is not None:
        violation.resolution_notes = resolution_notes

    violation.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(violation)

    return violation


async def acknowledge_violation(
    db: AsyncSession,
    violation_id: UUID,
    acknowledged_by_email: str,
    acknowledged_by_name: str,
) -> Optional[Violation]:
    """
    Acknowledge a violation.

    Args:
        db: Database session
        violation_id: Violation UUID
        acknowledged_by_email: Acknowledger email
        acknowledged_by_name: Acknowledger name

    Returns:
        Updated violation or None if not found
    """
    violation = await get_violation(db, violation_id)
    if not violation:
        return None

    violation.status = "acknowledged"
    violation.assigned_to_email = acknowledged_by_email
    violation.assigned_to_name = acknowledged_by_name
    violation.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(violation)

    return violation


async def delete_violation(db: AsyncSession, violation_id: UUID) -> bool:
    """
    Delete violation by ID.

    Args:
        db: Database session
        violation_id: Violation UUID

    Returns:
        True if deleted, False if not found
    """
    violation = await get_violation(db, violation_id)
    if not violation:
        return False

    await db.delete(violation)
    await db.commit()

    return True


async def get_violation_stats(db: AsyncSession) -> dict:
    """
    Get violation statistics.

    Args:
        db: Database session

    Returns:
        Dictionary with statistics
    """
    # Total violations
    total_result = await db.execute(select(func.count(Violation.id)))
    total = total_result.scalar_one()

    # By severity
    severity_result = await db.execute(
        select(Violation.severity, func.count(Violation.id))
        .group_by(Violation.severity)
    )
    by_severity = {row[0]: row[1] for row in severity_result.all()}

    # By status
    status_result = await db.execute(
        select(Violation.status, func.count(Violation.id))
        .group_by(Violation.status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    # By framework
    framework_result = await db.execute(
        select(Violation.framework, func.count(Violation.id))
        .group_by(Violation.framework)
    )
    by_framework = {row[0]: row[1] for row in framework_result.all()}

    return {
        "total": total,
        "by_severity": by_severity,
        "by_status": by_status,
        "by_framework": by_framework,
    }
