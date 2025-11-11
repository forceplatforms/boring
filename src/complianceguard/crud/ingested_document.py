"""
CRUD operations for IngestedDocument model.
Handles database operations for API-based document ingestion.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.models.ingested_document import IngestedDocument

logger = logging.getLogger(__name__)


async def create_ingested_document(
    db: AsyncSession,
    filename: str,
    file_hash: str,
    file_size: int,
    mime_type: str,
    s3_key: str,
    s3_bucket: str,
    doc_type: Optional[str] = None,
    doc_category: Optional[str] = None,
    metadata: Optional[dict] = None,
) -> IngestedDocument:
    """
    Create a new ingested document record.

    Args:
        db: Database session
        filename: Original filename
        file_hash: SHA-256 hash for deduplication
        file_size: File size in bytes
        mime_type: MIME type
        s3_key: S3 key for the document
        s3_bucket: S3 bucket name
        doc_type: Optional document type
        doc_category: Optional document category
        metadata: Optional flexible metadata

    Returns:
        Created IngestedDocument instance
    """
    document = IngestedDocument(
        filename=filename,
        file_hash=file_hash,
        file_size=file_size,
        mime_type=mime_type,
        s3_key=s3_key,
        s3_bucket=s3_bucket,
        doc_type=doc_type,
        doc_category=doc_category,
        doc_metadata=metadata or {},
        indexing_status="pending",
    )

    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info(f"Created ingested document {document.id} with hash {file_hash}")

    return document


async def get_ingested_document(
    db: AsyncSession, document_id: UUID
) -> Optional[IngestedDocument]:
    """
    Get ingested document by ID.

    Args:
        db: Database session
        document_id: Document UUID

    Returns:
        IngestedDocument instance or None if not found
    """
    result = await db.execute(
        select(IngestedDocument).where(IngestedDocument.id == document_id)
    )
    return result.scalar_one_or_none()


async def get_ingested_document_by_hash(
    db: AsyncSession, file_hash: str
) -> Optional[IngestedDocument]:
    """
    Get ingested document by file hash for deduplication.

    Args:
        db: Database session
        file_hash: SHA-256 file hash

    Returns:
        IngestedDocument instance or None if not found
    """
    result = await db.execute(
        select(IngestedDocument).where(IngestedDocument.file_hash == file_hash)
    )
    return result.scalar_one_or_none()


async def list_ingested_documents(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    doc_type: Optional[str] = None,
    doc_category: Optional[str] = None,
    indexing_status: Optional[str] = None,
    index_name: Optional[str] = None,
) -> tuple[list[IngestedDocument], int]:
    """
    List ingested documents with filtering and pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        doc_type: Filter by document type
        doc_category: Filter by document category
        indexing_status: Filter by indexing status
        index_name: Filter by Milvus index name

    Returns:
        Tuple of (list of documents, total count)
    """
    # Build query
    query = select(IngestedDocument)

    # Apply filters
    if doc_type:
        query = query.where(IngestedDocument.doc_type == doc_type)
    if doc_category:
        query = query.where(IngestedDocument.doc_category == doc_category)
    if indexing_status:
        query = query.where(IngestedDocument.indexing_status == indexing_status)
    if index_name:
        query = query.where(IngestedDocument.index_name == index_name)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination and ordering
    query = query.order_by(IngestedDocument.created_at.desc()).offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    documents = list(result.scalars().all())

    return documents, total


async def update_indexing_info(
    db: AsyncSession,
    document_id: UUID,
    index_name: str,
    num_pages: int,
    page_image_s3_prefix: str,
    status: str = "completed",
    error_message: Optional[str] = None,
) -> Optional[IngestedDocument]:
    """
    Update document indexing information after Milvus indexing.

    Args:
        db: Database session
        document_id: Document UUID
        index_name: Milvus collection name
        num_pages: Number of pages indexed
        page_image_s3_prefix: S3 prefix for page images
        status: Indexing status (completed, failed)
        error_message: Error message if failed

    Returns:
        Updated IngestedDocument or None if not found
    """
    document = await get_ingested_document(db, document_id)
    if not document:
        return None

    # Update indexing info
    document.index_name = index_name
    document.num_pages = num_pages
    document.page_image_s3_prefix = page_image_s3_prefix
    document.indexing_status = status

    if status == "completed":
        document.indexed_at = datetime.now()
        document.indexing_error = None
    elif status == "failed":
        document.indexing_error = error_message

    document.updated_at = datetime.now()

    await db.commit()
    await db.refresh(document)

    logger.info(f"Updated indexing info for document {document_id}: status={status}")

    return document


async def update_metadata(
    db: AsyncSession,
    document_id: UUID,
    metadata: dict,
) -> Optional[IngestedDocument]:
    """
    Update document metadata.

    Args:
        db: Database session
        document_id: Document UUID
        metadata: New metadata dictionary

    Returns:
        Updated IngestedDocument or None if not found
    """
    document = await get_ingested_document(db, document_id)
    if not document:
        return None

    document.doc_metadata = metadata
    document.updated_at = datetime.now()

    await db.commit()
    await db.refresh(document)

    return document


async def delete_ingested_document(db: AsyncSession, document_id: UUID) -> bool:
    """
    Delete ingested document by ID.

    Note: This only deletes the database record, not the S3 files.

    Args:
        db: Database session
        document_id: Document UUID

    Returns:
        True if deleted, False if not found
    """
    document = await get_ingested_document(db, document_id)
    if not document:
        return False

    await db.delete(document)
    await db.commit()

    logger.info(f"Deleted ingested document {document_id}")

    return True


async def get_ingested_document_stats(db: AsyncSession) -> dict:
    """
    Get ingested document statistics.

    Args:
        db: Database session

    Returns:
        Dictionary with statistics
    """
    # Total documents
    total_result = await db.execute(select(func.count(IngestedDocument.id)))
    total = total_result.scalar_one()

    # By type
    type_result = await db.execute(
        select(IngestedDocument.doc_type, func.count(IngestedDocument.id)).group_by(
            IngestedDocument.doc_type
        )
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    # By status
    status_result = await db.execute(
        select(
            IngestedDocument.indexing_status, func.count(IngestedDocument.id)
        ).group_by(IngestedDocument.indexing_status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    # By index name
    index_result = await db.execute(
        select(IngestedDocument.index_name, func.count(IngestedDocument.id)).group_by(
            IngestedDocument.index_name
        )
    )
    by_index = {row[0]: row[1] for row in index_result.all()}

    # Total size
    size_result = await db.execute(select(func.sum(IngestedDocument.file_size)))
    total_size = size_result.scalar_one() or 0

    return {
        "total": total,
        "by_type": by_type,
        "by_status": by_status,
        "by_index": by_index,
        "total_size_bytes": total_size,
        "total_size_mb": round(total_size / (1024 * 1024), 2),
    }


async def get_unique_index_names(db: AsyncSession) -> list[str]:
    """
    Get list of unique index names from ingested documents.

    Args:
        db: Database session

    Returns:
        List of unique index names (excluding None)
    """
    result = await db.execute(
        select(IngestedDocument.index_name)
        .distinct()
        .where(IngestedDocument.index_name.is_not(None))
        .order_by(IngestedDocument.index_name)
    )
    index_names = [row[0] for row in result.all()]

    logger.info(f"Found {len(index_names)} unique index names")

    return index_names
