"""
Compliance Framework API endpoints.
Provides CRUD operations for managing compliance frameworks.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.crud import compliance_framework as framework_crud
from complianceguard.database import get_async_db
from complianceguard.models.compliance_framework import ComplianceFramework
from complianceguard.schemas.base import SuccessResponse
from complianceguard.schemas.compliance_framework import (
    ComplianceFrameworkCreate,
    ComplianceFrameworkListResponse,
    ComplianceFrameworkResponse,
    ComplianceFrameworkStatsResponse,
    ComplianceFrameworkUpdate,
    ComplianceTodosUpdate,
)

router = APIRouter(prefix="/frameworks", tags=["Compliance Frameworks"])


def _framework_to_response(framework: ComplianceFramework) -> ComplianceFrameworkResponse:
    """Convert ComplianceFramework model to response schema."""
    return ComplianceFrameworkResponse(
        id=framework.id,
        name=framework.name,
        description=framework.description,
        version=framework.version,
        framework_document_id=framework.framework_document_id,
        framework_index_name=framework.framework_index_name,
        compliance_todos=framework.compliance_todos or [],
        metadata=framework.framework_metadata or {},
        is_active=framework.is_active,
        created_by_email=framework.created_by_email,
        updated_by_email=framework.updated_by_email,
        todo_count=framework.todo_count,
        is_complete=framework.is_complete,
        created_at=framework.created_at,
        updated_at=framework.updated_at,
    )


@router.post(
    "/",
    response_model=ComplianceFrameworkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create compliance framework",
    description="Create a new compliance framework with requirements checklist",
)
async def create_framework(
    framework: ComplianceFrameworkCreate,
    db: AsyncSession = Depends(get_async_db),
) -> ComplianceFrameworkResponse:
    """
    Create a new compliance framework.

    Example request body:
    ```json
    {
        "name": "SOC 2 Type II",
        "description": "System and Organization Controls 2 Trust Service Criteria",
        "version": "2023.1",
        "framework_index_name": "framework_soc2",
        "compliance_todos": [
            "Verify access control policies are documented and enforced",
            "Confirm encryption standards meet AES-256 requirements"
        ],
        "metadata": {
            "category": "security",
            "jurisdiction": "US"
        },
        "is_active": true,
        "created_by_email": "admin@example.com"
    }
    ```
    """
    # Check if framework with same name already exists
    existing = await framework_crud.get_compliance_framework_by_name(db, framework.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Compliance framework with name '{framework.name}' already exists",
        )

    # Create framework
    created_framework = await framework_crud.create_compliance_framework(
        db=db,
        name=framework.name,
        framework_index_name=framework.framework_index_name,
        compliance_todos=framework.compliance_todos,
        description=framework.description,
        version=framework.version,
        framework_document_id=framework.framework_document_id,
        framework_metadata=framework.metadata,
        is_active=framework.is_active,
        created_by_email=framework.created_by_email,
    )

    return _framework_to_response(created_framework)


@router.get(
    "/",
    response_model=ComplianceFrameworkListResponse,
    summary="List compliance frameworks",
    description="Get a paginated list of compliance frameworks with optional filtering",
)
async def list_frameworks(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search in name and description"),
    db: AsyncSession = Depends(get_async_db),
) -> ComplianceFrameworkListResponse:
    """
    List compliance frameworks with pagination and filtering.

    Query parameters:
    - **skip**: Number of records to skip (for pagination)
    - **limit**: Maximum number of records to return (1-100)
    - **is_active**: Filter by active status (true/false)
    - **search**: Search query for name and description
    """
    frameworks, total = await framework_crud.list_compliance_frameworks(
        db=db,
        skip=skip,
        limit=limit,
        is_active=is_active,
        search_query=search,
    )

    items = [_framework_to_response(f) for f in frameworks]

    return ComplianceFrameworkListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=skip,
        has_more=(skip + len(items)) < total,
    )


@router.get(
    "/{framework_id}",
    response_model=ComplianceFrameworkResponse,
    summary="Get compliance framework",
    description="Get a specific compliance framework by ID",
)
async def get_framework(
    framework_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> ComplianceFrameworkResponse:
    """
    Get compliance framework by ID.

    Returns full framework details including all compliance todos and metadata.
    """
    framework = await framework_crud.get_compliance_framework(db, framework_id)
    if not framework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance framework {framework_id} not found",
        )

    return _framework_to_response(framework)


@router.put(
    "/{framework_id}",
    response_model=ComplianceFrameworkResponse,
    summary="Update compliance framework",
    description="Update compliance framework fields",
)
async def update_framework(
    framework_id: UUID,
    framework_update: ComplianceFrameworkUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> ComplianceFrameworkResponse:
    """
    Update compliance framework.

    Only provided fields will be updated. All fields are optional.
    """
    updated_framework = await framework_crud.update_compliance_framework(
        db=db,
        framework_id=framework_id,
        name=framework_update.name,
        description=framework_update.description,
        version=framework_update.version,
        framework_document_id=framework_update.framework_document_id,
        framework_index_name=framework_update.framework_index_name,
        compliance_todos=framework_update.compliance_todos,
        framework_metadata=framework_update.metadata,
        is_active=framework_update.is_active,
        updated_by_email=framework_update.updated_by_email,
    )

    if not updated_framework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance framework {framework_id} not found",
        )

    return _framework_to_response(updated_framework)


@router.patch(
    "/{framework_id}/todos",
    response_model=ComplianceFrameworkResponse,
    summary="Update compliance todos",
    description="Update just the compliance todos list for a framework",
)
async def update_todos(
    framework_id: UUID,
    todos_update: ComplianceTodosUpdate,
    db: AsyncSession = Depends(get_async_db),
) -> ComplianceFrameworkResponse:
    """
    Update just the compliance todos list.

    This is a convenience endpoint for updating only the requirements checklist.

    Example request body:
    ```json
    {
        "compliance_todos": [
            "New requirement 1",
            "New requirement 2"
        ],
        "updated_by_email": "admin@example.com"
    }
    ```
    """
    updated_framework = await framework_crud.update_compliance_todos(
        db=db,
        framework_id=framework_id,
        compliance_todos=todos_update.compliance_todos,
        updated_by_email=todos_update.updated_by_email,
    )

    if not updated_framework:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance framework {framework_id} not found",
        )

    return _framework_to_response(updated_framework)


@router.delete(
    "/{framework_id}",
    response_model=SuccessResponse,
    summary="Delete compliance framework",
    description="Delete a compliance framework by ID",
)
async def delete_framework(
    framework_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> SuccessResponse:
    """
    Delete compliance framework.

    **Warning**: This will permanently delete the framework and all associated data.
    This action cannot be undone.
    """
    success = await framework_crud.delete_compliance_framework(db, framework_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Compliance framework {framework_id} not found",
        )

    return SuccessResponse(
        success=True,
        message=f"Compliance framework {framework_id} deleted successfully",
    )


@router.get(
    "/stats/summary",
    response_model=ComplianceFrameworkStatsResponse,
    summary="Get framework statistics",
    description="Get summary statistics about compliance frameworks",
)
async def get_framework_stats(
    db: AsyncSession = Depends(get_async_db),
) -> ComplianceFrameworkStatsResponse:
    """
    Get compliance framework statistics.

    Returns counts of total, active, and inactive frameworks.
    """
    stats = await framework_crud.get_compliance_framework_stats(db)

    return ComplianceFrameworkStatsResponse(
        total_frameworks=stats["total_frameworks"],
        active_frameworks=stats["active_frameworks"],
        inactive_frameworks=stats["inactive_frameworks"],
    )
