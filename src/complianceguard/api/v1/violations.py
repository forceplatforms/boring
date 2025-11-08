"""
Violation management API endpoints with database integration.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.crud import violation as violation_crud
from complianceguard.database import get_async_db
from complianceguard.models.violation import Violation
from complianceguard.schemas.base import PaginatedResponse, SuccessResponse
from complianceguard.schemas.violation import (
    ViolationDetail,
    ViolationEvidence,
    ViolationRecommendation,
    ViolationStatsResponse,
    ViolationSummary,
    ViolationUpdateRequest,
)

router = APIRouter(prefix="/violations")


def _violation_to_summary(violation: Violation) -> ViolationSummary:
    """Convert Violation model to ViolationSummary."""
    return ViolationSummary(
        id=violation.id,
        severity=violation.severity,
        status=violation.status,
        violation_type=violation.violation_type,
        finding_summary=violation.finding_summary,
        rule_citation=violation.rule_citation,
        confidence_score=violation.confidence_score or 0.0,
        source_document_name=violation.source_document_data.get("file_name", "unknown"),
        target_document_name=violation.target_document_data.get("file_name", "unknown"),
        assigned_to=violation.assigned_to_email,
        created_at=violation.created_at,
        updated_at=violation.updated_at,
    )


def _violation_to_detail(violation: Violation) -> ViolationDetail:
    """Convert Violation model to ViolationDetail."""
    # Extract recommendation actions from the recommendations JSONB
    recommendations_list = []
    if violation.recommendations and "actions" in violation.recommendations:
        for action in violation.recommendations["actions"]:
            recommendations_list.append(
                ViolationRecommendation(
                    priority=action.get("priority", "medium"),
                    description=action.get("description", ""),
                    timeline=action.get("timeline", ""),
                    responsible_party=action.get("responsible_party", ""),
                )
            )

    # Get suggested language from recommendations
    suggested_language = None
    if violation.recommendations:
        suggested_language = violation.recommendations.get("suggested_language")

    # Get financial risk from recommendations
    financial_risk = None
    if violation.recommendations and "financial_risk" in violation.recommendations:
        financial_risk = violation.recommendations["financial_risk"]

    return ViolationDetail(
        id=violation.id,
        severity=violation.severity,
        status=violation.status,
        violation_type=violation.violation_type,
        finding_summary=violation.finding_summary,
        rule_citation=violation.rule_citation,
        confidence_score=violation.confidence_score or 0.0,
        source_document_name=violation.source_document_data.get("file_name", "unknown"),
        target_document_name=violation.target_document_data.get("file_name", "unknown"),
        assigned_to=violation.assigned_to_email,
        explanation=violation.explanation,
        evidence=ViolationEvidence(**violation.evidence) if violation.evidence else None,
        recommendations=recommendations_list,
        suggested_language=suggested_language,
        financial_risk=financial_risk,
        ai_metadata=violation.ai_metadata or {},
        source_document_id=violation.source_document_id,
        target_document_id=violation.target_document_id,
        framework=violation.framework,
        resolved_at=violation.resolved_at,
        resolution_notes=violation.resolution_notes,
        created_at=violation.created_at,
        updated_at=violation.updated_at,
    )


@router.get(
    "",
    response_model=PaginatedResponse[ViolationSummary],
    summary="List Violations",
    description="Get paginated list of violations with optional filters",
)
async def list_violations(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    status: Optional[str] = Query(None, description="Filter by status"),
    violation_type: Optional[str] = Query(None, description="Filter by type"),
    framework: Optional[str] = Query(None, description="Filter by framework"),
    assigned_to: Optional[str] = Query(None, description="Filter by assignee"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve a paginated list of violations.

    **Filters:**
    - severity: critical, high, medium, low
    - status: open, assigned, in_progress, remediated, false_positive
    - violation_type: material_omission, misleading_statement, delayed_disclosure, etc.
    - framework: SEC_CYBER, SOX, GDPR, etc.
    - assigned_to: user email address

    **Pagination:**
    - limit: maximum items per page (1-100)
    - offset: number of items to skip

    **Sorting:**
    Violations are sorted by severity (critical first) and creation date (newest first)
    """
    violations, total = await violation_crud.list_violations(
        db=db,
        skip=offset,
        limit=limit,
        framework=framework,
        severity=severity,
        status=status,
        violation_type=violation_type,
        assigned_to_email=assigned_to,
    )

    return PaginatedResponse(
        items=[_violation_to_summary(v) for v in violations],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/{violation_id}",
    response_model=ViolationDetail,
    summary="Get Violation",
    description="Get detailed violation information with full evidence",
    responses={
        200: {"description": "Violation details retrieved"},
        404: {"description": "Violation not found"},
    },
)
async def get_violation(
    violation_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve detailed information about a specific violation.

    Includes:
    - Complete finding explanation
    - Full evidence with source/target quotes
    - AI analysis metadata and confidence scores
    - Recommendations for remediation
    - Suggested compliant language
    - Financial risk estimates
    - Assignment and resolution status
    """
    violation = await violation_crud.get_violation(db, violation_id)

    if not violation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation {violation_id} not found",
        )

    return _violation_to_detail(violation)


@router.patch(
    "/{violation_id}",
    response_model=ViolationDetail,
    summary="Update Violation",
    description="Update violation status and assignment",
)
async def update_violation(
    violation_id: UUID,
    update_data: ViolationUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update violation status and assignment.

    Can update:
    - status: Change violation status (assigned, in_progress, remediated, false_positive)
    - assigned_to_email: Assign to a user
    - assigned_to_name: Assignee name
    - resolution_notes: Notes about how the violation was resolved

    **Status Workflow:**
    1. open → assigned (when assigned to someone)
    2. assigned → in_progress (when work begins)
    3. in_progress → remediated (when fixed)
    4. any → false_positive (if incorrectly flagged)
    """
    violation = await violation_crud.update_violation(
        db=db,
        violation_id=violation_id,
        status=update_data.status,
        assigned_to_email=update_data.assigned_to_email,
        assigned_to_name=update_data.assigned_to_name,
        resolution_notes=update_data.resolution_notes,
    )

    if not violation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation {violation_id} not found",
        )

    return _violation_to_detail(violation)


