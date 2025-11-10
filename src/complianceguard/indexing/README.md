# Document Indexing and Search System

This module provides a unified `DocumentIndex` class for indexing PDF documents and performing semantic search using ColPali embeddings from a hosted Modal service and Milvus vector database.

## Features

- **Unified API**: Single `DocumentIndex` class for all indexing and search operations
- **PDF to Image Conversion**: Automatically converts PDF pages to images
- **Modal Service Integration**: Uses hosted ColPali embedding service (no local model required)
- **Milvus Vector DB**: Local vector database for fast retrieval
- **MaxSim Scoring**: Normalized Maximum Similarity scoring for accurate document ranking
- **Multiple Indexes**: Support for multiple independent vector indexes
- **Duplicate Prevention**: Automatic tracking to prevent re-indexing the same documents
- **Index Tracking**: Persistent log of indexed documents with collection tracking
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

## Duplicate Prevention & Tracking

The indexing system automatically tracks which documents have been indexed to prevent duplicates. This is handled by the `IndexTracker` component.

### How It Works

1. **Automatic Tracking**: When you index a document, it's automatically recorded in a tracker log
2. **Collection-Specific**: Documents are tracked per collection, so the same document can be in multiple collections
3. **File Hash-Based**: Uses SHA-256 file hashing to detect identical documents even if renamed
4. **Persistent Log**: Tracker data is stored in `artifacts/index_tracker.json`

### Duplicate Prevention Example

```python
from complianceguard.indexing import DocumentIndex

index = DocumentIndex(
    index_name="my_docs",
    milvus_uri="./artifacts/milvus.db"
)

# First time - will index the document
num_pages = index.index_document("report.pdf")
print(f"Indexed {num_pages} pages")  # Output: Indexed 10 pages

# Second time - will skip (already indexed)
num_pages = index.index_document("report.pdf")
print(f"Indexed {num_pages} pages")  # Output: Indexed 0 pages
# Console will show: "⏭️  Document already indexed in collection 'my_docs'"

# Force re-indexing if needed
num_pages = index.index_document("report.pdf", force=True)
print(f"Indexed {num_pages} pages")  # Output: Indexed 10 pages (re-indexed)
```

### Tracker Statistics

```python
# View tracker statistics
index.print_tracker_stats()

# Or get programmatic access
stats = index.get_tracker_stats()
print(f"Total documents tracked: {stats['total_documents']}")
print(f"Total collections: {stats['total_collections']}")

# View documents in a specific collection
for coll_name, coll_data in stats['collections'].items():
    print(f"\n{coll_name}:")
    print(f"  Documents: {coll_data['document_count']}")
    print(f"  Total pages: {coll_data['total_pages']}")
```

### Multiple Collections

The tracker prevents duplicates within each collection separately:

```python
# Create two different indexes
index1 = DocumentIndex(index_name="collection_1")
index2 = DocumentIndex(index_name="collection_2")

# Index into collection_1
index1.index_document("report.pdf")  # ✓ Indexed

# Index into collection_2 (allowed - different collection)
index2.index_document("report.pdf")  # ✓ Indexed

# Try again in collection_1 (prevented)
index1.index_document("report.pdf")  # ⏭️ Skipped
```

### Batch Indexing with Tracking

```python
pdf_files = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]

# First run - indexes all new documents
stats = index.index_documents(pdf_files)
print(f"Indexed: {stats['documents_indexed']}")  # Output: 3
print(f"Skipped: {stats['documents_skipped']}")  # Output: 0

# Second run - skips all (already indexed)
stats = index.index_documents(pdf_files)
print(f"Indexed: {stats['documents_indexed']}")  # Output: 0
print(f"Skipped: {stats['documents_skipped']}")  # Output: 3
```

### Clearing the Tracker

When you clear an index, the tracker is also cleared:

```python
# Clear both the index and tracker entries
index.clear_index()
```

### Direct Tracker Access

For advanced use cases, you can access the tracker directly:

```python
from complianceguard.indexing import IndexTracker

# Create tracker instance
tracker = IndexTracker(tracker_file="./artifacts/index_tracker.json")

# Check if a document is indexed
is_indexed = tracker.is_indexed("report.pdf", "my_collection")

# Get indexing info
info = tracker.get_indexed_info("report.pdf", "my_collection")
if info:
    print(f"Indexed at: {info['indexed_at']}")
    print(f"Pages: {info['num_pages']}")

# Remove a specific entry
tracker.remove_entry("report.pdf", "my_collection")

# Clear all entries for a collection
tracker.clear_collection("my_collection")
```

