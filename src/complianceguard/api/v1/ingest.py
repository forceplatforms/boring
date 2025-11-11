"""
Document ingestion API endpoints for batch PDF uploads.
"""

import json
import logging
import re
import time
from typing import Optional

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

from complianceguard.config import get_settings
from complianceguard.crud import ingested_document as ingested_doc_crud
from complianceguard.database import get_async_db
from complianceguard.indexing import DocumentIndex
from complianceguard.models.ingested_document import IngestedDocument
from complianceguard.schemas.ingested_document import (
    BatchIngestResponse,
    BatchIngestResult,
    IngestDocumentResponse,
    IngestedDocumentSummary,
    IngestedDocumentStatsResponse,
)
from complianceguard.schemas.base import PaginatedResponse
from complianceguard.utils.file_storage import (
    calculate_file_hash,
    upload_file_to_s3,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest")


def _validate_and_sanitize_index_name(index_name: str) -> str:
    """Validate and sanitize Milvus collection name.

    Milvus collection naming rules:
    - Only alphanumeric and underscore allowed (hyphens NOT allowed)
    - Length: 1-255 characters (we enforce 3-64 for sanity)
    - Must start with letter or underscore
    - Case-sensitive but we normalize to lowercase

    Args:
        index_name: Raw index name from user input

    Returns:
        Sanitized and validated index name

    Raises:
        HTTPException: If index name is invalid
    """
    if not index_name or not index_name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Index name cannot be empty"
        )

    # Remove leading/trailing whitespace
    sanitized = index_name.strip()

    # Replace invalid characters (including hyphens) with underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', sanitized)

    # Convert to lowercase for consistency
    sanitized = sanitized.lower()

    # Check length constraints
    if len(sanitized) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Index name must be at least 3 characters (got: {len(sanitized)})"
        )

    if len(sanitized) > 64:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Index name must be at most 64 characters (got: {len(sanitized)})"
        )

    # Must start with letter or underscore
    if not (sanitized[0].isalpha() or sanitized[0] == '_'):
        sanitized = f"idx_{sanitized}"

    logger.info(f"[INGEST] Validated index name: '{index_name}' -> '{sanitized}'")

    return sanitized


