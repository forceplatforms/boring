"""Document indexing into Milvus using ColPali embeddings from Modal service.

This module provides a class-based interface for indexing PDF documents into Milvus
and performing MaxSim-based semantic search using embeddings from a hosted Modal service.
"""

import base64
import io
import os

import numpy as np
import requests
from pdf2image import convert_from_path
from PIL import Image
from pymilvus import MilvusClient
from tqdm import tqdm

from complianceguard.indexing.milvus_retriever import MilvusRetriever


class DocumentIndex:
    """A complete document indexing and search system using ColPali embeddings from Modal.

    This class provides a complete workflow for:
    1. Converting PDF documents to images
    2. Getting embeddings from the hosted Modal service
    3. Indexing embeddings in a local Milvus vector database
    4. Performing semantic search using normalized MaxSim scoring

    Each instance manages a specific vector index (collection) in Milvus.

    Example:
        >>> index = DocumentIndex(index_name="my_docs")
        >>> index.index_document("report.pdf")
        >>> results = index.search("What is the revenue?", topk=5)
        >>> index.print_results("What is the revenue?", results)
    """
    
    # Modal service endpoint
    MODAL_URL = "https://fluidzero--colpali-indexing-fastapi-app.modal.run/get_embeddings"
    
    def __init__(
        self,
        index_name: str,
        milvus_uri: str = "./artifacts/milvus.db",
        dim: int = 128
    ):
        """Initialize the document index.

        Args:
            index_name: Name of the vector index (Milvus collection) to use
            milvus_uri: URI for Milvus connection (default: "./artifacts/milvus.db")
            dim: Dimensionality of ColPali embeddings (default: 128)
        """
        self.index_name = index_name
        self.milvus_uri = milvus_uri
        self.dim = dim
        
        # Ensure directory exists for local file URIs
        if not milvus_uri.startswith(("http://", "https://")):
            dir_path = os.path.dirname(milvus_uri)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
        
        # Initialize Milvus client
        self.client = MilvusClient(uri=milvus_uri)
        
        # Initialize retriever
        self.retriever = MilvusRetriever(
            milvus_client=self.client,
            collection_name=index_name,
            dim=dim
        )
        
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
    
    def _get_embeddings_from_modal(
        self,
        images: list[Image.Image] | None = None,
        queries: list[str] | None = None
    ) -> dict:
        """Get embeddings from the Modal service.
        
        Args:
            images: List of PIL Image objects (optional)
            queries: List of text queries (optional)
            
        Returns:
            Dictionary with 'image_embeddings' and/or 'query_embeddings'
            
        Raises:
            requests.exceptions.RequestException: If the API call fails
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
            response = requests.post(
                self.MODAL_URL,
                headers=headers,
                json=payload,
                timeout=300
            )
            response.raise_for_status()

            data = response.json()
            print("Received embeddings from Modal service")

            return data
            
        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            print(f"Response: {response.text}")
            raise
        except requests.exceptions.RequestException as e:
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
    
    def index_document(self, pdf_path: str, batch_size: int = 4) -> int:
        """Index a single PDF document.
        
        Args:
            pdf_path: Path to the PDF file
            batch_size: Number of images to process in each batch (default: 4)
            
        Returns:
            Number of pages indexed
        """
        print(f"\n{'='*60}")
        print(f"Indexing document: {pdf_path}")
        print(f"{'='*60}")
        
        # Convert PDF to images
        images = self._pdf_to_images(pdf_path)
        num_pages = len(images)
        
        # Get the next available doc_id
        existing_docs = self.retriever.get_all_doc_ids()
        next_doc_id = max([doc_id for doc_id, _ in existing_docs], default=-1) + 1
        
        # Process images in batches
        for i in tqdm(range(0, num_pages, batch_size), desc="Processing batches"):
            batch_images = images[i:i + batch_size]
            
            # Get embeddings from Modal service
            result = self._get_embeddings_from_modal(images=batch_images)
            
            if "image_embeddings" not in result:
                raise ValueError("No image embeddings returned from Modal service")
            
            # Insert each page's embeddings into Milvus
            for page_idx, embedding in enumerate(result["image_embeddings"]):
                actual_page_idx = i + page_idx
                doc_id = next_doc_id + actual_page_idx
                
                # Convert to numpy array
                embedding_array = np.array(embedding, dtype=np.float32)
                
                data = {
                    "colbert_vecs": embedding_array,
                    "doc_id": doc_id,
                    "filepath": f"{pdf_path}#page={actual_page_idx + 1}",
                }
                
                self.retriever.insert(data)
        
        print(f"Successfully indexed {num_pages} pages from {pdf_path}")
        
        # Ensure collection is loaded for searching
        self.client.load_collection(collection_name=self.index_name)
        
        return num_pages
    
    def index_documents(self, pdf_paths: list[str], batch_size: int = 4) -> dict:
        """Index multiple PDF documents.
        
        Args:
            pdf_paths: List of paths to PDF files
            batch_size: Number of images to process in each batch (default: 4)
            
        Returns:
            Dictionary with indexing statistics
        """
        total_pages = 0
        total_docs = len(pdf_paths)
        
        for pdf_path in pdf_paths:
            num_pages = self.index_document(pdf_path, batch_size=batch_size)
            total_pages += num_pages
        
        print(f"\n{'='*60}")
        print("Indexing complete!")
        print(f"Total documents processed: {total_docs}")
        print(f"Total pages indexed: {total_pages}")
        print(f"{'='*60}\n")
        
        return {
            "total_documents": total_docs,
            "total_pages": total_pages
        }
    
    def search(self, query: str, topk: int = 5) -> list[tuple[float, int, str]]:
        """Search for documents using a text query with normalized MaxSim scoring.
        
        This method:
        1. Generates ColPali embeddings for the query using Modal service
        2. Performs normalized MaxSim-based search in Milvus
        3. Returns ranked results with normalized scores
        
        Args:
            query: Text query to search for
            topk: Number of top results to return (default: 5)
            
        Returns:
            List of tuples (normalized_maxsim_score, doc_id, filepath) sorted by relevance
            
        Example:
            >>> index = DocumentIndex("my_index")
            >>> results = index.search("What is the revenue?", topk=3)
            >>> index.print_results("What is the revenue?", results)
        """
        print(f"Searching for: '{query}'")
        
        # Get query embeddings from Modal service
        result = self._get_embeddings_from_modal(queries=[query])
        
        if "query_embeddings" not in result or len(result["query_embeddings"]) == 0:
            raise ValueError("No query embeddings returned from Modal service")
        
        # Get the first query's embeddings
        query_embedding = np.array(result["query_embeddings"][0], dtype=np.float32)
        
        print(f"Query embedding shape: {query_embedding.shape}")
        print(f"Performing normalized MaxSim search (top-{topk})...")
        
        # Perform search using the retriever
        results = self.retriever.search(query_embedding, topk=topk)
        
        return results

    def batch_search(self, queries: list[str], topk: int = 5) -> list[list[tuple[float, int, str]]]:
        """Search for documents using multiple queries.

        Args:
            queries: List of text queries to search for
            topk: Number of top results to return per query (default: 5)

        Returns:
            List of result lists, one per query. Each result list contains tuples
            of (normalized_maxsim_score, doc_id, filepath)

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
        results: list[tuple[float, int, str]],
        show_scores: bool = True
    ) -> None:
        """Pretty print search results.

        Args:
            query: The original query
            results: List of tuples (score, doc_id, filepath) from search()
            show_scores: Whether to show normalized MaxSim scores (default: True)

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

        for i, (score, doc_id, filepath) in enumerate(results, 1):
            print(f"\n{i}. {filepath}")
            if show_scores:
                print(f"   Normalized MaxSim Score: {score:.4f}")
            print(f"   Document ID: {doc_id}")

        print(f"\n{'='*80}\n")

    def clear_index(self) -> None:
        """Clear all documents from the index.
        
        This drops the entire collection. A new collection will be created
        automatically on the next indexing operation.
        """
        if self.client.has_collection(self.index_name):
            print(f"Dropping collection: {self.index_name}")
            self.client.drop_collection(collection_name=self.index_name)
            print(f"Collection '{self.index_name}' cleared")
            # Recreate empty collection
            self._ensure_collection_exists()
        else:
            print(f"Collection '{self.index_name}' does not exist")
    
    def get_stats(self) -> dict:
        """Get statistics about the indexed documents.
        
        Returns:
            Dictionary with index statistics
        """
        all_docs = self.retriever.get_all_doc_ids()
        
        return {
            "index_name": self.index_name,
            "total_documents": len(all_docs),
            "documents": [{"doc_id": doc_id, "filepath": filepath} for doc_id, filepath in all_docs]
        }


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

