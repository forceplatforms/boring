"""
Document query API endpoints for searching ingested documents.
"""

import logging
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.config import get_settings
from complianceguard.crud import ingested_document as ingested_doc_crud
from complianceguard.database import get_async_db
from complianceguard.indexing import DocumentIndex
from complianceguard.schemas.ingested_document import (
    QueryRequest,
    QueryResponse,
    QueryResultItem,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query")


@router.post(
    "",
    response_model=QueryResponse,
    summary="Query Documents",
    description="Search indexed documents using semantic search",
    responses={
        200: {"description": "Query executed successfully"},
        400: {"description": "Invalid query parameters"},
        500: {"description": "Search service error"},
    },
)
async def query_documents(
    request: QueryRequest = Body(
        ...,
        examples={
            "basic": {
                "summary": "Basic query",
                "value": {
                    "query": "What is the contract termination clause?",
                    "k": 5,
                    "min_threshold": 0.5,
                },
            },
            "advanced": {
                "summary": "Advanced query with custom index",
                "value": {
                    "query": "revenue growth and financial performance",
                    "k": 10,
                    "min_threshold": 0.6,
                    "index_name": "financial_docs",
                },
            },
        },
    ),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Search ingested documents using semantic search with ColPali embeddings.

    **Query Parameters:**
    - **query**: Natural language search query (required)
    - **k**: Number of top results to return (1-50, default: 5)
    - **min_threshold**: Minimum similarity score threshold (0.0-1.0, default: 0.0)
    - **index_name**: Milvus index to search (optional, uses default if not specified)

    **Example:**
    ```json
    {
      "query": "What are the payment terms?",
      "k": 5,
      "min_threshold": 0.5
    }
    ```

    **Process:**
    1. Validates query parameters
    2. Searches Milvus index using ColPali embeddings
    3. Filters results by minimum threshold
    4. Enriches results with document metadata from Postgres
    5. Returns ranked results with page images and metadata

    **Returns:**
    Query results with scores, page images, and document metadata.
    """
    settings = get_settings()

    # Determine index name
    index_name = request.index_name or settings.indexing_default_collection

    try:
        # Initialize DocumentIndex
        index = DocumentIndex(
            index_name=index_name,
            milvus_uri=settings.indexing_milvus_uri,
        )

        # Get index stats
        stats = await index.get_stats()

        # Perform search
        # Returns list of tuples: (score, doc_id, filepath, page_image_url)
        search_results = await index.search(request.query, topk=request.k)

        # Filter by minimum threshold
        filtered_results = [
            result for result in search_results if result[0] >= request.min_threshold
        ]

        # Build response items
        result_items = []
        for rank, (score, doc_id, filepath, page_url, file_hash) in enumerate(filtered_results, 1):
            # Parse filepath which is in format: "path/to/file.pdf#page=N"
            file_part = filepath.split("#")[0] if "#" in filepath else filepath
            page_num = None
            if "page=" in filepath:
                try:
                    page_num = int(filepath.split("page=")[1])
                except (ValueError, IndexError):
                    page_num = None

            filename = Path(file_part).name

            # Try to get document metadata from database using file hash
            document = None
            doc_type = None
            doc_category = None
            metadata = {}
            document_id = None

            if file_hash:
                try:
                    document = await ingested_doc_crud.get_ingested_document_by_hash(db, file_hash)
                    if document:
                        document_id = document.id
                        doc_type = document.doc_type
                        doc_category = document.doc_category
                        metadata = document.doc_metadata or {}
                        # Use the original filename from database
                        filename = document.filename
                except Exception as e:
                    logger.warning(f"Could not fetch document metadata for hash {file_hash}: {e}")

            # Build result item
            result_item = QueryResultItem(
                rank=rank,
                score=float(score),
                page_number=page_num or 0,
                filepath=file_part,
                filename=filename,
                page_image_url=page_url if page_url else None,
                document_id=document_id,
                doc_type=doc_type,
                doc_category=doc_category,
                metadata=metadata,
            )
            result_items.append(result_item)

        # Build response
        return QueryResponse(
            query=request.query,
            k=request.k,
            min_threshold=request.min_threshold,
            index_name=index_name,
            total_documents_in_index=stats["total_documents"],
            results_count=len(result_items),
            results=result_items,
        )

    except Exception as e:
        logger.error(f"Query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search service error: {str(e)}",
        )
