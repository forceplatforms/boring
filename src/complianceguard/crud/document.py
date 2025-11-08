"""
CRUD operations for Document model.
Handles database operations for document management.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.models.document import Document
from complianceguard.models.document_chunk import DocumentChunk
from complianceguard.models.document_split import DocumentSplit
from complianceguard.services.landing_ai import get_landing_ai_client
from complianceguard.utils.file_storage import upload_file_to_s3

logger = logging.getLogger(__name__)


async def create_document(
    db: AsyncSession,
    upload_file: UploadFile,
    doc_type: str,
    doc_category: Optional[str] = None,
    uploaded_by_email: Optional[str] = None,
    uploaded_by_name: Optional[str] = None,
) -> Document:
    """
    Create a new document from uploaded file.

    Args:
        db: Database session
        upload_file: Uploaded file
        doc_type: Type of document
        doc_category: Optional document category
        uploaded_by_email: Email of uploader
        uploaded_by_name: Name of uploader

    Returns:
        Created document instance with chunks and splits
    """
    # Read file content once
    file_content = await upload_file.read()
    await upload_file.seek(0)  # Reset for S3 upload

    # Upload file to S3 and get metadata
    s3_key, file_hash, file_size, mime_type = await upload_file_to_s3(upload_file)

    # Create document record first (without text/metadata)
    document_id = uuid4()
    document = Document(
        id=document_id,
        file_name=upload_file.filename or "unknown",
        file_path=s3_key,
        file_hash=file_hash,
        file_size_bytes=file_size,
        mime_type=mime_type,
        doc_type=doc_type,
        doc_category=doc_category,
        extraction_status="processing",
        uploaded_by_email=uploaded_by_email,
        uploaded_by_name=uploaded_by_name,
    )

    # Add and flush to get the document in the session
    db.add(document)
    await db.flush()

    # Try to parse document with Landing AI (but don't fail if it doesn't work)
    try:
        landing_ai_client = get_landing_ai_client()
        (
            extracted_text,
            extraction_metadata,
            chunks_list,
            splits_list,
        ) = await landing_ai_client.parse_and_prepare_chunks(
            document_id=document_id,
            file_content=file_content,
            filename=upload_file.filename or "unknown",
        )

        # Add all chunks to session
        for chunk in chunks_list:
            db.add(chunk)

        # Add all splits to session (if any)
        if splits_list:
            for split in splits_list:
                db.add(split)

        # Update document with successful extraction
        document.extracted_text = extracted_text
        document.extraction_metadata = extraction_metadata
        document.extraction_status = "completed"

        logger.info(f"Successfully extracted text from document {document_id}")

    except Exception as e:
        # Log the error but don't fail the upload
        logger.error(f"Failed to extract text from document {document_id}: {e}")

        # Update document with failed extraction status
        document.extraction_status = "failed"
        document.extraction_error = str(e)
        document.extracted_text = "[Extraction pending - will retry]"
        document.extraction_metadata = {
            "error": str(e),
            "extraction_method": "landing_ai_ade",
            "retry_required": True,
            "file_size": file_size,
        }

    # Always commit the document (success or failure)
    await db.commit()
    await db.refresh(document)

    return document


async def get_document(db: AsyncSession, document_id: UUID) -> Optional[Document]:
    """
    Get document by ID.

    Args:
        db: Database session
        document_id: Document UUID

    Returns:
        Document instance or None if not found
    """
    result = await db.execute(select(Document).where(Document.id == document_id))
    return result.scalar_one_or_none()


async def get_document_by_hash(db: AsyncSession, file_hash: str) -> Optional[Document]:
    """
    Get document by file hash.

    Args:
        db: Database session
        file_hash: SHA-256 file hash

    Returns:
        Document instance or None if not found
    """
    result = await db.execute(select(Document).where(Document.file_hash == file_hash))
    return result.scalar_one_or_none()


async def list_documents(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    doc_type: Optional[str] = None,
    doc_category: Optional[str] = None,
    extraction_status: Optional[str] = None,
    uploaded_by_email: Optional[str] = None,
) -> tuple[list[Document], int]:
    """
    List documents with filtering and pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        doc_type: Filter by document type
        doc_category: Filter by document category
        extraction_status: Filter by extraction status
        uploaded_by_email: Filter by uploader email

    Returns:
        Tuple of (list of documents, total count)
    """
    # Build query
    query = select(Document)

    # Apply filters
    if doc_type:
        query = query.where(Document.doc_type == doc_type)
    if doc_category:
        query = query.where(Document.doc_category == doc_category)
    if extraction_status:
        query = query.where(Document.extraction_status == extraction_status)
    if uploaded_by_email:
        query = query.where(Document.uploaded_by_email == uploaded_by_email)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply pagination and ordering
    query = query.order_by(Document.created_at.desc()).offset(skip).limit(limit)

    # Execute query
    result = await db.execute(query)
    documents = list(result.scalars().all())

    return documents, total


async def update_document(
    db: AsyncSession,
    document_id: UUID,
    doc_type: Optional[str] = None,
    doc_category: Optional[str] = None,
    extraction_status: Optional[str] = None,
    extracted_text: Optional[str] = None,
    extraction_error: Optional[str] = None,
    extraction_metadata: Optional[dict] = None,
) -> Optional[Document]:
    """
    Update document fields.

    Args:
        db: Database session
        document_id: Document UUID
        doc_type: Optional new document type
        doc_category: Optional new document category
        extraction_status: Optional new extraction status
        extracted_text: Optional extracted text
        extraction_error: Optional extraction error
        extraction_metadata: Optional extraction metadata

    Returns:
        Updated document or None if not found
    """
    document = await get_document(db, document_id)
    if not document:
        return None

    # Update fields if provided
    if doc_type is not None:
        document.doc_type = doc_type
    if doc_category is not None:
        document.doc_category = doc_category
    if extraction_status is not None:
        document.extraction_status = extraction_status
    if extracted_text is not None:
        document.extracted_text = extracted_text
    if extraction_error is not None:
        document.extraction_error = extraction_error
    if extraction_metadata is not None:
        document.extraction_metadata = extraction_metadata

    document.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(document)

    return document


async def delete_document(db: AsyncSession, document_id: UUID) -> bool:
    """
    Delete document by ID.

    Args:
        db: Database session
        document_id: Document UUID

    Returns:
        True if deleted, False if not found
    """
    document = await get_document(db, document_id)
    if not document:
        return False

    await db.delete(document)
    await db.commit()

    return True


async def get_document_stats(db: AsyncSession) -> dict:
    """
    Get document statistics.

    Args:
        db: Database session

    Returns:
        Dictionary with statistics
    """
    # Total documents
    total_result = await db.execute(select(func.count(Document.id)))
    total = total_result.scalar_one()

    # By type
    type_result = await db.execute(
        select(Document.doc_type, func.count(Document.id))
        .group_by(Document.doc_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}

    # By status
    status_result = await db.execute(
        select(Document.extraction_status, func.count(Document.id))
        .group_by(Document.extraction_status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    # Total size
    size_result = await db.execute(select(func.sum(Document.file_size_bytes)))
    total_size = size_result.scalar_one() or 0

    return {
        "total": total,
        "by_type": by_type,
        "by_status": by_status,
        "total_size_bytes": total_size,
    }
