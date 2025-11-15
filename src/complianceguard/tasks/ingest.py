"""
Celery tasks for document ingestion and indexing.

This module contains background tasks that handle the time-consuming process
of converting PDFs to images, generating embeddings, and indexing in Milvus.
"""

import asyncio
import logging
import os
import tempfile
import time
from typing import Optional
from uuid import UUID

from complianceguard.celery_app import app
from complianceguard.config import get_settings
from complianceguard.database import get_async_db
from complianceguard.crud import ingested_document as ingested_doc_crud
from complianceguard.indexing import DocumentIndex
from complianceguard.utils.file_storage import get_file_from_s3
from complianceguard.services.landing_ai import get_landing_ai_client
from complianceguard.models.document_chunk import DocumentChunk
from complianceguard.models.document_split import DocumentSplit

logger = logging.getLogger(__name__)
settings = get_settings()


@app.task(
    bind=True,
    name="process_document_indexing",
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,  # 1 hour
    retry_jitter=True,
)
def process_document_indexing(
    self,
    document_id: str,
    index_name: str,
    s3_key: str,
    file_hash: str,
    filename: str,
) -> dict:
    """
    Background task to index a document in Milvus.

    This task performs the following steps:
    1. Mark document as 'processing' in database
    2. Download PDF from S3
    3. Convert PDF to images
    4. Generate ColPali embeddings
    5. Upload page images to S3
    6. Insert vectors into Milvus
    7. Update document status to 'completed' or 'failed'

    Args:
        self: Task instance (bound)
        document_id: UUID of the document to index
        index_name: Milvus collection name
        s3_key: S3 key where the PDF is stored
        file_hash: SHA-256 hash of the file
        filename: Original filename

    Returns:
        dict: Task result with status and metadata
    """
    task_id = self.request.id
    logger.info(f"[TASK {task_id}] Starting indexing for document {document_id}")

    # Run async indexing in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            _async_index_document(
                document_id=UUID(document_id),
                index_name=index_name,
                s3_key=s3_key,
                file_hash=file_hash,
                filename=filename,
                task_id=task_id,
            )
        )
        logger.info(f"[TASK {task_id}] ✓ Indexing completed successfully")
        return result
    except Exception as e:
        logger.error(f"[TASK {task_id}] ✗ Indexing failed: {e}")
        raise
    finally:
        loop.close()


