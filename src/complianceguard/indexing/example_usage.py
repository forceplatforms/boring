"""Example usage of the DocumentIndex for indexing and searching PDF documents.

This script demonstrates:
1. Creating a DocumentIndex instance
2. Indexing a PDF document
3. Searching the indexed documents
4. Managing multiple indexes
5. Searching existing indexes without re-indexing

To run individual examples:
- python -c "from complianceguard.indexing.example_usage import example_basic_usage; example_basic_usage()"
- python -c "from complianceguard.indexing.example_usage import example_search_existing_index; example_search_existing_index()"
"""

from complianceguard.indexing import DocumentIndex


def example_basic_usage():
    """Basic example: Index and search a single document."""
    print("=" * 80)
    print("Example 1: Basic Usage")
    print("=" * 80)

    # Create index
    index = DocumentIndex(
        index_name="example_docs",
        milvus_uri="./artifacts/milvus_example.db"
    )

    # Index a document
    # Replace with your actual PDF path
    pdf_path = "/Users/tilaksharma/VsCodeProjects/boring/src/complianceguard/resources/molorag.pdf"
    print(f"\nIndexing document: {pdf_path}")

    try:
        num_pages = index.index_document(pdf_path, batch_size=4)
        print(f"Successfully indexed {num_pages} pages")

        # Search the document
        query = "What was the average accuracy of Qwen2.5-VL-7B with MoLoRAG+"
        results = index.search(query, topk=3)

        # Print results using built-in method
        index.print_results(query, results)

    except FileNotFoundError:
        print(f"Error: PDF file not found at {pdf_path}")
        print("Please update the pdf_path variable with a valid PDF file path")


def example_multiple_documents():
    """Example: Index multiple documents."""
    print("\n" + "=" * 80)
    print("Example 2: Multiple Documents")
    print("=" * 80)

    index = DocumentIndex(
        index_name="multi_docs",
        milvus_uri="./artifacts/milvus_example.db"
    )

    # List of PDFs to index
    pdf_files = [
        "path/to/document1.pdf",
        "path/to/document2.pdf",
        "path/to/document3.pdf",
    ]

    print(f"\nIndexing {len(pdf_files)} documents...")

    try:
        stats = index.index_documents(pdf_files, batch_size=4)
        print("\nIndexing complete!")
        print(f"Total documents: {stats['total_documents']}")
        print(f"Total pages: {stats['total_pages']}")

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please update the pdf_files list with valid PDF file paths")


def example_multiple_indexes():
    """Example: Using multiple independent indexes."""
    print("\n" + "=" * 80)
    print("Example 3: Multiple Indexes")
    print("=" * 80)

    # Create separate indexes for different document types
    finance_index = DocumentIndex(
        index_name="finance_documents",
        milvus_uri="./artifacts/milvus_example.db"
    )

    legal_index = DocumentIndex(
        index_name="legal_documents",
        milvus_uri="./artifacts/milvus_example.db"
    )

    print("\nCreated two separate indexes:")
    print(f"  - {finance_index.index_name}: {finance_index.get_stats()['total_documents']} documents")
    print(f"  - {legal_index.index_name}: {legal_index.get_stats()['total_documents']} documents")

    # You can now index different documents to different indexes
    # finance_index.index_document("financial_report.pdf")
    # legal_index.index_document("contract.pdf")

    # Search in specific indexes
    # finance_results = finance_index.search("revenue", topk=5)
    # legal_results = legal_index.search("terms", topk=5)


def example_index_management():
    """Example: Managing indexes and viewing statistics."""
    print("\n" + "=" * 80)
    print("Example 4: Index Management")
    print("=" * 80)

    index = DocumentIndex(
        index_name="management_example",
        milvus_uri="./artifacts/milvus_example.db"
    )

    # Get index statistics
    stats = index.get_stats()
    print(f"\nIndex: {stats['index_name']}")
    print(f"Total documents: {stats['total_documents']}")

    if stats['documents']:
        print("\nIndexed documents:")
        for doc in stats['documents']:
            print(f"  - {doc['filepath']} (ID: {doc['doc_id']})")
    else:
        print("\nNo documents indexed yet")

    # Clear the index (commented out for safety)
    # print("\nClearing index...")
    # index.clear_index()
    # print("Index cleared")


