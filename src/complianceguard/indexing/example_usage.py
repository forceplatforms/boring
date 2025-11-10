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

from pathlib import Path

from complianceguard.config import get_settings
from complianceguard.indexing import DocumentIndex


# Get project root directory (3 levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RESOURCES_DIR = PROJECT_ROOT / "resources" / "sample_documents"


def example_basic_usage():
    """Basic example: Index and search a single document."""
    print("=" * 80)
    print("Example 1: Basic Usage")
    print("=" * 80)

    # Get settings
    settings = get_settings()

    # Create index (uses config defaults)
    index = DocumentIndex(
        index_name="example_docs",
        milvus_uri=str(PROJECT_ROOT / "artifacts" / "milvus_example.db")
    )

    # Find PDF files in resources directory
    pdf_files = list(RESOURCES_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"\n⚠️  No PDF files found in {RESOURCES_DIR}")
        print("\nTo use this example:")
        print(f"1. Place your PDF files in: {RESOURCES_DIR}")
        print("2. Run this script again")
        print("\nExample:")
        print(f"   cp your_document.pdf {RESOURCES_DIR}/")
        return

    # Use the first PDF found
    pdf_path = str(pdf_files[0])
    print(f"\n📄 Found PDF: {Path(pdf_path).name}")
    print(f"   Full path: {pdf_path}")

    try:
        num_pages = index.index_document(pdf_path, batch_size=settings.indexing_batch_size)
        print(f"\n✓ Successfully indexed {num_pages} pages")

        if num_pages > 0:
            # Search the document
            query = "What is the main topic of this document?"
            print(f"\n🔍 Searching for: '{query}'")
            results = index.search(query, topk=settings.indexing_default_topk)

            # Print results using built-in method
            index.print_results(query, results)
        else:
            print("\n⏭️  Document was already indexed (skipped)")
            print("   Use force=True to re-index")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")


