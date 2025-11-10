# Document Indexing and Search System

This module provides a unified `DocumentIndex` class for indexing PDF documents and performing semantic search using ColPali embeddings from a hosted Modal service and Milvus vector database.

## Features

- **Unified API**: Single `DocumentIndex` class for all indexing and search operations
- **PDF to Image Conversion**: Automatically converts PDF pages to images
- **Modal Service Integration**: Uses hosted ColPali embedding service (no local model required)
- **Milvus Vector DB**: Local vector database for fast retrieval
- **MaxSim Scoring**: Normalized Maximum Similarity scoring for accurate document ranking
- **Multiple Indexes**: Support for multiple independent vector indexes
- **Batch Operations**: Efficient batch processing and batch search
- **Built-in Result Formatting**: Pretty print search results

## Installation

### Python Dependencies

Install the project with all dependencies:
```bash
# From the project root
uv pip install -e .
# or
pip install -e .
```

The following dependencies are automatically installed:
- `pymilvus[milvus_lite]>=2.6.0` - Vector database
- `pdf2image>=1.17.0` - PDF to image conversion
- `pillow>=10.0.0` - Image processing
- `numpy>=2.0.0` - Array operations
- `requests>=2.32.0` - HTTP client for Modal service
- `tqdm>=4.67.0` - Progress bars

### System Dependencies