def example_batch_search():
    """Example: Searching with multiple queries."""
    print("\n" + "=" * 80)
    print("Example 5: Batch Search")
    print("=" * 80)

    index = DocumentIndex(
        index_name="batch_search_example",
        milvus_uri="./artifacts/milvus_example.db"
    )

    # Multiple queries to search
    queries = [
        "What is the main topic?",
        "Who are the authors?",
        "What are the key findings?",
        "What are the conclusions?",
    ]

    print(f"\nSearching with {len(queries)} queries...")

    # Use batch_search method for efficiency
    all_results = index.batch_search(queries, topk=3)

    # Print results for each query
    for i, (query, results) in enumerate(zip(queries, all_results, strict=True), 1):
        print(f"\n{i}. Query: '{query}'")
        if results:
            for rank, (score, _page, filepath) in enumerate(results, 1):
                print(f"   {rank}. {filepath} (score: {score:.4f})")
        else:
            print("   No results found")


def example_search_existing_index():
    """Example: Search an already-indexed collection without re-indexing.

    This is useful when you've already indexed documents and just want to
    run searches without having to index again.
    """
    print("\n" + "=" * 80)
    print("Example 6: Search Existing Index")
    print("=" * 80)

    # Connect to existing index
    index = DocumentIndex(
        index_name="example_docs",  # Use the same name as your indexed collection
        milvus_uri="./artifacts/milvus_example.db"
    )

    # Check if index has data
    stats = index.get_stats()
    print(f"\nConnected to index: {stats['index_name']}")
    print(f"Total documents: {stats['total_documents']}")

    if stats['total_documents'] == 0:
        print("\nNo documents found in index. Please run indexing first.")
        print("You can run: example_basic_usage() to index a document first.")
        return

    print("\nIndexed documents:")
    for doc in stats['documents']:
        print(f"  - {doc['filepath']}")

    # Example searches
    print("\n" + "-" * 80)
    print("Running example searches...")
    print("-" * 80)

    # Search 1: Specific technical question
    query1 = "What was the average accuracy of Qwen2.5-VL-7B with MoLoRAG+"
    print(f"\n1. Searching: '{query1}'")
    results1 = index.search(query1, topk=3)

    if results1:
        print(f"   Found {len(results1)} results:")
        for rank, (score, page_num, filepath) in enumerate(results1, 1):
            print(f"   {rank}. Page {page_num} - Score: {score:.4f}")
            print(f"      File: {filepath}")
    else:
        print("   No results found")

    # Search 2: Broader topic
    query2 = "mixture of experts"
    print(f"\n2. Searching: '{query2}'")
    results2 = index.search(query2, topk=5)

    if results2:
        print(f"   Found {len(results2)} results:")
        for rank, (score, page_num, _filepath) in enumerate(results2, 1):
            print(f"   {rank}. Page {page_num} - Score: {score:.4f}")
    else:
        print("   No results found")

    # Search 3: Using print_results for better formatting
    query3 = "retrieval augmented generation"
    print(f"\n3. Searching with formatted output: '{query3}'")
    results3 = index.search(query3, topk=3)
    index.print_results(query3, results3)

    # Search 4: Batch search example
    print("\n4. Running batch search...")
    batch_queries = [
        "What is the main contribution?",
        "How does the training work?",
        "What are the benchmarks used?",
    ]

    batch_results = index.batch_search(batch_queries, topk=2)

    for query, results in zip(batch_queries, batch_results, strict=True):
        print(f"\n   Query: '{query}'")
        if results:
            for rank, (score, page_num, _filepath) in enumerate(results, 1):
                print(f"     {rank}. Page {page_num} (score: {score:.4f})")
        else:
            print("     No results")

    print("\n" + "-" * 80)
    print("Search examples complete!")
    print("-" * 80)


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("DocumentIndex Usage Examples")
    print("=" * 80)
    print("\nNote: Update the PDF paths in this script with your actual documents")
    print("=" * 80)

    # Run examples
    example_basic_usage()

    # Uncomment to run other examples:
    # example_multiple_documents()
    # example_multiple_indexes()
    # example_index_management()
    # example_batch_search()

    # Search existing index (run this after indexing is complete)
    # example_search_existing_index()

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)
    print("\nTo search your indexed documents, run:")
    print("  python -c 'from complianceguard.indexing.example_usage import example_search_existing_index; example_search_existing_index()'")
    print("=" * 80)


if __name__ == "__main__":
    main()