def example_multiple_documents():
    """Example: Index multiple documents."""
    print("\n" + "=" * 80)
    print("Example 2: Multiple Documents")
    print("=" * 80)

    # Get settings
    settings = get_settings()

    index = DocumentIndex(
        index_name="multi_docs",
        milvus_uri=str(PROJECT_ROOT / "artifacts" / "milvus_example.db")
    )

    # Find all PDFs in resources directory
    pdf_files = [str(p) for p in RESOURCES_DIR.glob("*.pdf")]

    if not pdf_files:
        print(f"\n⚠️  No PDF files found in {RESOURCES_DIR}")
        print("\nPlease add PDF files to the resources directory first.")
        return

    print(f"\n📚 Found {len(pdf_files)} PDF file(s):")
    for pdf in pdf_files:
        print(f"   - {Path(pdf).name}")

    try:
        print("\n📥 Indexing documents...")
        stats = index.index_documents(pdf_files, batch_size=settings.indexing_batch_size)
        print("\n✓ Indexing complete!")
        print(f"   Total documents processed: {stats['total_documents']}")
        print(f"   Documents indexed: {stats['documents_indexed']}")
        print(f"   Documents skipped: {stats['documents_skipped']}")
        print(f"   Total pages: {stats['total_pages']}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


def example_multiple_indexes():
    """Example: Using multiple independent indexes."""
    print("\n" + "=" * 80)
    print("Example 3: Multiple Indexes")
    print("=" * 80)

    milvus_uri = str(PROJECT_ROOT / "artifacts" / "milvus_example.db")

    # Create separate indexes for different document types
    finance_index = DocumentIndex(
        index_name="finance_documents",
        milvus_uri=milvus_uri
    )

    legal_index = DocumentIndex(
        index_name="legal_documents",
        milvus_uri=milvus_uri
    )

    print("\n✓ Created two separate indexes:")
    finance_stats = finance_index.get_stats()
    legal_stats = legal_index.get_stats()
    print(f"  📊 {finance_index.index_name}: {finance_stats['total_documents']} documents")
    print(f"  📜 {legal_index.index_name}: {legal_stats['total_documents']} documents")

    print("\n💡 You can now index different documents to different collections:")
    print("   finance_index.index_document('financial_report.pdf')")
    print("   legal_index.index_document('contract.pdf')")
    print("\n💡 And search in specific collections:")
    print("   finance_results = finance_index.search('revenue', topk=5)")
    print("   legal_results = legal_index.search('terms', topk=5)")


def example_index_management():
    """Example: Managing indexes and viewing statistics."""
    print("\n" + "=" * 80)
    print("Example 4: Index Management")
    print("=" * 80)

    index = DocumentIndex(
        index_name="management_example",
        milvus_uri=str(PROJECT_ROOT / "artifacts" / "milvus_example.db")
    )

    # Get index statistics
    stats = index.get_stats()
    print(f"\n📊 Index: {stats['index_name']}")
    print(f"   Total documents: {stats['total_documents']}")

    if stats['documents']:
        print("\n📚 Indexed documents:")
        for doc in stats['documents']:
            print(f"   - {Path(doc['filepath']).name} (ID: {doc['doc_id']})")
    else:
        print("\n⚠️  No documents indexed yet")

    # Show tracker stats
    print("\n📈 Tracker Statistics:")
    index.print_tracker_stats()

    # Clear the index (commented out for safety)
    # print("\n🗑️  Clearing index...")
    # index.clear_index()
    # print("✓ Index cleared")


def example_batch_search():
    """Example: Searching with multiple queries."""
    print("\n" + "=" * 80)
    print("Example 5: Batch Search")
    print("=" * 80)

    # Get settings
    settings = get_settings()

    index = DocumentIndex(
        index_name="example_docs",
        milvus_uri=str(PROJECT_ROOT / "artifacts" / "milvus_example.db")
    )

    # Check if index has data
    stats = index.get_stats()
    if stats['total_documents'] == 0:
        print("\n⚠️  No documents in index. Please run example_basic_usage() first.")
        return

    # Multiple queries to search
    queries = [
        "What is the main topic?",
        "Who are the authors?",
        "What are the key findings?",
        "What are the conclusions?",
    ]

    print(f"\n🔍 Searching with {len(queries)} queries...")

    # Use batch_search method for efficiency
    all_results = index.batch_search(queries, topk=3)

    # Print results for each query
    for i, (query, results) in enumerate(zip(queries, all_results, strict=True), 1):
        print(f"\n{i}. 💬 Query: '{query}'")
        if results:
            for rank, (score, _page, filepath, page_url) in enumerate(results, 1):
                print(f"   {rank}. {Path(filepath).name} (score: {score:.4f})")
                if page_url:
                    print(f"      📷 {page_url}")
        else:
            print("   ⚠️  No results found")


def example_search_existing_index():
    """Example: Search an already-indexed collection without re-indexing.

    This is useful when you've already indexed documents and just want to
    run searches without having to index again.
    """
    print("\n" + "=" * 80)
    print("Example 6: Search Existing Index")
    print("=" * 80)

    # Get settings
    settings = get_settings()

    # Connect to existing index
    index = DocumentIndex(
        index_name="example_docs",
        milvus_uri=str(PROJECT_ROOT / "artifacts" / "milvus_example.db")
    )

    # Check if index has data
    stats = index.get_stats()
    print(f"\n✓ Connected to index: {stats['index_name']}")
    print(f"   Total documents: {stats['total_documents']}")

    if stats['total_documents'] == 0:
        print("\n⚠️  No documents found in index. Please run indexing first.")
        print("   You can run: example_basic_usage() to index a document first.")
        return

    print("\n📚 Indexed documents:")
    for doc in stats['documents']:
        print(f"   - {Path(doc['filepath']).name}")

    # Example searches
    print("\n" + "-" * 80)
    print("🔍 Running example searches...")
    print("-" * 80)

    # Search 1: General query
    query1 = "What is the main topic of this document?"
    print(f"\n1. 💬 Searching: '{query1}'")
    results1 = index.search(query1, topk=3)

    if results1:
        print(f"   ✓ Found {len(results1)} result(s):")
        for rank, (score, page_num, filepath, page_url) in enumerate(results1, 1):
            print(f"   {rank}. Page {page_num} - Score: {score:.4f}")
            print(f"      File: {Path(filepath).name}")
            if page_url:
                print(f"      📷 Image: {page_url}")
    else:
        print("   ⚠️  No results found")

    # Search 2: Another example query
    query2 = "key findings and results"
    print(f"\n2. 💬 Searching: '{query2}'")
    results2 = index.search(query2, topk=settings.indexing_default_topk)

    if results2:
        print(f"   ✓ Found {len(results2)} result(s):")
        for rank, (score, page_num, filepath, page_url) in enumerate(results2, 1):
            print(f"   {rank}. {Path(filepath).name} - Page {page_num} (score: {score:.4f})")
            if page_url:
                print(f"      📷 {page_url}")
    else:
        print("   ⚠️  No results found")

    # Search 3: Using print_results for better formatting
    query3 = "methodology and approach"
    print(f"\n3. 💬 Searching with formatted output: '{query3}'")
    results3 = index.search(query3, topk=3)
    index.print_results(query3, results3)

    # Search 4: Batch search example
    print("\n4. 🔍 Running batch search...")
    batch_queries = [
        "conclusions and summary",
        "future work and improvements",
        "limitations and challenges",
    ]

    batch_results = index.batch_search(batch_queries, topk=2)

    for query, results in zip(batch_queries, batch_results, strict=True):
        print(f"\n   💬 Query: '{query}'")
        if results:
            for rank, (score, page_num, filepath, page_url) in enumerate(results, 1):
                print(f"     {rank}. {Path(filepath).name} - Page {page_num} (score: {score:.4f})")
                if page_url:
                    print(f"        📷 {page_url}")
        else:
            print("     ⚠️  No results")

    print("\n" + "-" * 80)
    print("✓ Search examples complete!")
    print("-" * 80)


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("📚 ComplianceGuard Document Indexing Examples")
    print("=" * 80)
    print(f"\n📁 Resources directory: {RESOURCES_DIR}")
    print(f"📁 Project root: {PROJECT_ROOT}")
    print("\n💡 Place your PDF files in the resources directory to get started!")
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
    print("✓ Examples complete!")
    print("=" * 80)
    print("\n📖 To run individual examples:")
    print("  .venv/bin/python -c 'from complianceguard.indexing.example_usage import example_search_existing_index; example_search_existing_index()'")
    print("\n📖 Or use the search script:")
    print("  .venv/bin/python src/complianceguard/indexing/search_example.py")
    print("=" * 80)


if __name__ == "__main__":
    main()

