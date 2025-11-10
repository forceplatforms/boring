"""Milvus-based retriever with normalized MaxSim scoring for ColPali embeddings.

This module implements a multi-vector retrieval system that stores ColPali embeddings
in Milvus and uses normalized MaxSim (Maximum Similarity) scoring for ranking documents.
Unlike simple similarity search, MaxSim compares query tokens with document tokens
by finding the most similar document token for each query token, then normalizes
the score by the number of query tokens for fair comparison across different query lengths.
"""

import concurrent.futures
from typing import Any, Dict, List, Tuple

import numpy as np
from pymilvus import DataType, MilvusClient


class MilvusRetriever:
    def __init__(self, milvus_client: MilvusClient, collection_name: str, dim: int = 128):
        """Initialize the retriever.
        
        Args:
            milvus_client: Connected Milvus client instance
            collection_name: Name of the collection to use
            dim: Dimensionality of ColPali embeddings (default: 128)
        """
        self.collection_name = collection_name
        self.client = milvus_client
        self.dim = dim
        
        # Load collection if it exists
        if self.client.has_collection(collection_name=self.collection_name):
            self.client.load_collection(collection_name=self.collection_name)

    def create_collection(self) -> None:
        """Create a new Milvus collection for storing multi-vector embeddings.
        
        Schema:
        - pk: Primary key (auto-generated)
        - vector: The embedding vector (FLOAT_VECTOR)
        - seq_id: Sequence position in the original embedding list (INT16)
        - doc_id: Document ID this embedding belongs to (INT64)
        - doc: Document metadata (filepath, etc.) stored in first vector only (VARCHAR)
        """
        # Drop existing collection if present
        if self.client.has_collection(collection_name=self.collection_name):
            self.client.drop_collection(collection_name=self.collection_name)
        
        # Define schema
        schema = self.client.create_schema(
            auto_id=True,
            enable_dynamic_fields=True,
        )
        schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True)
        schema.add_field(
            field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=self.dim
        )
        schema.add_field(field_name="seq_id", datatype=DataType.INT16)
        schema.add_field(field_name="doc_id", datatype=DataType.INT64)
        schema.add_field(field_name="doc", datatype=DataType.VARCHAR, max_length=65535)

        self.client.create_collection(
            collection_name=self.collection_name, schema=schema
        )
        print(f"Created collection: {self.collection_name}")

    def create_index(self) -> None:
        """Create vector index for fast similarity search.
        
        Uses AUTOINDEX which automatically selects the best index type for the environment.
        Inner Product metric is used because ColPali embeddings are L2-normalized.
        Note: In local mode, Milvus supports FLAT, IVF_FLAT, and AUTOINDEX.
        """
        self.client.release_collection(collection_name=self.collection_name)
        
        # Drop existing index if present
        try:
            self.client.drop_index(
                collection_name=self.collection_name, index_name="vector_index"
            )
        except Exception:
            pass  # Index might not exist yet
        
        # Create new index
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_name="vector_index",
            index_type="AUTOINDEX",
            metric_type="IP",  # Inner Product for normalized vectors
        )

        self.client.create_index(
            collection_name=self.collection_name, index_params=index_params, sync=True
        )
        print(f"Created vector index on collection: {self.collection_name}")

    def create_scalar_index(self) -> None:
        """Create scalar index on doc_id field for fast filtering during reranking."""
        self.client.release_collection(collection_name=self.collection_name)

        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="doc_id",
            index_name="doc_id_index",
            index_type="INVERTED",  # Inverted index for fast filtering
        )

        self.client.create_index(
            collection_name=self.collection_name, index_params=index_params, sync=True
        )
        print(f"Created scalar index on doc_id field")

    def insert(self, data: Dict[str, Any]) -> None:
        """Insert a document's multi-vector embeddings into the collection.
        
        Args:
            data: Dictionary containing:
                - colbert_vecs: numpy array of shape (seq_length, dim)
                - doc_id: Unique document identifier
                - filepath: Document filepath (optional metadata)
        """
        colbert_vecs = data["colbert_vecs"]
        doc_id = data["doc_id"]
        filepath = data.get("filepath", "")
        
        seq_length = len(colbert_vecs)
        
        # Prepare data: each vector becomes a separate row
        # Only the first vector stores the filepath metadata
        insert_data = []
        for i in range(seq_length):
            insert_data.append({
                "vector": colbert_vecs[i].tolist() if isinstance(colbert_vecs[i], np.ndarray) else colbert_vecs[i],
                "seq_id": i,
                "doc_id": doc_id,
                "doc": filepath if i == 0 else "",
            })
        
        self.client.insert(self.collection_name, insert_data)

    def search(self, query_embedding: np.ndarray, topk: int = 5) -> List[Tuple[float, int, str]]:
        """Search for most relevant documents using normalized MaxSim scoring.
        
        Process:
        1. Perform initial vector search for each query token embedding
        2. Collect candidate document IDs
        3. Rerank candidates using full normalized MaxSim calculation
        
        Normalized MaxSim formula:
        score(query, doc) = (Σ max(similarity(q_i, d_j)) for all query tokens i) / num_query_tokens
        
        This normalization ensures scores are comparable across queries with different lengths.
        
        Args:
            query_embedding: Query embeddings array of shape (num_tokens, dim)
            topk: Number of top results to return
            
        Returns:
            List of tuples (normalized_score, doc_id, filepath) sorted by score (highest first)
        """
        search_params = {"metric_type": "IP", "params": {}}
        
        # Search with each query token embedding to get candidate documents
        # We retrieve more candidates (50) than needed to ensure good coverage
        results = self.client.search(
            self.collection_name,
            query_embedding.tolist() if isinstance(query_embedding, np.ndarray) else query_embedding,
            limit=50,  # Retrieve top 50 for each query token
            output_fields=["vector", "seq_id", "doc_id", "doc"],
            search_params=search_params,
        )
        
        # Collect unique document IDs from initial search
        doc_ids = set()
        for result_list in results:
            for result in result_list:
                doc_ids.add(result["entity"]["doc_id"])
        
        # Rerank documents using full MaxSim calculation
        def rerank_single_doc(doc_id: int) -> Tuple[float, int, str]:
            """Compute normalized MaxSim score for a single document.
            
            Retrieves all embeddings for the document and computes:
            score = (Σ max(dot(query_token_i, doc_token_j)) for all i) / num_query_tokens
            """
            # Fetch all vectors for this document
            doc_colbert_vecs = self.client.query(
                collection_name=self.collection_name,
                filter=f"doc_id == {doc_id}",
                output_fields=["seq_id", "vector", "doc"],
                limit=1000,  # Max sequence length we support
            )
            
            if not doc_colbert_vecs:
                return (0.0, doc_id, "")
            
            # Stack document vectors into matrix
            doc_vecs = np.vstack([
                vec["vector"] for vec in doc_colbert_vecs
            ])
            
            # Get filepath from first vector
            filepath = doc_colbert_vecs[0].get("doc", "")
            
            # Compute MaxSim: for each query token, find max similarity to any doc token
            # Shape: (num_query_tokens, num_doc_tokens)
            similarity_matrix = np.dot(query_embedding, doc_vecs.T)
            
            # For each query token, take maximum similarity
            # Then sum across all query tokens
            maxsim_score = similarity_matrix.max(axis=1).sum()
            
            # Normalize by number of query tokens to get average similarity per token
            num_query_tokens = query_embedding.shape[0]
            normalized_maxsim_score = maxsim_score / num_query_tokens
            
            return (float(normalized_maxsim_score), doc_id, filepath)
        
        # Parallel reranking for efficiency
        scores = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = {
                executor.submit(rerank_single_doc, doc_id): doc_id 
                for doc_id in doc_ids
            }
            for future in concurrent.futures.as_completed(futures):
                scores.append(future.result())
        
        # Sort by score (highest first) and return top-k
        scores.sort(key=lambda x: x[0], reverse=True)
        return scores[:topk]

    def get_document_by_id(self, doc_id: int) -> Dict[str, Any]:
        """Retrieve all embeddings and metadata for a document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            Dictionary with document embeddings and metadata
        """
        results = self.client.query(
            collection_name=self.collection_name,
            filter=f"doc_id == {doc_id}",
            output_fields=["seq_id", "vector", "doc"],
            limit=1000,
        )
        
        if not results:
            return {}
        
        # Sort by sequence ID
        results.sort(key=lambda x: x["seq_id"])
        
        return {
            "doc_id": doc_id,
            "filepath": results[0].get("doc", ""),
            "embeddings": np.vstack([r["vector"] for r in results]),
            "num_tokens": len(results)
        }
    
    def get_all_doc_ids(self) -> List[Tuple[int, str]]:
        """Get all unique document IDs and their filepaths from the collection.
        
        Returns:
            List of tuples (doc_id, filepath) sorted by doc_id
        """
        # Query to get all documents (only first vector per doc has filepath)
        results = self.client.query(
            collection_name=self.collection_name,
            filter="seq_id == 0",  # Only get first vector of each document
            output_fields=["doc_id", "doc"],
            limit=10000,  # Adjust if you have more documents
        )
        
        # Extract unique doc_ids and filepaths
        doc_info = [(r["doc_id"], r.get("doc", "")) for r in results]
        
        # Sort by doc_id
        doc_info.sort(key=lambda x: x[0])
        
        return doc_info

