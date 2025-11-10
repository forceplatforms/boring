#!/usr/bin/env python3
"""Standalone script to search already-indexed documents.

Run this script after you've indexed documents using the DocumentIndex.
This is useful for quickly testing searches without re-indexing.

Usage:
    .venv/bin/python src/complianceguard/indexing/search_example.py
    .venv/bin/python src/complianceguard/indexing/search_example.py --index-name my_docs
    .venv/bin/python src/complianceguard/indexing/search_example.py --query "your search query"
"""

import argparse
from pathlib import Path

from complianceguard.config import get_settings
from complianceguard.indexing import DocumentIndex


# Get project root directory (3 levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


def run_interactive_search(
    index_name: str | None = None,
    milvus_uri: str | None = None,
    topk: int | None = None
):
    """Run interactive search mode."""
    # Get settings
    settings = get_settings()

    # Use provided values or config defaults
    index_name = index_name or settings.indexing_default_collection
    milvus_uri = milvus_uri or str(PROJECT_ROOT / "artifacts" / "milvus_example.db")
    topk = topk or settings.indexing_default_topk

    # Connect to existing index
    index = DocumentIndex(index_name=index_name, milvus_uri=milvus_uri)

    # Check if index has data
    stats = index.get_stats()
    print("=" * 80)
    print(f"✓ Connected to index: {stats['index_name']}")
    print(f"  Total documents: {stats['total_documents']}")
    print("=" * 80)

    if stats['total_documents'] == 0:
        print("\n⚠️  No documents found in index.")
        print("\n💡 Please index documents first:")
        print("  .venv/bin/python -c 'from complianceguard.indexing.example_usage import example_basic_usage; example_basic_usage()'")
        return

    print("\n📚 Indexed documents:")
    for doc in stats['documents']:
        print(f"   - {Path(doc['filepath']).name}")

    print("\n" + "=" * 80)
    print("Interactive Search Mode")
    print("=" * 80)
    print("Type your queries below. Type 'quit', 'exit', or press Ctrl+C to exit.\n")

    try:
        while True:
            query = input("Search query: ").strip()

            if not query:
                continue

            if query.lower() in ['quit', 'exit', 'q']:
                print("\nExiting search mode. Goodbye!")
                break

            # Perform search
            results = index.search(query, topk=topk)

            if results:
                print(f"\n✓ Found {len(results)} result(s):\n")
                for rank, (score, page_num, filepath, page_url) in enumerate(results, 1):
                    print(f"  {rank}. Score: {score:.4f}")
                    print(f"     Page: {page_num}")
                    print(f"     File: {Path(filepath).name}")
                    if page_url:
                        print(f"     📷 Image: {page_url}")
                    print()
            else:
                print("\n⚠️  No results found.\n")

    except KeyboardInterrupt:
        print("\n\nExiting search mode. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error during search: {e}")


def run_single_query(
    query: str,
    index_name: str | None = None,
    milvus_uri: str | None = None,
    topk: int | None = None
):
    """Run a single search query."""
    # Get settings
    settings = get_settings()

    # Use provided values or config defaults
    index_name = index_name or settings.indexing_default_collection
    milvus_uri = milvus_uri or str(PROJECT_ROOT / "artifacts" / "milvus_example.db")
    topk = topk or settings.indexing_default_topk

    # Connect to existing index
    index = DocumentIndex(index_name=index_name, milvus_uri=milvus_uri)

    # Check if index has data
    stats = index.get_stats()

    if stats['total_documents'] == 0:
        print("⚠️  No documents found in index. Please index documents first.")
        return

    print(f"Searching in index '{index_name}' with {stats['total_documents']} document(s)...")
    print(f"Query: {query}\n")

    # Perform search
    results = index.search(query, topk=topk)

    if results:
        print(f"✓ Found {len(results)} result(s):\n")
        for rank, (score, page_num, filepath, page_url) in enumerate(results, 1):
            print(f"{rank}. Score: {score:.4f} | Page: {page_num}")
            print(f"   File: {Path(filepath).name}")
            if page_url:
                print(f"   📷 Image: {page_url}")
            print()
    else:
        print("⚠️  No results found.")


def main():
    """Main entry point for the search script."""
    parser = argparse.ArgumentParser(
        description="Search already-indexed documents using DocumentIndex",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (default)
  python search_example.py

  # Single query
  python search_example.py --query "What is machine learning?"

  # Search in a specific index
  python search_example.py --index-name my_documents --query "API documentation"

  # Get more results
  python search_example.py --query "neural networks" --topk 10
        """
    )

    parser.add_argument(
        '--index-name',
        type=str,
        default=None,
        help='Name of the index to search (default: from config)'
    )

    parser.add_argument(
        '--milvus-uri',
        type=str,
        default=None,
        help='Path to Milvus database (default: from config)'
    )

    parser.add_argument(
        '--query',
        type=str,
        help='Single search query (if not provided, enters interactive mode)'
    )

    parser.add_argument(
        '--topk',
        type=int,
        default=None,
        help='Number of results to return (default: from config)'
    )

    args = parser.parse_args()

    if args.query:
        # Single query mode
        run_single_query(args.query, args.index_name, args.milvus_uri, args.topk)
    else:
        # Interactive mode
        run_interactive_search(args.index_name, args.milvus_uri)


if __name__ == "__main__":
    main()

