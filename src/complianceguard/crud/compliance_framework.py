"""
CRUD operations for ComplianceFramework model.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from complianceguard.models.compliance_framework import ComplianceFramework

logger = logging.getLogger(__name__)


async def create_compliance_framework(
    db: AsyncSession,
    name: str,
    framework_index_name: str,
    compliance_todos: list[str],
    description: Optional[str] = None,
    version: Optional[str] = None,
    framework_document_id: Optional[UUID] = None,
    framework_metadata: Optional[dict] = None,
    is_active: bool = True,
    created_by_email: Optional[str] = None,
) -> ComplianceFramework:
    """
    Create a new compliance framework.

    Args:
        db: Database session
        name: Framework name (e.g., "SOC 2 Type II")
        framework_index_name: Milvus collection name for framework documents
        compliance_todos: List of compliance requirement strings
        description: Optional framework description
        version: Optional version string
        framework_document_id: Optional reference to framework document
        framework_metadata: Optional additional metadata
        is_active: Whether framework is active
        created_by_email: Email of creator

    Returns:
        Created ComplianceFramework instance
    """
    framework = ComplianceFramework(
        name=name,
        description=description,
        version=version,
        framework_document_id=framework_document_id,
        framework_index_name=framework_index_name,
        compliance_todos=compliance_todos or [],
        framework_metadata=framework_metadata or {},
        is_active=is_active,
        created_by_email=created_by_email,
    )

    db.add(framework)
    await db.commit()
    await db.refresh(framework)

    logger.info(f"Created compliance framework: {framework.name} (ID: {framework.id})")
    return framework


async def get_compliance_framework(
    db: AsyncSession, framework_id: UUID, load_document: bool = False
) -> Optional[ComplianceFramework]:
    """
    Get a compliance framework by ID.

    Args:
        db: Database session
        framework_id: Framework UUID
        load_document: Whether to eagerly load the framework document relationship

    Returns:
        ComplianceFramework instance or None
    """
    query = select(ComplianceFramework).where(ComplianceFramework.id == framework_id)

    if load_document:
        query = query.options(joinedload(ComplianceFramework.framework_document))

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_compliance_framework_by_name(
    db: AsyncSession, name: str
) -> Optional[ComplianceFramework]:
    """
    Get a compliance framework by name.

    Args:
        db: Database session
        name: Framework name

    Returns:
        ComplianceFramework instance or None
    """
    query = select(ComplianceFramework).where(ComplianceFramework.name == name)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_compliance_frameworks(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    is_active: Optional[bool] = None,
    search_query: Optional[str] = None,
) -> tuple[list[ComplianceFramework], int]:
    """
    List compliance frameworks with pagination and filtering.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        is_active: Filter by active status
        search_query: Search in name and description

    Returns:
        Tuple of (list of frameworks, total count)
    """
    # Base query
    query = select(ComplianceFramework)
    count_query = select(func.count()).select_from(ComplianceFramework)

    # Apply filters
    if is_active is not None:
        query = query.where(ComplianceFramework.is_active == is_active)
        count_query = count_query.where(ComplianceFramework.is_active == is_active)

    if search_query:
        search_filter = (
            ComplianceFramework.name.ilike(f"%{search_query}%")
            | ComplianceFramework.description.ilike(f"%{search_query}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply ordering and pagination
    query = query.order_by(ComplianceFramework.created_at.desc())
    query = query.offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    frameworks = list(result.scalars().all())

    return frameworks, total


async def update_compliance_framework(
    db: AsyncSession,
    framework_id: UUID,
    name: Optional[str] = None,
    description: Optional[str] = None,
    version: Optional[str] = None,
    framework_document_id: Optional[UUID] = None,
    framework_index_name: Optional[str] = None,
    compliance_todos: Optional[list[str]] = None,
    framework_metadata: Optional[dict] = None,
    is_active: Optional[bool] = None,
    updated_by_email: Optional[str] = None,
) -> Optional[ComplianceFramework]:
    """
    Update a compliance framework.

    Args:
        db: Database session
        framework_id: Framework UUID
        name: Optional new name
        description: Optional new description
        version: Optional new version
        framework_document_id: Optional new document reference
        framework_index_name: Optional new index name
        compliance_todos: Optional new todos list
        framework_metadata: Optional new metadata
        is_active: Optional new active status
        updated_by_email: Email of updater

    Returns:
        Updated ComplianceFramework instance or None
    """
    framework = await get_compliance_framework(db, framework_id)
    if not framework:
        return None

    # Update fields
    if name is not None:
        framework.name = name
    if description is not None:
        framework.description = description
    if version is not None:
        framework.version = version
    if framework_document_id is not None:
        framework.framework_document_id = framework_document_id
    if framework_index_name is not None:
        framework.framework_index_name = framework_index_name
    if compliance_todos is not None:
        framework.compliance_todos = compliance_todos
    if framework_metadata is not None:
        framework.framework_metadata = framework_metadata
    if is_active is not None:
        framework.is_active = is_active
    if updated_by_email is not None:
        framework.updated_by_email = updated_by_email

    await db.commit()
    await db.refresh(framework)

    logger.info(f"Updated compliance framework: {framework.name} (ID: {framework.id})")
    return framework


async def update_compliance_todos(
    db: AsyncSession,
    framework_id: UUID,
    compliance_todos: list[str],
    updated_by_email: Optional[str] = None,
) -> Optional[ComplianceFramework]:
    """
    Update just the compliance todos list for a framework.

    Args:
        db: Database session
        framework_id: Framework UUID
        compliance_todos: New todos list
        updated_by_email: Email of updater

    Returns:
        Updated ComplianceFramework instance or None
    """
    framework = await get_compliance_framework(db, framework_id)
    if not framework:
        return None

    framework.compliance_todos = compliance_todos
    if updated_by_email:
        framework.updated_by_email = updated_by_email

    await db.commit()
    await db.refresh(framework)

    logger.info(
        f"Updated compliance todos for {framework.name}: {len(compliance_todos)} todos"
    )
    return framework


async def delete_compliance_framework(
    db: AsyncSession, framework_id: UUID
) -> bool:
    """
    Delete a compliance framework.

    Args:
        db: Database session
        framework_id: Framework UUID

    Returns:
        True if deleted, False if not found
    """
    framework = await get_compliance_framework(db, framework_id)
    if not framework:
        return False

    await db.delete(framework)
    await db.commit()

    logger.info(f"Deleted compliance framework: {framework.name} (ID: {framework_id})")
    return True


async def get_compliance_framework_stats(db: AsyncSession) -> dict:
    """
    Get statistics about compliance frameworks.

    Args:
        db: Database session

    Returns:
        Dictionary with statistics
    """
    # Total count
    total_query = select(func.count()).select_from(ComplianceFramework)
    total_result = await db.execute(total_query)
    total = total_result.scalar()

    # Active count
    active_query = select(func.count()).select_from(ComplianceFramework).where(
        ComplianceFramework.is_active == True
    )
    active_result = await db.execute(active_query)
    active = active_result.scalar()

    return {
        "total_frameworks": total,
        "active_frameworks": active,
        "inactive_frameworks": total - active,
    }
