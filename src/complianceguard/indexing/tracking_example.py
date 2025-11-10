"""Example demonstrating the index tracking functionality.

This script shows how the tracking system prevents duplicate indexing
and provides statistics about indexed documents.
"""

from complianceguard.indexing import DocumentIndex


def demo_duplicate_prevention():
    """Demonstrate how the tracker prevents duplicate indexing."""
    print("\n" + "=" * 80)
    print("Example: Duplicate Prevention with Index Tracker")
    print("=" * 80)
    
    # Create an index instance
    index = DocumentIndex(
        index_name="tracked_docs",
        milvus_uri="./artifacts/milvus_example.db",
        tracker_file="./artifacts/index_tracker.json"
    )
    
    # PDF to index (update with your actual path)
    pdf_path = "/Users/tilaksharma/VsCodeProjects/boring/src/complianceguard/resources/molorag.pdf"
    
    print("\n--- First Indexing Attempt ---")
    print(f"Attempting to index: {pdf_path}")
    
    try:
        # First time - will index the document
        num_pages = index.index_document(pdf_path, batch_size=4)
        if num_pages > 0:
            print(f"\n✓ Successfully indexed {num_pages} pages")
        
        print("\n--- Second Indexing Attempt (Same Document) ---")
        print(f"Attempting to index the same document again: {pdf_path}")
        
        # Second time - will be skipped
        num_pages = index.index_document(pdf_path, batch_size=4)
        if num_pages == 0:
            print("\n✓ Document was skipped - no duplicates created!")
        
        print("\n--- Third Attempt with force=True ---")
        print("Attempting to re-index with force=True...")
        
        # With force=True, it will re-index
        # Commented out to avoid actual re-indexing in demo
        # num_pages = index.index_document(pdf_path, batch_size=4, force=True)
        print("(Skipped in demo - use force=True to override duplicate check)")
        
    except FileNotFoundError:
        print(f"\nError: PDF not found at {pdf_path}")
        print("Please update the pdf_path variable with a valid file path")


def demo_tracker_stats():
    """Demonstrate tracker statistics."""
    print("\n" + "=" * 80)
    print("Example: Index Tracker Statistics")
    print("=" * 80)
    
    # Create an index instance
    index = DocumentIndex(
        index_name="tracked_docs",
        milvus_uri="./artifacts/milvus_example.db",
        tracker_file="./artifacts/index_tracker.json"
    )
    
    # Print tracker statistics
    print("\n--- Tracker Statistics ---")
    index.print_tracker_stats()
    
    # Get programmatic access to stats
    stats = index.get_tracker_stats()
    
    print("\n--- Programmatic Stats Access ---")
    print(f"Total documents tracked: {stats['total_documents']}")
    print(f"Total collections: {stats['total_collections']}")
    
    if stats['collections']:
        print("\nCollections:")
        for coll_name, coll_data in stats['collections'].items():
            print(f"  - {coll_name}: {coll_data['document_count']} documents, "
                  f"{coll_data['total_pages']} pages")


def demo_multiple_collections():
    """Demonstrate tracking across multiple collections."""
    print("\n" + "=" * 80)
    print("Example: Multiple Collections with Tracking")
    print("=" * 80)
    
    # Same PDF, different collections
    pdf_path = "/Users/tilaksharma/VsCodeProjects/boring/src/complianceguard/resources/molorag.pdf"
    
    # Create two different indexes
    index1 = DocumentIndex(
        index_name="collection_1",
        milvus_uri="./artifacts/milvus_example.db",
        tracker_file="./artifacts/index_tracker.json"
    )
    
    index2 = DocumentIndex(
        index_name="collection_2",
        milvus_uri="./artifacts/milvus_example.db",
        tracker_file="./artifacts/index_tracker.json"
    )
    
    print("\n--- Indexing into Collection 1 ---")
    try:
        # Will index if not already in collection_1
        num_pages1 = index1.index_document(pdf_path, batch_size=4)
        if num_pages1 > 0:
            print(f"✓ Indexed {num_pages1} pages into collection_1")
        else:
            print("✓ Already indexed in collection_1")
        
        print("\n--- Indexing into Collection 2 ---")
        # Will index if not already in collection_2 (even if in collection_1)
        num_pages2 = index2.index_document(pdf_path, batch_size=4)
        if num_pages2 > 0:
            print(f"✓ Indexed {num_pages2} pages into collection_2")
        else:
            print("✓ Already indexed in collection_2")
        
        print("\nNote: The same document can be indexed in different collections.")
        print("The tracker prevents duplicates within each collection separately.")
        
    except FileNotFoundError:
        print(f"\nError: PDF not found at {pdf_path}")
        print("Please update the pdf_path variable with a valid file path")


def demo_batch_indexing():
    """Demonstrate tracking with batch indexing."""
    print("\n" + "=" * 80)
    print("Example: Batch Indexing with Tracking")
    print("=" * 80)
    
    index = DocumentIndex(
        index_name="batch_docs",
        milvus_uri="./artifacts/milvus_example.db",
        tracker_file="./artifacts/index_tracker.json"
    )
    
    # List of PDFs (update with actual paths)
    pdf_files = [
        "/Users/tilaksharma/VsCodeProjects/boring/src/complianceguard/resources/molorag.pdf",
        # Add more PDFs here
    ]
    
    print(f"\n--- Indexing {len(pdf_files)} documents ---")
    
    try:
        # First run - will index new documents
        print("\nFirst batch run:")
        stats1 = index.index_documents(pdf_files, batch_size=4)
        print(f"Results: {stats1['documents_indexed']} indexed, "
              f"{stats1['documents_skipped']} skipped")
        
        # Second run - will skip already indexed documents
        print("\nSecond batch run (same documents):")
        stats2 = index.index_documents(pdf_files, batch_size=4)
        print(f"Results: {stats2['documents_indexed']} indexed, "
              f"{stats2['documents_skipped']} skipped")
        
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Please update the pdf_files list with valid file paths")


def main():
    """Run all examples."""
    print("\n" + "=" * 80)
    print("Index Tracking Examples")
    print("=" * 80)
    
    # Run examples
    demo_duplicate_prevention()
    demo_tracker_stats()
    
    # Uncomment to run additional examples:
    # demo_multiple_collections()
    # demo_batch_indexing()
    
    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)
    print("\nKey Takeaways:")
    print("1. The tracker automatically prevents duplicate indexing")
    print("2. Documents are tracked per collection")
    print("3. Use force=True to override and re-index")
    print("4. Tracker maintains a JSON log in artifacts/index_tracker.json")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    # Run individual examples:
    # demo_duplicate_prevention()
    # demo_tracker_stats()
    # demo_multiple_collections()
    # demo_batch_indexing()
    
    # Or run all:
    main()

