"""Index tracking system to prevent duplicate indexing.

This module provides functionality to track which documents have been indexed
in which collections to avoid duplicate indexing operations.
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


class IndexTracker:
    """Tracks indexed documents to prevent duplicates.
    
    The tracker maintains a JSON log file that records:
    - Document identifier (file path + hash)
    - Collection name
    - Indexing timestamp
    - Number of pages indexed
    - Document metadata
    
    This allows the system to skip indexing if a document has already
    been indexed in a specific collection.
    """
    
    def __init__(self, tracker_file: str = "./artifacts/index_tracker.json"):
        """Initialize the index tracker.
        
        Args:
            tracker_file: Path to the JSON tracker file (default: "./artifacts/index_tracker.json")
        """
        self.tracker_file = tracker_file
        
        # Ensure directory exists
        tracker_dir = os.path.dirname(tracker_file)
        if tracker_dir and not os.path.exists(tracker_dir):
            os.makedirs(tracker_dir, exist_ok=True)
        
        # Load or initialize tracker data
        self._data = self._load_tracker()
    
    def _load_tracker(self) -> dict:
        """Load tracker data from JSON file.
        
        Returns:
            Dictionary with tracker data
        """
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load tracker file: {e}")
                print("Starting with empty tracker")
                return {"indexed_documents": []}
        return {"indexed_documents": []}
    
    def _save_tracker(self) -> None:
        """Save tracker data to JSON file."""
        try:
            with open(self.tracker_file, 'w') as f:
                json.dump(self._data, f, indent=2)
        except IOError as e:
            print(f"Warning: Could not save tracker file: {e}")
    
    def _compute_file_hash(self, filepath: str) -> str:
        """Compute SHA-256 hash of a file.
        
        Args:
            filepath: Path to the file
            
        Returns:
            Hex string of the file hash
        """
        sha256 = hashlib.sha256()
        
        try:
            with open(filepath, 'rb') as f:
                # Read file in chunks to handle large files
                for chunk in iter(lambda: f.read(8192), b''):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except IOError as e:
            print(f"Warning: Could not compute hash for {filepath}: {e}")
            # Fallback to filepath-based identification
            return hashlib.sha256(filepath.encode()).hexdigest()
    
    def is_indexed(self, filepath: str, collection_name: str) -> bool:
        """Check if a document is already indexed in a specific collection.
        
        Args:
            filepath: Path to the document
            collection_name: Name of the collection
            
        Returns:
            True if document is already indexed in the collection, False otherwise
        """
        # Normalize filepath
        normalized_path = os.path.abspath(filepath)
        file_hash = self._compute_file_hash(filepath)
        
        # Check if document exists in tracker for this collection
        for entry in self._data.get("indexed_documents", []):
            if (entry["collection_name"] == collection_name and 
                (entry["filepath"] == normalized_path or entry["file_hash"] == file_hash)):
                return True
        
        return False
    
    def get_indexed_info(self, filepath: str, collection_name: str) -> Optional[dict]:
        """Get indexing information for a document in a collection.
        
        Args:
            filepath: Path to the document
            collection_name: Name of the collection
            
        Returns:
            Dictionary with indexing info or None if not indexed
        """
        normalized_path = os.path.abspath(filepath)
        file_hash = self._compute_file_hash(filepath)
        
        for entry in self._data.get("indexed_documents", []):
            if (entry["collection_name"] == collection_name and 
                (entry["filepath"] == normalized_path or entry["file_hash"] == file_hash)):
                return entry
        
        return None
    
    def record_indexing(
        self,
        filepath: str,
        collection_name: str,
        num_pages: int,
        metadata: Optional[dict] = None
    ) -> None:
        """Record that a document has been indexed.
        
        Args:
            filepath: Path to the document
            collection_name: Name of the collection
            num_pages: Number of pages indexed
            metadata: Optional metadata about the indexing operation
        """
        normalized_path = os.path.abspath(filepath)
        file_hash = self._compute_file_hash(filepath)
        
        # Check if already recorded (update if exists)
        existing_entry = None
        for i, entry in enumerate(self._data.get("indexed_documents", [])):
            if (entry["collection_name"] == collection_name and 
                (entry["filepath"] == normalized_path or entry["file_hash"] == file_hash)):
                existing_entry = i
                break
        
        # Create entry
        entry_data = {
            "filepath": normalized_path,
            "file_hash": file_hash,
            "filename": os.path.basename(filepath),
            "collection_name": collection_name,
            "num_pages": num_pages,
            "indexed_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        # Update or add entry
        if existing_entry is not None:
            self._data["indexed_documents"][existing_entry] = entry_data
            print(f"Updated existing tracker entry for {filepath} in {collection_name}")
        else:
            if "indexed_documents" not in self._data:
                self._data["indexed_documents"] = []
            self._data["indexed_documents"].append(entry_data)
            print(f"Added tracker entry for {filepath} in {collection_name}")
        
        # Save to file
        self._save_tracker()
    
    def remove_entry(self, filepath: str, collection_name: str) -> bool:
        """Remove an entry from the tracker.
        
        Args:
            filepath: Path to the document
            collection_name: Name of the collection
            
        Returns:
            True if entry was removed, False if not found
        """
        normalized_path = os.path.abspath(filepath)
        file_hash = self._compute_file_hash(filepath)
        
        original_count = len(self._data.get("indexed_documents", []))
        
        self._data["indexed_documents"] = [
            entry for entry in self._data.get("indexed_documents", [])
            if not (entry["collection_name"] == collection_name and 
                   (entry["filepath"] == normalized_path or entry["file_hash"] == file_hash))
        ]
        
        removed = len(self._data["indexed_documents"]) < original_count
        
        if removed:
            self._save_tracker()
            print(f"Removed tracker entry for {filepath} in {collection_name}")
        
        return removed
    
    def get_all_indexed(self, collection_name: Optional[str] = None) -> list[dict]:
        """Get all indexed documents, optionally filtered by collection.
        
        Args:
            collection_name: Optional collection name to filter by
            
        Returns:
            List of indexed document entries
        """
        entries = self._data.get("indexed_documents", [])
        
        if collection_name:
            entries = [e for e in entries if e["collection_name"] == collection_name]
        
        return entries
    
    def clear_collection(self, collection_name: str) -> int:
        """Remove all entries for a specific collection.
        
        Args:
            collection_name: Name of the collection to clear
            
        Returns:
            Number of entries removed
        """
        original_count = len(self._data.get("indexed_documents", []))
        
        self._data["indexed_documents"] = [
            entry for entry in self._data.get("indexed_documents", [])
            if entry["collection_name"] != collection_name
        ]
        
        removed_count = original_count - len(self._data["indexed_documents"])
        
        if removed_count > 0:
            self._save_tracker()
            print(f"Cleared {removed_count} entries for collection {collection_name}")
        
        return removed_count
    
    def get_stats(self) -> dict:
        """Get statistics about indexed documents.
        
        Returns:
            Dictionary with statistics
        """
        entries = self._data.get("indexed_documents", [])
        
        # Group by collection
        collections = {}
        for entry in entries:
            coll_name = entry["collection_name"]
            if coll_name not in collections:
                collections[coll_name] = {
                    "document_count": 0,
                    "total_pages": 0,
                    "documents": []
                }
            collections[coll_name]["document_count"] += 1
            collections[coll_name]["total_pages"] += entry.get("num_pages", 0)
            collections[coll_name]["documents"].append({
                "filename": entry.get("filename"),
                "filepath": entry.get("filepath"),
                "num_pages": entry.get("num_pages"),
                "indexed_at": entry.get("indexed_at")
            })
        
        return {
            "total_documents": len(entries),
            "total_collections": len(collections),
            "collections": collections
        }
    
    def print_stats(self) -> None:
        """Print statistics about indexed documents."""
        stats = self.get_stats()
        
        print("\n" + "=" * 80)
        print("Index Tracker Statistics")
        print("=" * 80)
        print(f"Total documents tracked: {stats['total_documents']}")
        print(f"Total collections: {stats['total_collections']}")
        
        if stats['collections']:
            print("\nBy Collection:")
            for coll_name, coll_data in stats['collections'].items():
                print(f"\n  {coll_name}:")
                print(f"    Documents: {coll_data['document_count']}")
                print(f"    Total pages: {coll_data['total_pages']}")
                print(f"    Files:")
                for doc in coll_data['documents']:
                    print(f"      - {doc['filename']} ({doc['num_pages']} pages)")
        else:
            print("\nNo documents indexed yet")
        
        print("=" * 80 + "\n")