def _ingested_doc_to_response(doc: IngestedDocument) -> IngestDocumentResponse:
    """Convert IngestedDocument model to IngestDocumentResponse."""
    return IngestDocumentResponse(
        id=doc.id,
        filename=doc.filename,
        file_hash=doc.file_hash,
        file_size=doc.file_size,
        file_size_mb=doc.file_size_mb,
        mime_type=doc.mime_type,
        doc_type=doc.doc_type,
        doc_category=doc.doc_category,
        indexing_status=doc.indexing_status,
        s3_key=doc.s3_key,
        s3_bucket=doc.s3_bucket,
        metadata=doc.doc_metadata or {},
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


async def _process_single_file(
    db: AsyncSession,
    file: UploadFile,
    doc_type: Optional[str],
    doc_category: Optional[str],
    metadata: Optional[dict],
    index_name: str,
    settings,
) -> BatchIngestResult:
    """
    Process a single file upload: validate, upload to S3, create DB record, and index.

    Args:
        db: Database session
        file: Uploaded file
        doc_type: Optional document type
        doc_category: Optional document category
        metadata: Optional metadata dictionary
        index_name: Milvus collection name to use for indexing
        settings: Application settings

    Returns:
        BatchIngestResult with success/failure status
    """
    start_time = time.time()
    filename = file.filename or "unknown.pdf"

    logger.info(f"[INGEST] Starting ingestion for file: {filename}")
    logger.info(f"[INGEST] Target index: {index_name}")
    logger.info(f"[INGEST] File metadata - type: {doc_type}, category: {doc_category}")

    try:
        # Validate file type (only PDFs)
        logger.info(f"[INGEST] Validating file type for: {filename}")
        if file.content_type != "application/pdf":
            logger.warning(f"[INGEST] Invalid file type for {filename}: {file.content_type} (expected: application/pdf)")
            return BatchIngestResult(
                filename=filename,
                success=False,
                document=None,
                error="Invalid file type. Only PDFs are supported.",
                duplicate=False,
            )
        logger.info(f"[INGEST] File type validated successfully: {filename}")

        # Read file content once
        logger.info(f"[INGEST] Reading file content: {filename}")
        file_content = await file.read()
        file_size_bytes = len(file_content)
        file_size_mb = file_size_bytes / (1024 * 1024)
        logger.info(f"[INGEST] File content read - size: {file_size_mb:.2f} MB ({file_size_bytes} bytes)")
        await file.seek(0)  # Reset for potential reuse

        # Calculate file hash for deduplication
        logger.info(f"[INGEST] Calculating SHA-256 hash for: {filename}")
        hash_start = time.time()
        file_hash = calculate_file_hash(file_content)
        hash_time = time.time() - hash_start
        logger.info(f"[INGEST] File hash calculated in {hash_time:.3f}s: {file_hash[:16]}...")

        # Check for duplicates
        logger.info(f"[INGEST] Checking for duplicate documents with hash: {file_hash[:16]}...")
        duplicate_check_start = time.time()
        existing_doc = await ingested_doc_crud.get_ingested_document_by_hash(db, file_hash)
        duplicate_check_time = time.time() - duplicate_check_start

        if existing_doc:
            logger.info(f"[INGEST] Duplicate detected for {filename} - existing document ID: {existing_doc.id}")
            logger.info(f"[INGEST] Duplicate check completed in {duplicate_check_time:.3f}s")
            logger.info(f"[INGEST] Skipping ingestion - returning existing document")
            return BatchIngestResult(
                filename=filename,
                success=True,
                document=_ingested_doc_to_response(existing_doc),
                error=None,
                duplicate=True,
            )
        logger.info(f"[INGEST] No duplicate found in {duplicate_check_time:.3f}s - proceeding with upload")

        # Upload to S3
        logger.info(f"[INGEST] Starting S3 upload for: {filename}")
        await file.seek(0)  # Reset for S3 upload
        s3_start = time.time()
        s3_key, _, file_size, mime_type = await upload_file_to_s3(file)
        s3_time = time.time() - s3_start
        logger.info(f"[INGEST] S3 upload completed in {s3_time:.3f}s")
        logger.info(f"[INGEST] S3 location - bucket: {settings.s3_bucket_name}, key: {s3_key}")

        # Create database record
        logger.info(f"[INGEST] Creating database record for: {filename}")
        db_start = time.time()
        document = await ingested_doc_crud.create_ingested_document(
            db=db,
            filename=filename,
            file_hash=file_hash,
            file_size=file_size,
            mime_type=mime_type,
            s3_key=s3_key,
            s3_bucket=settings.s3_bucket_name,
            doc_type=doc_type,
            doc_category=doc_category,
            metadata=metadata or {},
        )
        db_time = time.time() - db_start
        logger.info(f"[INGEST] Database record created in {db_time:.3f}s - document ID: {document.id}")

        # Start background indexing (mark as processing)
        logger.info(f"[INGEST] Marking document {document.id} as 'indexing'")
        document.mark_as_indexing()
        await db.commit()
        await db.refresh(document)
        logger.info(f"[INGEST] Document status updated to 'indexing'")

        # Index document in Milvus
        indexing_start = time.time()
        try:
            logger.info(f"[INGEST] Starting Milvus indexing for document {document.id}")
            # Initialize DocumentIndex
            logger.info(f"[INGEST] Initializing DocumentIndex with collection: {index_name}")
            index = DocumentIndex(
                index_name=index_name,
                milvus_uri=settings.indexing_milvus_uri,
            )

            # Download file temporarily and index
            # The index_document method will:
            # 1. Convert PDF to images
            # 2. Generate ColPali embeddings
            # 3. Upload page images to S3
            # 4. Insert into Milvus with page URLs
            from complianceguard.utils.file_storage import get_file_from_s3
            import tempfile
            import os

            # Download file from S3
            logger.info(f"[INGEST] Downloading PDF from S3 for indexing: {s3_key}")
            download_start = time.time()
            file_bytes = await get_file_from_s3(s3_key)
            download_time = time.time() - download_start
            logger.info(f"[INGEST] PDF downloaded from S3 in {download_time:.3f}s ({len(file_bytes)} bytes)")

            # Save to temporary file
            logger.info(f"[INGEST] Creating temporary file for PDF processing")
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file_bytes)
                tmp_file_path = tmp_file.name
            logger.info(f"[INGEST] Temporary file created: {tmp_file_path}")

            try:
                # Index document (pass file_hash for metadata lookup)
                logger.info(f"[INGEST] Starting PDF indexing process (conversion + embeddings + storage)")
                index_start = time.time()
                num_pages = await index.index_document(tmp_file_path, file_hash=file_hash)
                index_time = time.time() - index_start
                logger.info(f"[INGEST] PDF indexed successfully in {index_time:.3f}s - {num_pages} pages processed")

                # Get page image S3 prefix (with index_name namespace)
                page_image_prefix = f"pages/{index_name}/{file_hash}/{filename}/"
                logger.info(f"[INGEST] Page images stored at S3 prefix: {page_image_prefix}")

                # Update document with indexing success
                logger.info(f"[INGEST] Updating document {document.id} with indexing success info")
                update_start = time.time()
                await ingested_doc_crud.update_indexing_info(
                    db=db,
                    document_id=document.id,
                    index_name=index_name,
                    num_pages=num_pages,
                    page_image_s3_prefix=page_image_prefix,
                    status="completed",
                )
                update_time = time.time() - update_start
                logger.info(f"[INGEST] Document indexing info updated in {update_time:.3f}s")

                indexing_total_time = time.time() - indexing_start
                logger.info(f"[INGEST] ✓ Complete indexing pipeline finished in {indexing_total_time:.3f}s")
                logger.info(f"[INGEST] Successfully indexed document {document.id} with {num_pages} pages")

            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    logger.info(f"[INGEST] Cleaning up temporary file: {tmp_file_path}")
                    os.remove(tmp_file_path)
                    logger.info(f"[INGEST] Temporary file removed")

        except Exception as index_error:
            # Log error but don't fail the upload
            indexing_error_time = time.time() - indexing_start
            logger.error(f"[INGEST] ✗ Indexing failed for document {document.id} after {indexing_error_time:.3f}s")
            logger.error(f"[INGEST] Error details: {type(index_error).__name__}: {str(index_error)}")
            logger.exception(f"[INGEST] Full traceback for indexing error:")

            # Update document with indexing failure
            logger.info(f"[INGEST] Updating document {document.id} with indexing failure status")
            await ingested_doc_crud.update_indexing_info(
                db=db,
                document_id=document.id,
                index_name=index_name,
                num_pages=0,
                page_image_s3_prefix="",
                status="failed",
                error_message=str(index_error),
            )
            logger.info(f"[INGEST] Document marked as indexing failed in database")

        # Refresh to get latest state
        await db.refresh(document)

        total_time = time.time() - start_time
        logger.info(f"[INGEST] ✓ File processing completed successfully in {total_time:.3f}s: {filename}")
        logger.info(f"[INGEST] Final document state - ID: {document.id}, status: {document.indexing_status}")

        return BatchIngestResult(
            filename=filename,
            success=True,
            document=_ingested_doc_to_response(document),
            error=None,
            duplicate=False,
        )

    except Exception as e:
        total_time = time.time() - start_time
        logger.error(f"[INGEST] ✗ Failed to process file {filename} after {total_time:.3f}s")
        logger.error(f"[INGEST] Error type: {type(e).__name__}")
        logger.error(f"[INGEST] Error details: {str(e)}")
        logger.exception(f"[INGEST] Full traceback:")
        return BatchIngestResult(
            filename=filename,
            success=False,
            document=None,
            error=str(e),
            duplicate=False,
        )


