"""
Document management API endpoints with database integration.
"""

from typing import Optional
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.crud import document as document_crud
from complianceguard.crud import document_chunk as chunk_crud
from complianceguard.crud import document_split as split_crud
from complianceguard.database import get_async_db
from complianceguard.models.document import Document
from complianceguard.models.document_chunk import DocumentChunk
from complianceguard.models.document_split import DocumentSplit
from complianceguard.schemas.base import PaginatedResponse, SuccessResponse
from complianceguard.schemas.document import (
    ChunkStatsResponse,
    DocumentChunkResponse,
    DocumentDetail,
    DocumentSplitResponse,
    DocumentStatsResponse,
    DocumentSummary,
    DocumentUpdateRequest,
    DocumentUploadResponse,
    SplitStatsResponse,
)

router = APIRouter(prefix="/documents")


async def _document_to_upload_response(doc: Document) -> DocumentUploadResponse:
    """Convert Document model to DocumentUploadResponse."""
    # Import here to avoid circular dependency
    from complianceguard.utils.file_storage import generate_presigned_url

    # Generate presigned URL for S3 access (24 hours expiration)
    file_url = None
    try:
        file_url = await generate_presigned_url(doc.file_path, expiration_seconds=86400)
    except Exception as e:
        # Log but don't fail if URL generation fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to generate presigned URL for document {doc.id}: {e}")

    return DocumentUploadResponse(
        id=doc.id,
        file_name=doc.file_name,
        doc_type=doc.doc_type,
        doc_category=doc.doc_category,
        file_size_bytes=doc.file_size_bytes,
        extraction_status=doc.extraction_status,
        uploaded_by=doc.uploaded_by_email or "unknown",
        file_url=file_url,
        file_path=doc.file_path,
        file_hash=doc.file_hash,
        mime_type=doc.mime_type,
        extracted_text=doc.extracted_text,
        extraction_error=doc.extraction_error,
        extraction_metadata=doc.extraction_metadata or {},
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def _document_to_summary(doc: Document) -> DocumentSummary:
    """Convert Document model to DocumentSummary."""
    return DocumentSummary(
        id=doc.id,
        file_name=doc.file_name,
        doc_type=doc.doc_type,
        doc_category=doc.doc_category,
        file_size_bytes=doc.file_size_bytes,
        extraction_status=doc.extraction_status,
        uploaded_by=doc.uploaded_by_email or "unknown",
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def _document_to_detail(doc: Document) -> DocumentDetail:
    """Convert Document model to DocumentDetail."""
    return DocumentDetail(
        id=doc.id,
        file_name=doc.file_name,
        doc_type=doc.doc_type,
        doc_category=doc.doc_category,
        file_size_bytes=doc.file_size_bytes,
        extraction_status=doc.extraction_status,
        uploaded_by=doc.uploaded_by_email or "unknown",
        file_path=doc.file_path,
        file_hash=doc.file_hash,
        mime_type=doc.mime_type,
        extracted_text=doc.extracted_text,
        extraction_error=doc.extraction_error,
        extraction_metadata=doc.extraction_metadata or {},
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


def _chunk_to_response(chunk: DocumentChunk) -> DocumentChunkResponse:
    """Convert DocumentChunk model to DocumentChunkResponse."""
    return DocumentChunkResponse(
        id=chunk.id,
        document_id=chunk.document_id,
        chunk_id=chunk.chunk_id,
        chunk_type=chunk.chunk_type,
        chunk_order=chunk.chunk_order,
        content=chunk.content,
        page_number=chunk.page_number,
        bounding_box=chunk.bounding_box or {},
        split_identifier=chunk.split_identifier,
        created_at=chunk.created_at,
        updated_at=chunk.updated_at,
    )


def _split_to_response(split: DocumentSplit) -> DocumentSplitResponse:
    """Convert DocumentSplit model to DocumentSplitResponse."""
    return DocumentSplitResponse(
        id=split.id,
        document_id=split.document_id,
        class_=split.class_,
        identifier=split.identifier,
        pages=split.pages or [],
        markdown=split.markdown,
        chunk_ids=split.chunk_ids or [],
        split_order=split.split_order,
        created_at=split.created_at,
        updated_at=split.updated_at,
    )


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Document",
    description="Upload a PDF or DOCX document for compliance analysis",
    responses={
        201: {"description": "Document uploaded successfully"},
        400: {"description": "Invalid file type or size"},
        409: {"description": "Document already exists (duplicate hash)"},
    },
)
async def upload_document(
    file: UploadFile = File(..., description="PDF or DOCX file to upload"),
    doc_type: str = Form(..., description="Document type: ciso_report or sec_filing"),
    doc_category: Optional[str] = Form(None, description="Document category"),
    uploaded_by_email: Optional[str] = Form(None, description="Uploader email"),
    uploaded_by_name: Optional[str] = Form(None, description="Uploader name"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Upload a document for compliance analysis.

    - **file**: PDF or DOCX file (max 50MB)
    - **doc_type**: Type of document (ciso_report, sec_filing)
    - **doc_category**: Optional category (Form_8K, Incident_Report, etc.)
    - **uploaded_by_email**: Email of uploader
    - **uploaded_by_name**: Name of uploader

    Returns document ID and extraction status. Text extraction begins automatically.
    """
    # Validate file type
    if file.content_type not in [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are supported",
        )

    # Create document in database (this also uploads to S3)
    document = await document_crud.create_document(
        db=db,
        upload_file=file,
        doc_type=doc_type,
        doc_category=doc_category,
        uploaded_by_email=uploaded_by_email,
        uploaded_by_name=uploaded_by_name,
    )

    return await _document_to_upload_response(document)


@router.get(
    "",
    response_model=PaginatedResponse[DocumentSummary],
    summary="List Documents",
    description="Get paginated list of documents with optional filters",
)
async def list_documents(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    doc_category: Optional[str] = Query(None, description="Filter by document category"),
    extraction_status: Optional[str] = Query(None, description="Filter by extraction status"),
    uploaded_by: Optional[str] = Query(None, description="Filter by uploader email"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve a paginated list of documents.

    **Filters:**
    - doc_type: ciso_report, sec_filing, unknown
    - doc_category: Form_8K, Incident_Report, etc.
    - extraction_status: pending, processing, completed, failed
    - uploaded_by: user email address

    **Pagination:**
    - limit: maximum items per page (1-100)
    - offset: number of items to skip
    """
    documents, total = await document_crud.list_documents(
        db=db,
        skip=offset,
        limit=limit,
        doc_type=doc_type,
        doc_category=doc_category,
        extraction_status=extraction_status,
        uploaded_by_email=uploaded_by,
    )

    return PaginatedResponse(
        items=[_document_to_summary(doc) for doc in documents],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Get Document",
    description="Get detailed document information including extracted text",
    responses={
        200: {"description": "Document details retrieved"},
        404: {"description": "Document not found"},
    },
)
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve detailed information about a specific document.

    Includes:
    - File metadata (name, size, type, hash)
    - Extraction status and results
    - Extracted text content
    - Processing metadata (pages, tables, confidence)
    """
    document = await document_crud.get_document(db, document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    return _document_to_detail(document)


@router.patch(
    "/{document_id}",
    response_model=DocumentDetail,
    summary="Update Document",
    description="Update document metadata",
)
async def update_document(
    document_id: UUID,
    update_data: DocumentUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update document metadata.

    Can update:
    - doc_type: Document type
    - doc_category: Document category
    """
    document = await document_crud.update_document(
        db=db,
        document_id=document_id,
        doc_type=update_data.doc_type,
        doc_category=update_data.doc_category,
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    return _document_to_detail(document)


@router.delete(
    "/{document_id}",
    response_model=SuccessResponse,
    summary="Delete Document",
    description="Delete a document and its associated data",
    responses={
        200: {"description": "Document deleted successfully"},
        404: {"description": "Document not found"},
    },
)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete a document.

    This will:
    - Remove the document record
    - Delete the file from storage
    - Remove from any indexes
    - Cascade delete associated violations
    """
    # Get document first to get file name
    document = await document_crud.get_document(db, document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    file_name = document.file_name

    # Delete document (CASCADE will handle violations)
    deleted = await document_crud.delete_document(db, document_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete document",
        )

    return SuccessResponse(
        success=True,
        message=f"Document '{file_name}' deleted successfully",
        data={"document_id": str(document_id)},
    )


@router.get(
    "/stats/summary",
    response_model=DocumentStatsResponse,
    summary="Document Statistics",
    description="Get aggregated document statistics",
)
async def get_document_stats(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get aggregated statistics about all documents.

    Returns:
    - Total document count
    - Count by document type
    - Count by extraction status
    - Total storage used
    """
    stats = await document_crud.get_document_stats(db)

    return DocumentStatsResponse(
        total_documents=stats["total"],
        by_type=stats["by_type"],
        by_status=stats["by_status"],
        total_size_mb=round(stats["total_size_bytes"] / (1024 * 1024), 2),
    )


# Document Chunk Endpoints


@router.get(
    "/{document_id}/chunks",
    response_model=PaginatedResponse[DocumentChunkResponse],
    summary="List Document Chunks",
    description="Get chunks for a document with optional filters",
    responses={
        200: {"description": "Chunks retrieved successfully"},
        404: {"description": "Document not found"},
    },
)
async def list_document_chunks(
    document_id: UUID,
    chunk_type: Optional[str] = Query(None, description="Filter by chunk type"),
    page_number: Optional[int] = Query(None, description="Filter by page number"),
    split_identifier: Optional[str] = Query(None, description="Filter by split identifier"),
    limit: int = Query(100, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve chunks for a specific document.

    **Filters:**
    - chunk_type: text, table, figure, form, etc.
    - page_number: specific page (1-indexed)
    - split_identifier: section/split identifier

    **Use cases:**
    - Get all tables: chunk_type=table
    - Get page 5 chunks: page_number=5
    - Get Item 1C chunks: split_identifier=Item_1C
    """
    # Verify document exists
    document = await document_crud.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Get chunks
    chunks, total = await chunk_crud.get_document_chunks(
        db=db,
        document_id=document_id,
        chunk_type=chunk_type,
        page_number=page_number,
        split_identifier=split_identifier,
        skip=offset,
        limit=limit,
    )

    return PaginatedResponse(
        items=[_chunk_to_response(chunk) for chunk in chunks],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/{document_id}/chunks/{chunk_id}",
    response_model=DocumentChunkResponse,
    summary="Get Specific Chunk",
    description="Get a specific chunk by its Landing AI chunk ID",
    responses={
        200: {"description": "Chunk retrieved successfully"},
        404: {"description": "Document or chunk not found"},
    },
)
async def get_document_chunk(
    document_id: UUID,
    chunk_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve a specific chunk by its Landing AI chunk ID.

    **Use cases:**
    - Get details for a specific chunk
    - Access chunk content for PDF highlighting
    - Get bounding box coordinates
    """
    # Verify document exists
    document = await document_crud.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Get chunk
    chunk = await chunk_crud.get_chunk_by_id(db, document_id, chunk_id)
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk {chunk_id} not found in document {document_id}",
        )

    return _chunk_to_response(chunk)


@router.get(
    "/{document_id}/tables",
    response_model=PaginatedResponse[DocumentChunkResponse],
    summary="Get All Tables",
    description="Get all table chunks from a document",
    responses={
        200: {"description": "Tables retrieved successfully"},
        404: {"description": "Document not found"},
    },
)
async def get_document_tables(
    document_id: UUID,
    limit: int = Query(100, ge=1, le=500, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve all table chunks from a document.

    **Use cases:**
    - Extract all tables for analysis
    - Generate table summaries
    - Compare tables across documents
    """
    # Verify document exists
    document = await document_crud.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Get table chunks
    chunks, total = await chunk_crud.get_document_chunks(
        db=db,
        document_id=document_id,
        chunk_type="table",
        skip=offset,
        limit=limit,
    )

    return PaginatedResponse(
        items=[_chunk_to_response(chunk) for chunk in chunks],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/{document_id}/page/{page_num}/chunks",
    response_model=list[DocumentChunkResponse],
    summary="Get Chunks by Page",
    description="Get all chunks on a specific page",
    responses={
        200: {"description": "Chunks retrieved successfully"},
        404: {"description": "Document not found"},
    },
)
async def get_chunks_by_page(
    document_id: UUID,
    page_num: int,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve all chunks on a specific page.

    **Use cases:**
    - PDF page highlighting
    - Page-by-page navigation
    - Spatial analysis of page content
    """
    # Verify document exists
    document = await document_crud.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Get chunks for page
    chunks = await chunk_crud.get_chunks_by_page(db, document_id, page_num)

    return [_chunk_to_response(chunk) for chunk in chunks]


@router.get(
    "/{document_id}/chunks/stats",
    response_model=ChunkStatsResponse,
    summary="Chunk Statistics",
    description="Get chunk statistics for a document",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        404: {"description": "Document not found"},
    },
)
async def get_chunk_stats(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get aggregated chunk statistics for a document.

    Returns:
    - Total chunk count
    - Count by chunk type (text, table, figure)
    - Count by page number
    """
    # Verify document exists
    document = await document_crud.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Get stats
    stats = await chunk_crud.get_chunk_stats(db, document_id)

    # Convert page numbers from int to str for JSON keys
    by_page = {str(k): v for k, v in stats["by_page"].items()}

    return ChunkStatsResponse(
        total=stats["total"],
        by_type=stats["by_type"],
        by_page=by_page,
    )


# Document Split Endpoints


@router.get(
    "/{document_id}/splits",
    response_model=list[DocumentSplitResponse],
    summary="List Document Splits",
    description="Get splits/sections for a document",
    responses={
        200: {"description": "Splits retrieved successfully"},
        404: {"description": "Document not found"},
    },
)
async def list_document_splits(
    document_id: UUID,
    class_filter: Optional[str] = Query(None, description="Filter by split class"),
    identifier_filter: Optional[str] = Query(None, description="Filter by identifier"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve splits/sections for a specific document.

    **Filters:**
    - class_filter: section, chapter, etc.
    - identifier_filter: specific identifier (e.g., 'Item_1C')

    **Use cases:**
    - Navigate document structure
    - Extract specific sections
    - Compare sections across documents
    """
    # Verify document exists
    document = await document_crud.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Get splits
    splits = await split_crud.get_document_splits(
        db=db,
        document_id=document_id,
        class_filter=class_filter,
        identifier_filter=identifier_filter,
    )

    return [_split_to_response(split) for split in splits]


@router.get(
    "/{document_id}/splits/{identifier}",
    response_model=DocumentSplitResponse,
    summary="Get Specific Split",
    description="Get a specific split by its identifier",
    responses={
        200: {"description": "Split retrieved successfully"},
        404: {"description": "Document or split not found"},
    },
)
async def get_document_split(
    document_id: UUID,
    identifier: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve a specific split by its identifier.

    **Use cases:**
    - Get Item 1C section
    - Extract Risk Factors section
    - Access specific chapters
    """
    # Verify document exists
    document = await document_crud.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Get split
    split = await split_crud.get_split_by_identifier(db, document_id, identifier)
    if not split:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Split '{identifier}' not found in document {document_id}",
        )

    return _split_to_response(split)


@router.get(
    "/{document_id}/splits/{identifier}/chunks",
    response_model=list[DocumentChunkResponse],
    summary="Get Split Chunks",
    description="Get all chunks belonging to a specific split/section",
    responses={
        200: {"description": "Chunks retrieved successfully"},
        404: {"description": "Document or split not found"},
    },
)
async def get_split_chunks(
    document_id: UUID,
    identifier: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve all chunks belonging to a specific split/section.

    **Use cases:**
    - Get all content in Item 1C section
    - Extract chunks from a specific chapter
    - Section-level content analysis
    """
    # Verify document exists
    document = await document_crud.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Verify split exists
    split = await split_crud.get_split_by_identifier(db, document_id, identifier)
    if not split:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Split '{identifier}' not found in document {document_id}",
        )

    # Get chunks for split
    chunks = await chunk_crud.get_chunks_by_split(db, document_id, identifier)

    return [_chunk_to_response(chunk) for chunk in chunks]


@router.get(
    "/{document_id}/splits/stats",
    response_model=SplitStatsResponse,
    summary="Split Statistics",
    description="Get split statistics for a document",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        404: {"description": "Document not found"},
    },
)
async def get_split_stats(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get aggregated split statistics for a document.

    Returns:
    - Total split count
    - Count by split class
    """
    # Verify document exists
    document = await document_crud.get_document(db, document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Get stats
    stats = await split_crud.get_split_stats(db, document_id)

    return SplitStatsResponse(
        total=stats["total"],
        by_class=stats["by_class"],
    )


@router.post(
    "/{document_id}/retry-extraction",
    response_model=DocumentDetail,
    summary="Retry Text Extraction",
    description="Retry text extraction for a document that failed processing",
    responses={
        200: {"description": "Extraction retried successfully"},
        404: {"description": "Document not found"},
        400: {"description": "Document already processed successfully"},
    },
)
async def retry_extraction(
    document_id: UUID,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retry text extraction for a document that failed processing.

    This endpoint:
    - Downloads the document from S3
    - Retries Landing AI extraction with retry logic
    - Updates the document with extracted chunks and text

    Only works for documents with extraction_status = 'failed' or 'processing'.
    """
    # Import here to avoid circular dependencies
    from complianceguard.utils.file_storage import get_file_from_s3
    from complianceguard.services.landing_ai import get_landing_ai_client
    from complianceguard.models.document_chunk import DocumentChunk
    from complianceguard.models.document_split import DocumentSplit
    from sqlalchemy import delete
    import logging

    logger = logging.getLogger(__name__)

    # Get the document
    document = await document_crud.get_document(db, document_id)

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    # Check if extraction already succeeded
    if document.extraction_status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document already processed successfully",
        )

    try:
        # Download file from S3
        file_content = await get_file_from_s3(document.file_path)

        # Update status to processing
        document.extraction_status = "processing"
        await db.flush()

        # Retry Landing AI extraction
        landing_ai_client = get_landing_ai_client()
        (
            extracted_text,
            extraction_metadata,
            chunks_list,
            splits_list,
        ) = await landing_ai_client.parse_and_prepare_chunks(
            document_id=document_id,
            file_content=file_content,
            filename=document.file_name,
        )

        # Delete any existing chunks/splits (for retry)
        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        )
        await db.execute(
            delete(DocumentSplit).where(DocumentSplit.document_id == document_id)
        )

        # Add new chunks
        for chunk in chunks_list:
            db.add(chunk)

        # Add new splits
        if splits_list:
            for split in splits_list:
                db.add(split)

        # Update document with successful extraction
        document.extracted_text = extracted_text
        document.extraction_metadata = extraction_metadata
        document.extraction_status = "completed"
        document.extraction_error = None

        await db.commit()
        await db.refresh(document)

        logger.info(f"Successfully retried extraction for document {document_id}")

    except Exception as e:
        # Update with new error
        document.extraction_status = "failed"
        document.extraction_error = str(e)
        await db.commit()

        logger.error(f"Retry failed for document {document_id}: {e}")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Extraction retry failed: {str(e)}",
        )

    return _document_to_detail(document)