You must also install `poppler` for PDF conversion:
- **macOS**: `brew install poppler`
- **Ubuntu**: `apt-get install poppler-utils`
- **Windows**: Download from [poppler releases](https://github.com/oschwartz10612/poppler-windows/releases)

## Quick Start

### 1. Basic Usage with DocumentIndex Class

```python
from complianceguard.indexing import DocumentIndex

# Create an index instance with a specific index name
index = DocumentIndex(
    index_name="my_documents",
    milvus_uri="./artifacts/milvus.db"  # Local Milvus database
)

# Index a single PDF document
index.index_document("path/to/document.pdf")

# Search the indexed documents
results = index.search("What is the revenue?", topk=5)

# Pretty print results using built-in method
index.print_results("What is the revenue?", results)
```

### 2. Index Multiple Documents

```python
# Index multiple PDFs
pdf_files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
stats = index.index_documents(pdf_files)

print(f"Indexed {stats['total_pages']} pages from {stats['total_documents']} documents")
```

### 3. Multiple Indexes

You can create separate indexes for different document collections:

```python
# Index for financial documents
finance_index = DocumentIndex(index_name="finance_docs")
finance_index.index_document("financial_report.pdf")

# Index for legal documents
legal_index = DocumentIndex(index_name="legal_docs")
legal_index.index_document("contract.pdf")

# Search in specific index
finance_results = finance_index.search("revenue growth", topk=3)
legal_results = legal_index.search("terms and conditions", topk=3)
```

### 4. Batch Search

```python
queries = [
    "What is the revenue?",
    "Who are the key stakeholders?",
    "What are the risks?"
]

# Use batch_search for multiple queries
all_results = index.batch_search(queries, topk=3)

# Print results for each query
for query, results in zip(queries, all_results):
    index.print_results(query, results)
```

### 5. Index Management

```python
# Get index statistics
stats = index.get_stats()
print(f"Index: {stats['index_name']}")
print(f"Total pages: {stats['total_documents']}")

# Clear the index
index.clear_index()
```

## API Reference

### DocumentIndex Class

The `DocumentIndex` class provides all functionality for indexing and searching documents in one unified interface.

#### Constructor

```python
DocumentIndex(
    index_name: str,
    milvus_uri: str = "./artifacts/milvus.db",
    dim: int = 128
)
```

**Parameters:**
- `index_name`: Name of the vector index (Milvus collection)
- `milvus_uri`: Path to Milvus database file or remote URI
- `dim`: Dimensionality of ColPali embeddings (default: 128)

#### Indexing Methods

##### `index_document(pdf_path: str, batch_size: int = 4) -> int`

Index a single PDF document.

**Parameters:**
- `pdf_path`: Path to the PDF file
- `batch_size`: Number of images to process per batch (default: 4)

**Returns:** Number of pages indexed

##### `index_documents(pdf_paths: list[str], batch_size: int = 4) -> dict`

Index multiple PDF documents.

**Parameters:**
- `pdf_paths`: List of PDF file paths
- `batch_size`: Number of images to process per batch (default: 4)

**Returns:** Dictionary with indexing statistics

#### Search Methods

##### `search(query: str, topk: int = 5) -> list[tuple[float, int, str]]`

Search for documents using a text query.

**Parameters:**
- `query`: Text query to search for
- `topk`: Number of top results to return (default: 5)

**Returns:** List of tuples `(normalized_score, doc_id, filepath)` sorted by relevance

##### `batch_search(queries: list[str], topk: int = 5) -> list[list[tuple[float, int, str]]]`

Search for documents using multiple queries.

**Parameters:**
- `queries`: List of text queries
- `topk`: Number of top results to return per query (default: 5)

**Returns:** List of result lists, one per query

##### `print_results(query: str, results: list[tuple[float, int, str]], show_scores: bool = True) -> None`

Pretty print search results.

**Parameters:**
- `query`: The original query
- `results`: List of tuples from `search()` or `batch_search()`
- `show_scores`: Whether to show scores (default: True)

#### Management Methods

##### `get_stats() -> dict`

Get statistics about the indexed documents.

**Returns:** Dictionary with index statistics

##### `clear_index() -> None`

Clear all documents from the index.

## Command-Line Usage

### Index a Document

```bash
python -m complianceguard.indexing.milvus_index path/to/document.pdf
```

### Search Documents

You can search from the command line by running the module:
```bash
python -m complianceguard.indexing.milvus_index path/to/document.pdf
```

This will index the document and run an example search.

## Architecture

### How It Works

1. **PDF Conversion**: PDFs are converted to images (one per page)
2. **Embedding Generation**: Images are sent to Modal service which returns ColPali multi-vector embeddings
3. **Vector Storage**: Embeddings are stored in Milvus with metadata (doc_id, filepath, page number)
4. **Search**: Query text is converted to embeddings and MaxSim scoring finds most similar pages

### MaxSim Scoring

The system uses **Normalized Maximum Similarity (MaxSim)** scoring:

```
score = (Σ max(similarity(query_token_i, doc_token_j)) for all query tokens) / num_query_tokens
```

This ensures:
- Each query token finds its best matching document token
- Scores are normalized by query length for fair comparison
- Works well for multi-vector ColPali embeddings

## Advanced Configuration

### Custom Milvus URI

For remote Milvus server:
```python
index = DocumentIndex(
    index_name="my_docs",
    milvus_uri="http://localhost:19530"  # Remote Milvus server
)
```

### Batch Size Tuning

Adjust batch size based on available memory:
```python
# Smaller batches for limited memory
index.index_document("large_doc.pdf", batch_size=2)

# Larger batches for faster processing
index.index_document("doc.pdf", batch_size=8)
```

### Collection Management

```python
# Get index statistics
stats = index.get_stats()
print(f"Total pages: {stats['total_documents']}")
for doc in stats['documents']:
    print(f"  {doc['filepath']} (ID: {doc['doc_id']})")

# Clear an index
index.clear_index()
```

## Troubleshooting

### Modal Service Connection Issues

If you get connection errors:
1. Check your internet connection
2. Verify the Modal service URL is correct in `milvus_index.py`
3. Check if the service has rate limits

### PDF Conversion Errors

If `pdf2image` fails:
1. Ensure `poppler` is installed and in PATH
2. Try converting a simple PDF first to verify setup
3. Check PDF file is not corrupted

### Memory Issues

For large PDFs:
1. Reduce batch size: `batch_size=2`
2. Process PDFs one at a time
3. Close other applications to free memory

### Milvus Database Locked

If you get database locked errors:
1. Ensure no other process is using the database
2. Close all DocumentIndex instances
3. Delete lock files in the Milvus directory

## Performance Tips

1. **Batch Processing**: Process multiple pages in batches (4-8 pages) for better throughput
2. **Parallel Indexing**: Use multiple DocumentIndex instances for different indexes
3. **Index Cleanup**: Periodically clear old/unused indexes to save space
4. **Query Optimization**: Keep queries concise for faster embedding generation
5. **Use batch_search**: For multiple queries, use `batch_search()` instead of multiple `search()` calls

## Example Project Structure

```
my_project/
├── artifacts/
│   └── milvus.db          # Milvus vector database
├── documents/
│   ├── reports/
│   │   ├── q1_2024.pdf
│   │   └── q2_2024.pdf
│   └── contracts/
│       └── agreement.pdf
└── index_and_search.py    # Your indexing script
```

Sample script:
```python
from complianceguard.indexing import DocumentIndex

# Index reports
reports_index = DocumentIndex(index_name="reports")
reports_index.index_documents([
    "documents/reports/q1_2024.pdf",
    "documents/reports/q2_2024.pdf"
])

# Index contracts
contracts_index = DocumentIndex(index_name="contracts")
contracts_index.index_document("documents/contracts/agreement.pdf")

# Search and print results
results = reports_index.search("revenue growth", topk=3)
reports_index.print_results("revenue growth", results)
```

## License

This module is part of the ComplianceGuard project.

