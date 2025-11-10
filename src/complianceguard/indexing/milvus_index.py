"""Document indexing into Milvus using ColPali embeddings from Modal service.

This module provides a class-based interface for indexing PDF documents into Milvus
and performing MaxSim-based semantic search using embeddings from a hosted Modal service.
"""

import asyncio
import base64
import hashlib
import io
import os
from typing import Optional

import numpy as np
import httpx
from pdf2image import convert_from_path
from PIL import Image
from pymilvus import MilvusClient
from tqdm import tqdm

from complianceguard.config import get_settings
from complianceguard.indexing.index_tracker import IndexTracker
from complianceguard.indexing.milvus_retriever import MilvusRetriever
from complianceguard.indexing.page_storage import (
    batch_upload_pages_to_s3,
    ensure_page_images_bucket_exists,
)


class DocumentIndex:
    """A complete document indexing and search system using ColPali embeddings from Modal.

    This class provides a complete workflow for:
    1. Converting PDF documents to images
    2. Getting embeddings from the hosted Modal service
    3. Indexing embeddings in a local Milvus vector database
    4. Performing semantic search using normalized MaxSim scoring

    Each instance manages a specific vector index (collection) in Milvus.

    Example:
        >>> from complianceguard.indexing import DocumentIndex
        >>> index = DocumentIndex(index_name="my_docs")
        >>> index.index_document("report.pdf")
        >>> results = index.search("What is the revenue?", topk=5)
        >>> index.print_results("What is the revenue?", results)
    """

    def __init__(
        self,
        index_name: Optional[str] = None,
        milvus_uri: Optional[str] = None,
        dim: Optional[int] = None,
        tracker_file: Optional[str] = None,
        modal_url: Optional[str] = None
    ):
        """Initialize the document index.

        Args:
            index_name: Name of the vector index (Milvus collection).
                       If None, uses config default.
            milvus_uri: URI for Milvus connection. If None, uses config default.
            dim: Dimensionality of ColPali embeddings. If None, uses config default.
            tracker_file: Path to the index tracker file. If None, uses config default.
            modal_url: Modal service endpoint URL. If None, uses config default.
        """
        # Get settings from config
        settings = get_settings()

        # Use provided values or fall back to config defaults
        self.index_name = index_name or settings.indexing_default_collection
        self.milvus_uri = milvus_uri or settings.indexing_milvus_uri
        self.dim = dim or settings.indexing_embedding_dim
        self.modal_url = modal_url or settings.indexing_modal_url
        tracker_file = tracker_file or settings.indexing_tracker_file

        # Ensure directory exists for local file URIs
        if not self.milvus_uri.startswith(("http://", "https://")):
            dir_path = os.path.dirname(self.milvus_uri)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
        
        # Initialize Milvus client
        self.client = MilvusClient(uri=self.milvus_uri)

        # Initialize retriever
        self.retriever = MilvusRetriever(
            milvus_client=self.client,
            collection_name=self.index_name,
            dim=self.dim
        )
        
        # Initialize index tracker
        self.tracker = IndexTracker(tracker_file=tracker_file)
        
        # Create collection and indexes if they don't exist
        self._ensure_collection_exists()
    
    def _ensure_collection_exists(self) -> None:
        """Ensure the collection exists, creating it if necessary."""
        if not self.client.has_collection(self.index_name):
            print(f"Collection '{self.index_name}' does not exist. Creating...")
            self.retriever.create_collection()
            self.retriever.create_index()
            self.retriever.create_scalar_index()
            print(f"Collection '{self.index_name}' created successfully")
            # Load the newly created collection
            self.client.load_collection(collection_name=self.index_name)
            print(f"Collection '{self.index_name}' loaded")
        else:
            print(f"Using existing collection: {self.index_name}")
            # Ensure collection is loaded
            self.client.load_collection(collection_name=self.index_name)
    
    def _image_to_base64(self, image: Image.Image) -> str:
        """Convert PIL Image to base64 string.
        
        Args:
            image: PIL Image object
            
        Returns:
            Base64 encoded string
        """
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    async def _get_embeddings_from_modal(
        self,
        images: list[Image.Image] | None = None,
        queries: list[str] | None = None
    ) -> dict:
        """Get embeddings from the Modal service (async).

        Args:
            images: List of PIL Image objects (optional)
            queries: List of text queries (optional)

        Returns:
            Dictionary with 'image_embeddings' and/or 'query_embeddings'

        Raises:
            httpx.HTTPStatusError: If the API call fails
        """
        payload = {}

        # Process images if provided
        if images:
            print(f"Encoding {len(images)} image(s) to base64...")
            base64_images = [self._image_to_base64(img) for img in images]
            payload["images"] = base64_images

        # Process queries if provided
        if queries:
            payload["queries"] = queries

        if not payload:
            raise ValueError("Either images or queries must be provided")

        headers = {"Content-Type": "application/json", "accept": "application/json"}

        print("Sending request to Modal service...")
        try:
            # Use async httpx client with proper timeouts
            timeout = httpx.Timeout(300.0, connect=10.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.modal_url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()

                data = response.json()
                print("Received embeddings from Modal service")

                return data

        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e}")
            print(f"Response: {e.response.text}")
            raise
        except httpx.RequestError as e:
            print(f"Request error: {e}")
            raise
    
    def _pdf_to_images(self, pdf_path: str) -> list[Image.Image]:
        """Convert PDF to list of PIL Images.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of PIL Image objects, one per page
        """
        print(f"Converting PDF to images: {pdf_path}")
        try:
            images = convert_from_path(pdf_path)
            print(f"Converted {len(images)} pages")
            return images
        except Exception as e:
            print(f"Error converting PDF: {e}")
            raise
    
    async def index_document(self, pdf_path: str, batch_size: int = 4, force: bool = False, file_hash: str = None) -> int:
        """Index a single PDF document.

        Args:
            pdf_path: Path to the PDF file
            batch_size: Number of images to process in each batch (default: 4)
            force: Force re-indexing even if document is already indexed (default: False)
            file_hash: SHA-256 hash of the file for metadata lookup (optional)

        Returns:
            Number of pages indexed (0 if skipped)
        """
        print(f"\n{'='*60}")
        print(f"Indexing document: {pdf_path}")
        print(f"{'='*60}")

        # Check if document is already indexed
        if not force and self.tracker.is_indexed(pdf_path, self.index_name):
            indexed_info = self.tracker.get_indexed_info(pdf_path, self.index_name)
            print(f"⏭️  Document already indexed in collection '{self.index_name}'")
            print(f"   Indexed at: {indexed_info['indexed_at']}")
            print(f"   Pages: {indexed_info['num_pages']}")
            print("   Skipping to avoid duplicates...")
            print("   (Use force=True to re-index)")
            return 0

        # Convert PDF to images (run in thread pool to avoid blocking)
        images = await asyncio.to_thread(self._pdf_to_images, pdf_path)
        num_pages = len(images)

        # Compute document hash for consistent S3 keys
        doc_hash = hashlib.sha256(pdf_path.encode()).hexdigest()[:16]

        # Upload page images to S3 (async operation)
        settings = get_settings()
        page_image_urls = []
        if settings.indexing_s3_enabled:
            print(f"\n📤 Uploading {num_pages} page images to S3...")
            try:
                # Await async upload
                page_image_urls = await batch_upload_pages_to_s3(
                    images,
                    pdf_path,
                    start_page=1,
                    doc_hash=doc_hash
                )
                print(f"✓ Uploaded {len([u for u in page_image_urls if u])} pages to S3")
            except Exception as e:
                print(f"⚠️  S3 upload failed: {e}")
                if settings.indexing_local_fallback:
                    print("   Continuing with local fallback...")
                    page_image_urls = [""] * num_pages
        else:
            page_image_urls = [""] * num_pages

        # Get the next available doc_id (run in thread pool to avoid blocking)
        existing_docs = await asyncio.to_thread(self.retriever.get_all_doc_ids)
        next_doc_id = max([doc_id for doc_id, _ in existing_docs], default=-1) + 1

        # Process images in batches
        for i in tqdm(range(0, num_pages, batch_size), desc="Processing batches"):
            batch_images = images[i:i + batch_size]

            # Get embeddings from Modal service
            result = await self._get_embeddings_from_modal(images=batch_images)

            if "image_embeddings" not in result:
                raise ValueError("No image embeddings returned from Modal service")

            # Insert each page's embeddings into Milvus
            for page_idx, embedding in enumerate(result["image_embeddings"]):
                actual_page_idx = i + page_idx
                doc_id = next_doc_id + actual_page_idx

                # Convert to numpy array
                embedding_array = np.array(embedding, dtype=np.float32)

                # Get S3 URL for this page
                page_image_url = page_image_urls[actual_page_idx] if actual_page_idx < len(page_image_urls) else ""

                data = {
                    "colbert_vecs": embedding_array,
                    "doc_id": doc_id,
                    "filepath": f"{pdf_path}#page={actual_page_idx + 1}",
                    "page_image_url": page_image_url or "",
                }

                # Add file_hash if provided (for metadata lookup)
                if file_hash:
                    data["file_hash"] = file_hash

                # Insert into Milvus (run in thread pool to avoid blocking)
                await asyncio.to_thread(self.retriever.insert, data)
        
        print(f"✓ Successfully indexed {num_pages} pages from {pdf_path}")
        
        # Record in tracker (run in thread pool to avoid blocking)
        await asyncio.to_thread(
            self.tracker.record_indexing,
            filepath=pdf_path,
            collection_name=self.index_name,
            num_pages=num_pages,
            metadata={
                "batch_size": batch_size,
                "milvus_uri": self.milvus_uri
            }
        )

        # Ensure collection is loaded for searching (run in thread pool)
        await asyncio.to_thread(self.client.load_collection, collection_name=self.index_name)
        
        return num_pages
    
    def index_documents(self, pdf_paths: list[str], batch_size: int = 4, force: bool = False) -> dict:
        """Index multiple PDF documents.
        
        Args:
            pdf_paths: List of paths to PDF files
            batch_size: Number of images to process in each batch (default: 4)
            force: Force re-indexing even if documents are already indexed (default: False)
            
        Returns:
            Dictionary with indexing statistics
        """
        total_pages = 0
        total_docs = len(pdf_paths)
        docs_indexed = 0
        docs_skipped = 0
        
        for pdf_path in pdf_paths:
            num_pages = self.index_document(pdf_path, batch_size=batch_size, force=force)
            if num_pages > 0:
                docs_indexed += 1
                total_pages += num_pages
            else:
                docs_skipped += 1
        
        print(f"\n{'='*60}")
        print("Indexing complete!")
        print(f"Total documents processed: {total_docs}")
        print(f"  - Newly indexed: {docs_indexed} ({total_pages} pages)")
        print(f"  - Skipped (already indexed): {docs_skipped}")
        print(f"{'='*60}\n")
        
        return {
            "total_documents": total_docs,
            "documents_indexed": docs_indexed,
            "documents_skipped": docs_skipped,
            "total_pages": total_pages
        }
    
    async def search(self, query: str, topk: int = 5) -> list[tuple[float, int, str, str, str]]:
        """Search for documents using a text query with normalized MaxSim scoring.

        This method:
        1. Generates ColPali embeddings for the query using Modal service
        2. Performs normalized MaxSim-based search in Milvus
        3. Returns ranked results with normalized scores and page image URLs

        Args:
            query: Text query to search for
            topk: Number of top results to return (default: 5)

        Returns:
            List of tuples (normalized_maxsim_score, doc_id, filepath, page_image_url, file_hash) sorted by relevance

        Example:
            >>> index = DocumentIndex("my_index")
            >>> results = await index.search("What is the revenue?", topk=3)
            >>> index.print_results("What is the revenue?", results)
        """
        print(f"Searching for: '{query}'")

        # Get query embeddings from Modal service
        result = await self._get_embeddings_from_modal(queries=[query])
        
        if "query_embeddings" not in result or len(result["query_embeddings"]) == 0:
            raise ValueError("No query embeddings returned from Modal service")
        
        # Get the first query's embeddings
        query_embedding = np.array(result["query_embeddings"][0], dtype=np.float32)
        
        print(f"Query embedding shape: {query_embedding.shape}")
        print(f"Performing normalized MaxSim search (top-{topk})...")

        # Perform search using the retriever (run in thread pool to avoid blocking)
        results = await asyncio.to_thread(self.retriever.search, query_embedding, topk=topk)

        return results

    def batch_search(self, queries: list[str], topk: int = 5) -> list[list[tuple[float, int, str, str]]]:
        """Search for documents using multiple queries.

        Args:
            queries: List of text queries to search for
            topk: Number of top results to return per query (default: 5)

        Returns:
            List of result lists, one per query. Each result list contains tuples
            of (normalized_maxsim_score, doc_id, filepath, page_image_url)

        Example:
            >>> index = DocumentIndex("my_index")
            >>> queries = ["What is revenue?", "Who are the authors?"]
            >>> all_results = index.batch_search(queries, topk=3)
            >>> for query, results in zip(queries, all_results):
            ...     print(f"Query: {query}, Results: {len(results)}")
        """
        all_results = []
        for i, query in enumerate(queries, 1):
            print(f"\nQuery {i}/{len(queries)}: '{query}'")
            results = self.search(query, topk=topk)
            all_results.append(results)

        return all_results

    def print_results(
        self,
        query: str,
        results: list[tuple[float, int, str, str]],
        show_scores: bool = True,
        show_urls: bool = True
    ) -> None:
        """Pretty print search results.

        Args:
            query: The original query
            results: List of tuples (score, doc_id, filepath, page_image_url) from search()
            show_scores: Whether to show normalized MaxSim scores (default: True)
            show_urls: Whether to show page image URLs (default: True)

        Example:
            >>> index = DocumentIndex("my_index")
            >>> results = index.search("What is the revenue?", topk=3)
            >>> index.print_results("What is the revenue?", results)
        """
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")

        if not results:
            print("No results found.")
            return

        for i, (score, doc_id, filepath, page_image_url) in enumerate(results, 1):
            print(f"\n{i}. {filepath}")
            if show_scores:
                print(f"   Normalized MaxSim Score: {score:.4f}")
            print(f"   Document ID: {doc_id}")
            if show_urls and page_image_url:
                print(f"   📷 Page Image: {page_image_url}")

        print(f"\n{'='*80}\n")

    def clear_index(self) -> None:
        """Clear all documents from the index.
        
        This drops the entire collection and clears tracker entries.
        A new collection will be created automatically on the next indexing operation.
        """
        if self.client.has_collection(self.index_name):
            print(f"Dropping collection: {self.index_name}")
            self.client.drop_collection(collection_name=self.index_name)
            print(f"Collection '{self.index_name}' cleared")
            
            # Clear tracker entries for this collection
            removed_count = self.tracker.clear_collection(self.index_name)
            print(f"Cleared {removed_count} tracker entries for collection '{self.index_name}'")
            
            # Recreate empty collection
            self._ensure_collection_exists()
        else:
            print(f"Collection '{self.index_name}' does not exist")
    
    async def get_stats(self) -> dict:
        """Get statistics about the indexed documents.

        Returns:
            Dictionary with index statistics including tracker information
        """
        # Run blocking operations in thread pool
        all_docs = await asyncio.to_thread(self.retriever.get_all_doc_ids)
        tracked_docs = await asyncio.to_thread(self.tracker.get_all_indexed, collection_name=self.index_name)

        return {
            "index_name": self.index_name,
            "total_documents": len(all_docs),
            "documents": [{"doc_id": doc_id, "filepath": filepath} for doc_id, filepath in all_docs],
            "tracked_documents": len(tracked_docs),
            "tracker_info": tracked_docs
        }
    
    def get_tracker_stats(self) -> dict:
        """Get statistics from the index tracker.
        
        Returns:
            Dictionary with tracker statistics
        """
        return self.tracker.get_stats()
    
    def print_tracker_stats(self) -> None:
        """Print statistics from the index tracker."""
        self.tracker.print_stats()


if __name__ == "__main__":
    # Example usage
    import sys

    # Create an index instance
    index = DocumentIndex(
        index_name="my_documents",
        milvus_uri="./artifacts/milvus.db"
    )

    # Check if PDF path provided
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]

        if os.path.exists(pdf_path):
            # Index the document
            index.index_document(pdf_path)

            # Show stats
            stats = index.get_stats()
            print("\nIndex statistics:")
            print(f"Total pages indexed: {stats['total_documents']}")

            # Example search
            query = "What is this document about?"
            results = index.search(query, topk=3)

            # Print results using built-in method
            index.print_results(query, results)
        else:
            print(f"Error: PDF file not found: {pdf_path}")
    else:
        print("Usage: python milvus_index.py <path_to_pdf>")
        print("Example: python milvus_index.py document.pdf")