## API Reference

### DocumentIndex Class

The `DocumentIndex` class provides all functionality for indexing and searching documents in one unified interface.

#### Constructor

```python
DocumentIndex(
    index_name: str,
    milvus_uri: str = "./artifacts/milvus.db",
    dim: int = 128,
    tracker_file: str = "./artifacts/index_tracker.json"
)
```

**Parameters:**
- `index_name`: Name of the vector index (Milvus collection)
- `milvus_uri`: Path to Milvus database file or remote URI
- `dim`: Dimensionality of ColPali embeddings (default: 128)
- `tracker_file`: Path to the index tracker JSON file (default: "./artifacts/index_tracker.json")

#### Indexing Methods

##### `index_document(pdf_path: str, batch_size: int = 4, force: bool = False) -> int`

Index a single PDF document. Automatically checks if document is already indexed and skips if found.

**Parameters:**
- `pdf_path`: Path to the PDF file
- `batch_size`: Number of images to process per batch (default: 4)
- `force`: Force re-indexing even if document is already indexed (default: False)

**Returns:** Number of pages indexed (0 if skipped due to duplicate)

##### `index_documents(pdf_paths: list[str], batch_size: int = 4, force: bool = False) -> dict`

Index multiple PDF documents. Automatically skips documents that are already indexed.

**Parameters:**
- `pdf_paths`: List of PDF file paths
- `batch_size`: Number of images to process per batch (default: 4)
- `force`: Force re-indexing even if documents are already indexed (default: False)

**Returns:** Dictionary with indexing statistics including:
- `total_documents`: Total number of documents processed
- `documents_indexed`: Number of documents newly indexed
- `documents_skipped`: Number of documents skipped (already indexed)
- `total_pages`: Total pages indexed

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

Get statistics about the indexed documents, including tracker information.

**Returns:** Dictionary with index statistics including:
- `index_name`: Name of the collection
- `total_documents`: Number of documents in the index
- `documents`: List of indexed documents
- `tracked_documents`: Number of documents tracked
- `tracker_info`: Detailed tracker information

##### `clear_index() -> None`

Clear all documents from the index and remove tracker entries for this collection.

##### `get_tracker_stats() -> dict`

Get statistics from the index tracker across all collections.

**Returns:** Dictionary with tracker statistics including:
- `total_documents`: Total documents tracked across all collections
- `total_collections`: Number of collections with tracked documents
- `collections`: Detailed information per collection

##### `print_tracker_stats() -> None`

Print a formatted display of tracker statistics.

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

## Search Scripts and Examples

### Interactive Search Script

After indexing documents, you can use the standalone `search_example.py` script for quick searches:

**Interactive Mode** (default):
```bash
python src/complianceguard/indexing/search_example.py
```

This starts an interactive search session where you can type queries and see results immediately. Type `quit` or press Ctrl+C to exit.

**Single Query Mode**:
```bash
# Basic single query
python src/complianceguard/indexing/search_example.py --query "What is machine learning?"

# Search in a specific index
python src/complianceguard/indexing/search_example.py --index-name my_documents --query "API documentation"

# Get more results
python src/complianceguard/indexing/search_example.py --query "neural networks" --topk 10
```

**Options**:
- `--query`: Single search query (if not provided, enters interactive mode)
- `--index-name`: Name of the index to search (default: `example_docs`)
- `--milvus-uri`: Path to Milvus database (default: `./artifacts/milvus_example.db`)
- `--topk`: Number of results to return (default: 5)

### Example Usage Script

The `example_usage.py` script provides comprehensive examples:

```bash
# Run all examples (indexes and searches)
python -c "from complianceguard.indexing.example_usage import main; main()"

# Run individual examples
python -c "from complianceguard.indexing.example_usage import example_basic_usage; example_basic_usage()"

# Search existing index without re-indexing
python -c "from complianceguard.indexing.example_usage import example_search_existing_index; example_search_existing_index()"
```

Available examples in `example_usage.py`:
1. **example_basic_usage()** - Index and search a single document
2. **example_multiple_documents()** - Index multiple documents
3. **example_multiple_indexes()** - Create separate indexes for different document types
4. **example_index_management()** - View index statistics and manage indexes
5. **example_batch_search()** - Efficient batch searching with multiple queries
6. **example_search_existing_index()** - Search already-indexed documents with various query types

## License

This module is part of the ComplianceGuard project.