@router.post(
    "",
    response_model=BatchIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Batch Ingest Documents",
    description="Upload multiple PDF documents with metadata for indexing",
    responses={
        201: {"description": "Documents ingested successfully"},
        400: {"description": "Invalid request or file type"},
    },
)
async def batch_ingest_documents(
    files: list[UploadFile] = File(..., description="List of PDF files to upload"),
    index_name: Optional[str] = Form(None, description="Milvus collection name for indexing (defaults to configured index)"),
    doc_types: Optional[str] = Form(None, description="JSON array of document types (same order as files)"),
    doc_categories: Optional[str] = Form(None, description="JSON array of document categories (same order as files)"),
    metadata_list: Optional[str] = Form(None, description="JSON array of metadata objects (same order as files)"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Batch upload multiple PDF documents for compliance analysis.

    **Request:**
    - **files**: List of PDF files (multipart/form-data)
    - **index_name**: Optional Milvus collection name for data isolation (defaults to configured index)
    - **doc_types**: Optional JSON array of document types (e.g., ["contract", "invoice"])
    - **doc_categories**: Optional JSON array of categories (e.g., ["legal", "finance"])
    - **metadata_list**: Optional JSON array of metadata objects

    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/ingest" \\
      -F "files=@contract1.pdf" \\
      -F "files=@contract2.pdf" \\
      -F "index_name=client_acme" \\
      -F 'doc_types=["contract", "contract"]' \\
      -F 'doc_categories=["legal", "legal"]' \\
      -F 'metadata_list=[{"author": "John"}, {"author": "Jane"}]'
    ```

    **Process:**
    1. Validates file types (PDFs only)
    2. Checks for duplicates via SHA-256 hash
    3. Uploads files to S3
    4. Creates database records
    5. Generates page images
    6. Indexes in Milvus with ColPali embeddings
    7. Returns batch results with success/failure for each file

    **Returns:**
    Batch results with counts and per-file status.
    """
    batch_start_time = time.time()
    settings = get_settings()

    # Validate and sanitize index_name, or use default
    if index_name:
        validated_index_name = _validate_and_sanitize_index_name(index_name)
    else:
        validated_index_name = settings.indexing_default_collection
        logger.info(f"[INGEST-BATCH] No index_name provided, using default: {validated_index_name}")

    logger.info(f"[INGEST-BATCH] ========================================")
    logger.info(f"[INGEST-BATCH] Starting batch ingestion")
    logger.info(f"[INGEST-BATCH] Target index: {validated_index_name}")
    logger.info(f"[INGEST-BATCH] Number of files: {len(files)}")
    logger.info(f"[INGEST-BATCH] ========================================")

    # Parse optional JSON arrays
    doc_types_list = []
    doc_categories_list = []
    metadata_objects = []

    if doc_types:
        try:
            logger.info(f"[INGEST-BATCH] Parsing doc_types JSON array")
            doc_types_list = json.loads(doc_types)
            if not isinstance(doc_types_list, list):
                raise ValueError("doc_types must be a JSON array")
            logger.info(f"[INGEST-BATCH] Parsed {len(doc_types_list)} document types")
        except json.JSONDecodeError as e:
            logger.error(f"[INGEST-BATCH] Invalid JSON in doc_types: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON in doc_types: {e}",
            )

    if doc_categories:
        try:
            logger.info(f"[INGEST-BATCH] Parsing doc_categories JSON array")
            doc_categories_list = json.loads(doc_categories)
            if not isinstance(doc_categories_list, list):
                raise ValueError("doc_categories must be a JSON array")
            logger.info(f"[INGEST-BATCH] Parsed {len(doc_categories_list)} document categories")
        except json.JSONDecodeError as e:
            logger.error(f"[INGEST-BATCH] Invalid JSON in doc_categories: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON in doc_categories: {e}",
            )

    if metadata_list:
        try:
            logger.info(f"[INGEST-BATCH] Parsing metadata_list JSON array")
            metadata_objects = json.loads(metadata_list)
            if not isinstance(metadata_objects, list):
                raise ValueError("metadata_list must be a JSON array")
            logger.info(f"[INGEST-BATCH] Parsed {len(metadata_objects)} metadata objects")
        except json.JSONDecodeError as e:
            logger.error(f"[INGEST-BATCH] Invalid JSON in metadata_list: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON in metadata_list: {e}",
            )

    # Process each file
    logger.info(f"[INGEST-BATCH] Starting sequential processing of {len(files)} files")
    results = []
    for i, file in enumerate(files):
        file_num = i + 1
        logger.info(f"[INGEST-BATCH] ----------------------------------------")
        logger.info(f"[INGEST-BATCH] Processing file {file_num}/{len(files)}: {file.filename}")
        logger.info(f"[INGEST-BATCH] ----------------------------------------")

        # Get corresponding metadata if available
        doc_type = doc_types_list[i] if i < len(doc_types_list) else None
        doc_category = doc_categories_list[i] if i < len(doc_categories_list) else None
        metadata = metadata_objects[i] if i < len(metadata_objects) else None

        # Process file
        file_start = time.time()
        result = await _process_single_file(
            db=db,
            file=file,
            doc_type=doc_type,
            doc_category=doc_category,
            metadata=metadata,
            index_name=validated_index_name,
            settings=settings,
        )
        file_time = time.time() - file_start

        results.append(result)

        # Log result summary
        if result.success:
            if result.duplicate:
                logger.info(f"[INGEST-BATCH] File {file_num}/{len(files)} result: DUPLICATE (skipped) in {file_time:.3f}s")
            else:
                logger.info(f"[INGEST-BATCH] File {file_num}/{len(files)} result: SUCCESS in {file_time:.3f}s")
        else:
            logger.error(f"[INGEST-BATCH] File {file_num}/{len(files)} result: FAILED in {file_time:.3f}s - {result.error}")

    # Calculate stats
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    duplicates = sum(1 for r in results if r.duplicate)

    batch_total_time = time.time() - batch_start_time

    logger.info(f"[INGEST-BATCH] ========================================")
    logger.info(f"[INGEST-BATCH] Batch ingestion completed in {batch_total_time:.3f}s")
    logger.info(f"[INGEST-BATCH] Total files: {total}")
    logger.info(f"[INGEST-BATCH] Successful: {successful}")
    logger.info(f"[INGEST-BATCH] Failed: {failed}")
    logger.info(f"[INGEST-BATCH] Duplicates: {duplicates}")
    logger.info(f"[INGEST-BATCH] Average time per file: {batch_total_time/total:.3f}s")
    logger.info(f"[INGEST-BATCH] ========================================")

    return BatchIngestResponse(
        total=total,
        successful=successful,
        failed=failed,
        duplicates=duplicates,
        results=results,
    )


def _ingested_doc_to_summary(doc: IngestedDocument) -> IngestedDocumentSummary:
    """Convert IngestedDocument model to IngestedDocumentSummary."""
    return IngestedDocumentSummary(
        id=doc.id,
        filename=doc.filename,
        doc_type=doc.doc_type,
        doc_category=doc.doc_category,
        file_size=doc.file_size,
        file_size_mb=doc.file_size_mb,
        indexing_status=doc.indexing_status,
        index_name=doc.index_name,
        num_pages=doc.num_pages,
        indexed_at=doc.indexed_at,
        metadata=doc.doc_metadata or {},
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.get(
    "",
    response_model=PaginatedResponse[IngestedDocumentSummary],
    summary="List Ingested Documents",
    description="Get paginated list of ingested documents with optional filters",
)
async def list_ingested_documents(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    doc_type: Optional[str] = Query(None, description="Filter by document type"),
    doc_category: Optional[str] = Query(None, description="Filter by document category"),
    indexing_status: Optional[str] = Query(None, description="Filter by indexing status"),
    index_name: Optional[str] = Query(None, description="Filter by Milvus collection name"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve a paginated list of ingested documents.

    **Filters:**
    - doc_type: Document type classification
    - doc_category: Document category
    - indexing_status: pending, processing, completed, failed
    - index_name: Milvus collection name

    **Pagination:**
    - limit: maximum items per page (1-100)
    - offset: number of items to skip
    """
    documents, total = await ingested_doc_crud.list_ingested_documents(
        db=db,
        skip=offset,
        limit=limit,
        doc_type=doc_type,
        doc_category=doc_category,
        indexing_status=indexing_status,
        index_name=index_name,
    )

    return PaginatedResponse(
        items=[_ingested_doc_to_summary(doc) for doc in documents],
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/stats",
    response_model=IngestedDocumentStatsResponse,
    summary="Ingested Document Statistics",
    description="Get aggregated statistics for ingested documents",
)
async def get_ingested_document_stats(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get aggregated statistics about all ingested documents.

    Returns:
    - Total document count
    - Count by document type
    - Count by indexing status
    - Count by Milvus index
    - Total storage used
    """
    stats = await ingested_doc_crud.get_ingested_document_stats(db)

    return IngestedDocumentStatsResponse(
        total=stats["total"],
        by_type=stats["by_type"],
        by_status=stats["by_status"],
        by_index=stats["by_index"],
        total_size_bytes=stats["total_size_bytes"],
        total_size_mb=stats["total_size_mb"],
    )


@router.get(
    "/indexes",
    response_model=list[str],
    summary="List Unique Index Names",
    description="Get list of all unique Milvus collection/index names from ingested documents",
)
async def get_unique_indexes(
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get list of all unique index names from ingested documents.

    This endpoint returns all distinct Milvus collection names that have been used
    for document indexing. Useful for populating dropdowns or validating index names.

    Returns:
        List of unique index names (sorted alphabetically)
    """
    index_names = await ingested_doc_crud.get_unique_index_names(db)
    return index_names
