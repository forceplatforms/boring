"""
CRUD operations for DocumentChunk model.
Handles database operations for document chunk management.
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.models.document_chunk import DocumentChunk


async def get_document_chunks(
    db: AsyncSession,
    document_id: UUID,
    chunk_type: Optional[str] = None,
    page_number: Optional[int] = None,
    split_identifier: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> tuple[list[DocumentChunk], int]:
    """
    Get chunks for a document with filtering.

    Args:
        db: Database session
        document_id: Parent document UUID
        chunk_type: Filter by chunk type (text, table, figure, etc.)
        page_number: Filter by page number
        split_identifier: Filter by split/section identifier
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        Tuple of (list of chunks, total count)
    """
    # Build query
    query = select(DocumentChunk).where(DocumentChunk.document_id == document_id)

    # Apply filters
    if chunk_type:
        query = query.where(DocumentChunk.chunk_type == chunk_type)
    if page_number is not None:
        query = query.where(DocumentChunk.page_number == page_number)
    if split_identifier:
        query = query.where(DocumentChunk.split_identifier == split_identifier)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply ordering and pagination
    query = query.order_by(DocumentChunk.chunk_order).offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    chunks = list(result.scalars().all())

    return chunks, total


async def get_chunk_by_id(
    db: AsyncSession,
    document_id: UUID,
    chunk_id: str,
) -> Optional[DocumentChunk]:
    """
    Get a specific chunk by its chunk_id.

    Args:
        db: Database session
        document_id: Parent document UUID
        chunk_id: Landing AI chunk ID (e.g., 'chunk-abc-123')

    Returns:
        DocumentChunk instance or None if not found
    """
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .where(DocumentChunk.chunk_id == chunk_id)
    )
    return result.scalar_one_or_none()


async def get_chunks_by_type(
    db: AsyncSession,
    document_id: UUID,
    chunk_type: str,
) -> list[DocumentChunk]:
    """
    Get all chunks of a specific type for a document.

    Args:
        db: Database session
        document_id: Parent document UUID
        chunk_type: Type of chunks to retrieve

    Returns:
        List of DocumentChunk instances
    """
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .where(DocumentChunk.chunk_type == chunk_type)
        .order_by(DocumentChunk.chunk_order)
    )
    return list(result.scalars().all())


async def get_chunks_by_page(
    db: AsyncSession,
    document_id: UUID,
    page_number: int,
) -> list[DocumentChunk]:
    """
    Get all chunks on a specific page.

    Args:
        db: Database session
        document_id: Parent document UUID
        page_number: Page number (1-indexed)

    Returns:
        List of DocumentChunk instances
    """
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .where(DocumentChunk.page_number == page_number)
        .order_by(DocumentChunk.chunk_order)
    )
    return list(result.scalars().all())


async def get_chunks_by_split(
    db: AsyncSession,
    document_id: UUID,
    split_identifier: str,
) -> list[DocumentChunk]:
    """
    Get all chunks belonging to a specific split/section.

    Args:
        db: Database session
        document_id: Parent document UUID
        split_identifier: Split identifier (e.g., 'Item_1C')

    Returns:
        List of DocumentChunk instances
    """
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .where(DocumentChunk.split_identifier == split_identifier)
        .order_by(DocumentChunk.chunk_order)
    )
    return list(result.scalars().all())


async def get_chunk_stats(
    db: AsyncSession,
    document_id: UUID,
) -> dict:
    """
    Get chunk statistics for a document.

    Args:
        db: Database session
        document_id: Parent document UUID

    Returns:
        Dictionary with statistics
    """
    # Total chunks
    total_result = await db.execute(
        select(func.count(DocumentChunk.id))
        .where(DocumentChunk.document_id == document_id)
    )
    total = total_result.scalar_one()

    # By type
    type_result = await db.execute(
        select(DocumentChunk.chunk_type, func.count(DocumentChunk.id))
        .where(DocumentChunk.document_id == document_id)
        .group_by(DocumentChunk.chunk_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    # By page
    page_result = await db.execute(
        select(DocumentChunk.page_number, func.count(DocumentChunk.id))
        .where(DocumentChunk.document_id == document_id)
        .group_by(DocumentChunk.page_number)
        .order_by(DocumentChunk.page_number)
    )
    by_page = {row[0]: row[1] for row in page_result.all()}

    return {
        "total": total,
        "by_type": by_type,
        "by_page": by_page,
    }
