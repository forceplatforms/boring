"""
Landing AI Document AI Engine (ADE) integration.
Handles document parsing and text extraction using Landing AI's ADE Parse API.
"""

import asyncio
import logging
from typing import Optional
from uuid import UUID

import httpx
from pydantic import BaseModel, Field

from complianceguard.config import get_settings
from complianceguard.models.document_chunk import DocumentChunk
from complianceguard.models.document_split import DocumentSplit

logger = logging.getLogger(__name__)
settings = get_settings()


class ADEChunk(BaseModel):
    """A single content chunk from parsed document."""

    markdown: str
    type: str
    id: str
    grounding: Optional[dict] = None


class ADEMetadata(BaseModel):
    """Metadata about the parsing operation."""

    filename: Optional[str] = None
    org_id: Optional[str] = None
    page_count: int = 0
    duration_ms: int = 0
    credit_usage: int = 0
    job_id: Optional[str] = None
    version: Optional[str] = None


class ADEParseResponse(BaseModel):
    """Response from Landing AI ADE Parse API."""

    markdown: str
    chunks: list[ADEChunk] = Field(default_factory=list)
    metadata: ADEMetadata
    grounding: Optional[dict] = None
    splits: Optional[list] = None


class LandingAIClient:
    """Client for Landing AI Document AI Engine API."""

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize Landing AI client.

        Args:
            api_key: Landing AI API key (defaults to settings)
            base_url: Base URL for API (defaults to settings)
        """
        self.api_key = api_key or settings.landing_ai_api_key
        self.base_url = base_url or settings.landing_ai_base_url
        self.timeout = settings.landing_ai_timeout_seconds

        if not self.api_key:
            logger.warning("Landing AI API key not configured")

    async def parse_document(
        self,
        file_content: bytes,
        filename: str,
        split_by_page: bool = False,
    ) -> ADEParseResponse:
        """
        Parse document using Landing AI ADE Parse API.

        Args:
            file_content: Binary content of the document
            filename: Original filename
            split_by_page: Whether to split document by pages

        Returns:
            Parsed document response with text and metadata

        Raises:
            ValueError: If API key is not configured
            httpx.HTTPError: If API request fails
        """
        if not self.api_key:
            raise ValueError(
                "Landing AI API key not configured. Set LANDING_AI_API_KEY environment variable."
            )

        # Prepare request
        url = f"{self.base_url}/ade/parse"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Prepare multipart form data
        files = {"document": (filename, file_content)}
        data = {}

        if split_by_page:
            data["split"] = "page"

        # Make async request
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(f"Sending document to Landing AI: {filename}")

                response = await client.post(
                    url, headers=headers, files=files, data=data
                )
                response.raise_for_status()

                # Parse response
                result_data = response.json()
                parsed_response = ADEParseResponse(**result_data)

                logger.info(
                    f"Successfully parsed document: {filename}, "
                    f"pages={parsed_response.metadata.page_count}, "
                    f"chunks={len(parsed_response.chunks)}, "
                    f"credits={parsed_response.metadata.credit_usage}"
                )

                return parsed_response

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Landing AI API error: {e.response.status_code} - {e.response.text}"
                )
                raise
            except httpx.RequestError as e:
                logger.error(f"Request error calling Landing AI: {e}")
                raise
            except Exception as e:
                logger.error(f"Unexpected error parsing document: {e}")
                raise

    async def parse_document_with_retries(
        self,
        file_content: bytes,
        filename: str,
        split_by_page: bool = False,
    ) -> ADEParseResponse:
        """
        Parse document with automatic retry logic on failure.

        Args:
            file_content: Binary content of the document
            filename: Original filename
            split_by_page: Whether to split document by pages

        Returns:
            Parsed document response with text and metadata

        Raises:
            ValueError: If API key is not configured
            httpx.HTTPError: If all retry attempts fail
        """
        max_retries = settings.landing_ai_max_retries or 3

        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to parse document (attempt {attempt + 1}/{max_retries})")
                return await self.parse_document(
                    file_content=file_content,
                    filename=filename,
                    split_by_page=split_by_page,
                )
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 422:
                    # Don't retry on validation errors (e.g., password-protected PDF)
                    logger.error(f"Document validation error: {e.response.text}")
                    raise
                elif e.response.status_code >= 500:
                    # Retry on server errors
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(
                            f"Landing AI server error (attempt {attempt + 1}/{max_retries}). "
                            f"Retrying in {wait_time} seconds..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All retry attempts failed: {e}")
                        raise
                else:
                    # Don't retry on client errors (400-499 except 500+)
                    raise
            except (httpx.RequestError, httpx.TimeoutException) as e:
                # Network or timeout errors - retry
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Network/timeout error (attempt {attempt + 1}/{max_retries}). "
                        f"Retrying in {wait_time} seconds..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"All retry attempts failed: {e}")
                    raise
            except Exception as e:
                # Unexpected errors - don't retry
                logger.error(f"Unexpected error, not retrying: {e}")
                raise

    def extract_tables(self, response: ADEParseResponse) -> list[dict]:
        """
        Extract table chunks from parsed response.

        Args:
            response: Parsed document response

        Returns:
            List of table chunks with metadata
        """
        tables = []
        for chunk in response.chunks:
            if chunk.type == "table":
                tables.append(
                    {
                        "id": chunk.id,
                        "markdown": chunk.markdown,
                        "grounding": chunk.grounding,
                    }
                )
        return tables

    def extract_text_by_type(self, response: ADEParseResponse, chunk_type: str) -> str:
        """
        Extract text from chunks of specific type.

        Args:
            response: Parsed document response
            chunk_type: Type of chunks to extract (text, table, figure, etc.)

        Returns:
            Combined text from matching chunks
        """
        matching_chunks = [
            chunk.markdown for chunk in response.chunks if chunk.type == chunk_type
        ]
        return "\n\n".join(matching_chunks)

    def get_extraction_metadata(
        self, response: ADEParseResponse, file_size_bytes: int
    ) -> dict:
        """
        Build extraction metadata dict for database storage.

        Args:
            response: Parsed document response
            file_size_bytes: Original file size

        Returns:
            Metadata dictionary for storage
        """
        # Count chunks by type
        chunk_types = {}
        for chunk in response.chunks:
            chunk_types[chunk.type] = chunk_types.get(chunk.type, 0) + 1

        return {
            "extraction_method": "landing_ai_ade",
            "model_version": response.metadata.version or "dpt-2-latest",
            "file_size": file_size_bytes,
            "num_pages": response.metadata.page_count,
            "num_chunks": len(response.chunks),
            "chunk_types": chunk_types,
            "tables_found": chunk_types.get("table", 0),
            "text_length": len(response.markdown),
            "processing_time_ms": response.metadata.duration_ms,
            "credit_usage": response.metadata.credit_usage,
            "job_id": response.metadata.job_id,
            "confidence_score": 0.98,  # ADE doesn't provide this, using high default
        }

    async def parse_and_prepare_chunks(
        self,
        document_id: UUID,
        file_content: bytes,
        filename: str,
        split_by_page: bool = False,
    ) -> tuple[str, dict, list[DocumentChunk], list[DocumentSplit]]:
        """
        Parse document and prepare chunk and split objects for database storage.

        Args:
            document_id: UUID of the parent document
            file_content: Binary content of the document
            filename: Original filename
            split_by_page: Whether to split document by pages

        Returns:
            Tuple of (markdown_text, extraction_metadata, chunks_list, splits_list)

        Raises:
            ValueError: If API key is not configured
            httpx.HTTPError: If API request fails
        """
        # Parse document with retry logic
        response = await self.parse_document_with_retries(
            file_content, filename, split_by_page=split_by_page
        )

        # Get markdown text and metadata
        markdown_text = response.markdown
        extraction_metadata = self.get_extraction_metadata(response, len(file_content))

        # Create DocumentChunk objects from response.chunks
        chunks_list = []
        for idx, chunk_data in enumerate(response.chunks):
            # Extract grounding information
            grounding = chunk_data.grounding or {}
            page_number = grounding.get("page", 1)  # Default to page 1 if not provided
            bounding_box = grounding.get("box", {})

            # Create DocumentChunk instance
            chunk = DocumentChunk(
                document_id=document_id,
                chunk_id=chunk_data.id,
                chunk_type=chunk_data.type,
                chunk_order=idx,
                content=chunk_data.markdown,
                page_number=page_number,
                bounding_box=bounding_box,
                split_identifier=None,  # Will be set later if splits exist
            )
            chunks_list.append(chunk)

        logger.info(f"Created {len(chunks_list)} chunks for document {document_id}")

        # Create DocumentSplit objects from response.splits (if present)
        splits_list = []
        if response.splits:
            for idx, split_data in enumerate(response.splits):
                # Extract split data
                split_class = split_data.get("class", "section")
                identifier = split_data.get("identifier", f"split_{idx}")
                pages = split_data.get("pages", [])
                markdown = split_data.get("markdown", "")
                # Landing AI docs show "chunks" not "chunk_ids"
                chunk_ids = split_data.get("chunks", split_data.get("chunk_ids", []))

                # Create DocumentSplit instance
                split = DocumentSplit(
                    document_id=document_id,
                    class_=split_class,
                    identifier=identifier,
                    pages=pages,
                    markdown=markdown,
                    chunk_ids=chunk_ids,
                    split_order=idx,
                )
                splits_list.append(split)

                # Update chunks with split_identifier
                for chunk in chunks_list:
                    if chunk.chunk_id in chunk_ids:
                        chunk.split_identifier = identifier

            logger.info(f"Created {len(splits_list)} splits for document {document_id}")

        return markdown_text, extraction_metadata, chunks_list, splits_list


# Global client instance
_landing_ai_client: Optional[LandingAIClient] = None


def get_landing_ai_client() -> LandingAIClient:
    """
    Get or create global Landing AI client instance.

    Returns:
        Landing AI client instance
    """
    global _landing_ai_client
    if _landing_ai_client is None:
        _landing_ai_client = LandingAIClient()
    return _landing_ai_client


async def parse_document_with_landing_ai(
    file_content: bytes, filename: str
) -> tuple[str, dict]:
    """
    Parse document using Landing AI and return extracted text and metadata.

    Args:
        file_content: Binary file content
        filename: Original filename

    Returns:
        Tuple of (extracted_text, extraction_metadata)

    Raises:
        ValueError: If API key not configured
        httpx.HTTPError: If API request fails
    """
    client = get_landing_ai_client()

    # Parse document
    response = await client.parse_document(file_content, filename)

    # Extract text (full markdown)
    extracted_text = response.markdown

    # Build metadata
    metadata = client.get_extraction_metadata(response, len(file_content))

    return extracted_text, metadata