@router.post(
    "/{violation_id}/acknowledge",
    response_model=SuccessResponse,
    summary="Acknowledge Violation",
    description="Mark violation as acknowledged",
)
async def acknowledge_violation(
    violation_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Acknowledge a violation.

    This marks the violation as seen and acknowledged by the compliance team.
    The status will be updated to 'acknowledged' and a timestamp recorded.
    """
    # Use a default user for now - in production, this would come from auth context
    violation = await violation_crud.acknowledge_violation(
        db=db,
        violation_id=violation_id,
        acknowledged_by_email="compliance@company.com",
        acknowledged_by_name="Compliance Team",
    )

    if not violation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Violation {violation_id} not found",
        )

    return SuccessResponse(
        success=True,
        message="Violation acknowledged successfully",
        data={
            "violation_id": str(violation_id),
            "severity": violation.severity,
            "status": violation.status,
        },
    )


@router.get(
    "/stats/summary",
    response_model=ViolationStatsResponse,
    summary="Violation Statistics",
    description="Get aggregated violation statistics",
)
async def get_violation_stats(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get aggregated statistics about all violations.

    Returns:
    - Total violation count
    - Count by severity level
    - Count by status
    - Count by violation type
    - Total financial risk estimates
    - Average AI confidence score
    """
    stats = await violation_crud.get_violation_stats(db)

    # Calculate total financial risk and average confidence from all violations
    violations, _ = await violation_crud.list_violations(db, skip=0, limit=10000)

    total_min_risk = 0
    total_max_risk = 0
    confidence_scores = []
    by_type = {}

    for v in violations:
        # Count by type
        by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1

        # Sum financial risk
        if v.recommendations and "financial_risk" in v.recommendations:
            risk = v.recommendations["financial_risk"]
            total_min_risk += risk.get("estimated_penalty_min", 0)
            total_max_risk += risk.get("estimated_penalty_max", 0)

        # Collect confidence scores
        if v.confidence_score:
            confidence_scores.append(v.confidence_score)

    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

    return ViolationStatsResponse(
        total_violations=stats["total"],
        by_severity=stats["by_severity"],
        by_status=stats["by_status"],
        by_type=by_type,
        total_financial_risk={
            "min": total_min_risk,
            "max": total_max_risk,
            "currency": "USD",
        },
        avg_confidence_score=round(avg_confidence, 2),
    )
