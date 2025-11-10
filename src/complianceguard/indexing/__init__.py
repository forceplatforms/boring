"""Document indexing and search module using ColPali embeddings from Modal service.

This module provides a complete workflow for indexing PDF documents into Milvus
and performing semantic search using normalized MaxSim scoring.

Example:
    >>> from complianceguard.indexing import DocumentIndex
    >>> index = DocumentIndex(index_name="my_docs")
    >>> index.index_document("document.pdf")
    >>> results = index.search("What is the revenue?", topk=5)
    >>> index.print_results("What is the revenue?", results)
"""

from complianceguard.indexing.milvus_index import DocumentIndex
from complianceguard.indexing.milvus_retriever import MilvusRetriever

__all__ = [
    "DocumentIndex",
    "MilvusRetriever",
]