async def _async_index_document(
    document_id: UUID,
    index_name: str,
    s3_key: str,
    file_hash: str,
    filename: str,
    task_id: str,
) -> dict:
    """
    Async helper function to perform document indexing.

    This function contains the actual indexing logic extracted from the API endpoint.
    """
    indexing_start = time.time()

    # Create new database session for this task
    async for db in get_async_db():
        try:
            # Load document from database
            logger.info(f"[TASK {task_id}] Loading document {document_id} from database")
            document = await ingested_doc_crud.get_ingested_document(db=db, document_id=document_id)
            if not document:
                raise ValueError(f"Document {document_id} not found in database")

            # Mark as processing
            logger.info(f"[TASK {task_id}] Marking document as 'processing'")
            document.mark_as_indexing()
            await db.commit()
            await db.refresh(document)

            # Index document in Milvus
            try:
                logger.info(f"[TASK {task_id}] Initializing DocumentIndex")
                index = DocumentIndex(
                    index_name=index_name,
                    milvus_uri=settings.indexing_milvus_uri,
                )

                # Download file from S3
                logger.info(f"[TASK {task_id}] Downloading PDF from S3: {s3_key}")
                download_start = time.time()
                file_bytes = await get_file_from_s3(s3_key)
                download_time = time.time() - download_start
                logger.info(
                    f"[TASK {task_id}] PDF downloaded in {download_time:.3f}s "
                    f"({len(file_bytes)} bytes)"
                )

                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(file_bytes)
                    tmp_file_path = tmp_file.name
                logger.info(f"[TASK {task_id}] Temporary file created: {tmp_file_path}")

                try:
                    # Index document (convert to images, generate embeddings, upload to Milvus)
                    logger.info(f"[TASK {task_id}] Starting PDF indexing process")
                    index_start = time.time()
                    num_pages = await index.index_document(tmp_file_path, file_hash=file_hash)
                    index_time = time.time() - index_start
                    logger.info(
                        f"[TASK {task_id}] PDF indexed successfully in {index_time:.3f}s - "
                        f"{num_pages} pages processed"
                    )

                    # Get page image S3 prefix
                    page_image_prefix = f"pages/{index_name}/{file_hash}/{filename}/"
                    logger.info(f"[TASK {task_id}] Page images at: {page_image_prefix}")

                    # Extract text with Landing AI and create chunks
                    logger.info(f"[TASK {task_id}] Starting Landing AI text extraction")
                    extraction_start = time.time()
                    try:
                        landing_ai_client = get_landing_ai_client()
                        (
                            extracted_text,
                            extraction_metadata,
                            chunks_list,
                            splits_list,
                        ) = await landing_ai_client.parse_and_prepare_chunks(
                            document_id=document_id,
                            file_content=file_bytes,
                            filename=filename,
                        )

                        extraction_time = time.time() - extraction_start
                        logger.info(
                            f"[TASK {task_id}] Landing AI extraction completed in {extraction_time:.3f}s - "
                            f"Created {len(chunks_list)} chunks, {len(splits_list)} splits"
                        )

                        # Add chunks to database
                        logger.info(f"[TASK {task_id}] Saving {len(chunks_list)} chunks to database")
                        for chunk in chunks_list:
                            db.add(chunk)

                        # Add splits to database
                        if splits_list:
                            logger.info(f"[TASK {task_id}] Saving {len(splits_list)} splits to database")
                            for split in splits_list:
                                db.add(split)

                        # Commit chunks and splits
                        await db.commit()
                        logger.info(f"[TASK {task_id}] ✓ Chunks and splits saved successfully")

                    except Exception as extraction_error:
                        extraction_time = time.time() - extraction_start
                        logger.error(
                            f"[TASK {task_id}] ✗ Landing AI extraction failed after {extraction_time:.3f}s: {extraction_error}"
                        )
                        # Don't fail the entire task - Milvus indexing still succeeded
                        # Chunks can be created later via retry endpoint
                        logger.warning(
                            f"[TASK {task_id}] Continuing without chunks - "
                            f"Milvus indexing succeeded but text extraction failed"
                        )

                    # Update document with indexing success
                    logger.info(f"[TASK {task_id}] Updating document with success status")
                    await ingested_doc_crud.update_indexing_info(
                        db=db,
                        document_id=document_id,
                        index_name=index_name,
                        num_pages=num_pages,
                        page_image_s3_prefix=page_image_prefix,
                        status="completed",
                    )

                    indexing_total_time = time.time() - indexing_start
                    logger.info(
                        f"[TASK {task_id}] ✓ Complete indexing pipeline finished in "
                        f"{indexing_total_time:.3f}s"
                    )

                    return {
                        "status": "completed",
                        "document_id": str(document_id),
                        "num_pages": num_pages,
                        "indexing_time": indexing_total_time,
                    }

                finally:
                    # Clean up temporary file
                    if os.path.exists(tmp_file_path):
                        logger.info(f"[TASK {task_id}] Cleaning up temporary file")
                        os.remove(tmp_file_path)

            except Exception as index_error:
                # Log error and update document with failure status
                indexing_error_time = time.time() - indexing_start
                logger.error(
                    f"[TASK {task_id}] ✗ Indexing failed after {indexing_error_time:.3f}s"
                )
                logger.error(f"[TASK {task_id}] Error: {type(index_error).__name__}: {index_error}")
                logger.exception(f"[TASK {task_id}] Full traceback:")

                # Update document with indexing failure
                await ingested_doc_crud.update_indexing_info(
                    db=db,
                    document_id=document_id,
                    index_name=index_name,
                    num_pages=0,
                    page_image_s3_prefix="",
                    status="failed",
                    error_message=str(index_error),
                )
                logger.info(f"[TASK {task_id}] Document marked as failed in database")

                # Re-raise exception for Celery to handle retries
                raise index_error

        finally:
            # Ensure DB session is closed
            await db.close()
