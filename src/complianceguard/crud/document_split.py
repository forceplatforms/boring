"""
CRUD operations for DocumentSplit model.
Handles database operations for document split/section management.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.models.document_split import DocumentSplit


async def get_document_splits(
    db: AsyncSession,
    document_id: UUID,
    class_filter: Optional[str] = None,
    identifier_filter: Optional[str] = None,
) -> list[DocumentSplit]:
    """
    Get splits for a document with filtering.

    Args:
        db: Database session
        document_id: Parent document UUID
        class_filter: Filter by split class (section, chapter, etc.)
        identifier_filter: Filter by identifier (e.g., 'Item_1C')

    Returns:
        List of DocumentSplit instances
    """
    # Build query
    query = select(DocumentSplit).where(DocumentSplit.document_id == document_id)

    # Apply filters
    if class_filter:
        query = query.where(DocumentSplit.class_ == class_filter)
    if identifier_filter:
        query = query.where(DocumentSplit.identifier == identifier_filter)

    # Apply ordering
    query = query.order_by(DocumentSplit.split_order)

    # Execute query
    result = await db.execute(query)
    splits = list(result.scalars().all())

    return splits


async def get_split_by_identifier(
    db: AsyncSession,
    document_id: UUID,
    identifier: str,
) -> Optional[DocumentSplit]:
    """
    Get a specific split by its identifier.

    Args:
        db: Database session
        document_id: Parent document UUID
        identifier: Split identifier (e.g., 'Item_1C')

    Returns:
        DocumentSplit instance or None if not found
    """
    result = await db.execute(
        select(DocumentSplit)
        .where(DocumentSplit.document_id == document_id)
        .where(DocumentSplit.identifier == identifier)
    )
    return result.scalar_one_or_none()


async def get_splits_by_class(
    db: AsyncSession,
    document_id: UUID,
    class_name: str,
) -> list[DocumentSplit]:
    """
    Get all splits of a specific class for a document.

    Args:
        db: Database session
        document_id: Parent document UUID
        class_name: Class of splits to retrieve (section, chapter, etc.)

    Returns:
        List of DocumentSplit instances
    """
    result = await db.execute(
        select(DocumentSplit)
        .where(DocumentSplit.document_id == document_id)
        .where(DocumentSplit.class_ == class_name)
        .order_by(DocumentSplit.split_order)
    )
    return list(result.scalars().all())


async def get_split_stats(
    db: AsyncSession,
    document_id: UUID,
) -> dict:
    """
    Get split statistics for a document.

    Args:
        db: Database session
        document_id: Parent document UUID

    Returns:
        Dictionary with statistics
    """
    # Total splits
    total_result = await db.execute(
        select(func.count(DocumentSplit.id))
        .where(DocumentSplit.document_id == document_id)
    )
    total = total_result.scalar_one()

    # By class
    class_result = await db.execute(
        select(DocumentSplit.class_, func.count(DocumentSplit.id))
        .where(DocumentSplit.document_id == document_id)
        .group_by(DocumentSplit.class_)
    )
    by_class = {row[0]: row[1] for row in class_result.all()}

    return {
        "total": total,
        "by_class": by_class,
    }
