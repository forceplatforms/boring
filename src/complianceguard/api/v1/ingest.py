"""
Document ingestion API endpoints for batch PDF uploads.
"""

import json
import logging
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
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
)
from complianceguard.utils.file_storage import (
    calculate_file_hash,
    upload_file_to_s3,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest")


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
        settings: Application settings

    Returns:
        BatchIngestResult with success/failure status
    """
    filename = file.filename or "unknown.pdf"

    try:
        # Validate file type (only PDFs)
        if file.content_type != "application/pdf":
            return BatchIngestResult(
                filename=filename,
                success=False,
                document=None,
                error="Invalid file type. Only PDFs are supported.",
                duplicate=False,
            )

        # Read file content once
        file_content = await file.read()
        await file.seek(0)  # Reset for potential reuse

        # Calculate file hash for deduplication
        file_hash = calculate_file_hash(file_content)

        # Check for duplicates
        existing_doc = await ingested_doc_crud.get_ingested_document_by_hash(db, file_hash)
        if existing_doc:
            return BatchIngestResult(
                filename=filename,
                success=True,
                document=_ingested_doc_to_response(existing_doc),
                error=None,
                duplicate=True,
            )

        # Upload to S3
        await file.seek(0)  # Reset for S3 upload
        s3_key, _, file_size, mime_type = await upload_file_to_s3(file)

        # Create database record
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

        # Start background indexing (mark as processing)
        document.mark_as_indexing()
        await db.commit()
        await db.refresh(document)

        # Index document in Milvus
        try:
            # Initialize DocumentIndex
            index = DocumentIndex(
                index_name=settings.indexing_default_collection,
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
            file_bytes = await get_file_from_s3(s3_key)

            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(file_bytes)
                tmp_file_path = tmp_file.name

            try:
                # Index document (pass file_hash for metadata lookup)
                num_pages = await index.index_document(tmp_file_path, file_hash=file_hash)

                # Get page image S3 prefix
                page_image_prefix = f"pages/{file_hash}/{filename}/"

                # Update document with indexing success
                await ingested_doc_crud.update_indexing_info(
                    db=db,
                    document_id=document.id,
                    index_name=settings.indexing_default_collection,
                    num_pages=num_pages,
                    page_image_s3_prefix=page_image_prefix,
                    status="completed",
                )

                logger.info(f"Successfully indexed document {document.id} with {num_pages} pages")

            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)

        except Exception as index_error:
            # Log error but don't fail the upload
            logger.error(f"Failed to index document {document.id}: {index_error}")

            # Update document with indexing failure
            await ingested_doc_crud.update_indexing_info(
                db=db,
                document_id=document.id,
                index_name=settings.indexing_default_collection,
                num_pages=0,
                page_image_s3_prefix="",
                status="failed",
                error_message=str(index_error),
            )

        # Refresh to get latest state
        await db.refresh(document)

        return BatchIngestResult(
            filename=filename,
            success=True,
            document=_ingested_doc_to_response(document),
            error=None,
            duplicate=False,
        )

    except Exception as e:
        logger.error(f"Failed to process file {filename}: {e}")
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
    doc_types: Optional[str] = Form(None, description="JSON array of document types (same order as files)"),
    doc_categories: Optional[str] = Form(None, description="JSON array of document categories (same order as files)"),
    metadata_list: Optional[str] = Form(None, description="JSON array of metadata objects (same order as files)"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Batch upload multiple PDF documents for compliance analysis.

    **Request:**
    - **files**: List of PDF files (multipart/form-data)
    - **doc_types**: Optional JSON array of document types (e.g., ["contract", "invoice"])
    - **doc_categories**: Optional JSON array of categories (e.g., ["legal", "finance"])
    - **metadata_list**: Optional JSON array of metadata objects

    **Example:**
    ```bash
    curl -X POST "http://localhost:8000/api/v1/ingest" \\
      -F "files=@contract1.pdf" \\
      -F "files=@contract2.pdf" \\
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
    settings = get_settings()

    # Parse optional JSON arrays
    doc_types_list = []
    doc_categories_list = []
    metadata_objects = []

    if doc_types:
        try:
            doc_types_list = json.loads(doc_types)
            if not isinstance(doc_types_list, list):
                raise ValueError("doc_types must be a JSON array")
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON in doc_types: {e}",
            )

    if doc_categories:
        try:
            doc_categories_list = json.loads(doc_categories)
            if not isinstance(doc_categories_list, list):
                raise ValueError("doc_categories must be a JSON array")
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON in doc_categories: {e}",
            )

    if metadata_list:
        try:
            metadata_objects = json.loads(metadata_list)
            if not isinstance(metadata_objects, list):
                raise ValueError("metadata_list must be a JSON array")
        except json.JSONDecodeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSON in metadata_list: {e}",
            )

    # Process each file
    results = []
    for i, file in enumerate(files):
        # Get corresponding metadata if available
        doc_type = doc_types_list[i] if i < len(doc_types_list) else None
        doc_category = doc_categories_list[i] if i < len(doc_categories_list) else None
        metadata = metadata_objects[i] if i < len(metadata_objects) else None

        # Process file
        result = await _process_single_file(
            db=db,
            file=file,
            doc_type=doc_type,
            doc_category=doc_category,
            metadata=metadata,
            settings=settings,
        )
        results.append(result)

    # Calculate stats
    total = len(results)
    successful = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if not r.success)
    duplicates = sum(1 for r in results if r.duplicate)

    return BatchIngestResponse(
        total=total,
        successful=successful,
        failed=failed,
        duplicates=duplicates,
        results=results,
    )
