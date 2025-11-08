"""
ScanJob model for tracking compliance scan executions.
Lightweight model for monitoring and auditing scan operations.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import ARRAY, Column, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID

from complianceguard.models.base import BaseModel


class ScanType(str, Enum):
    """Types of compliance scans."""

    INITIAL = "initial"  # First scan of documents
    INCREMENTAL = "incremental"  # Scan only new/updated documents
    RESCAN = "rescan"  # Re-scan all documents
    TARGETED = "targeted"  # Scan specific documents
    SCHEDULED = "scheduled"  # Automated scheduled scan


class ScanStatus(str, Enum):
    """Scan job execution status."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL = "partial"  # Some documents processed successfully


class ScanJob(BaseModel):
    """
    ScanJob model for tracking scan execution.

    Stores scan configuration, execution status, and results
    in a lightweight structure for monitoring and auditing.
    """

    __tablename__ = "scan_jobs"

    # Scan Configuration
    framework = Column(
        String(50),
        nullable=False,
        index=True,
        comment="Compliance framework used for scanning",
    )
    scan_type = Column(
        String(20),
        nullable=False,
        default=ScanType.INITIAL,
        comment="Type of scan: initial, incremental, rescan, targeted",
    )

    # Documents in scope (denormalized - array of IDs)
    document_ids = Column(
        ARRAY(PostgresUUID(as_uuid=True)),
        nullable=False,
        comment="Array of document IDs to scan",
    )

    # Execution Status
    status = Column(
        String(20),
        default=ScanStatus.PENDING,
        nullable=False,
        index=True,
        comment="Current status of the scan job",
    )
    started_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When the scan started processing",
    )
    completed_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When the scan completed",
    )
    duration_seconds = Column(
        Integer,
        nullable=True,
        comment="Total duration of scan in seconds",
    )

    # Results (denormalized)
    results = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="""
        Scan results summary. Example:
        {
            "violations_found": 3,
            "documents_processed": 12,
            "documents_failed": 0,
            "critical_count": 1,
            "high_count": 2,
            "medium_count": 0,
            "low_count": 0,
            "violation_ids": ["uuid1", "uuid2", "uuid3"],
            "failed_document_ids": [],
            "processing_stats": {
                "total_tokens_used": 45000,
                "total_cost_usd": 0.576,
                "avg_processing_time_ms": 3200
            },
            "top_violations": [
                {
                    "type": "material_omission",
                    "count": 2
                }
            ]
        }
        """,
    )

    # Configuration (optional scan parameters)
    configuration = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="""
        Optional scan configuration. Example:
        {
            "severity_threshold": "medium",
            "skip_categories": ["Form_10Q"],
            "focus_rules": ["SEC Reg S-K Item 1C"],
            "confidence_threshold": 0.8,
            "max_violations_per_document": 10
        }
        """,
    )

    # Error Handling
    error_message = Column(
        Text,
        nullable=True,
        comment="Error message if scan failed",
    )
    error_details = Column(
        JSONB,
        nullable=True,
        comment="""
        Detailed error information. Example:
        {
            "error_type": "API_ERROR",
            "error_code": "BEDROCK_THROTTLED",
            "stack_trace": "...",
            "failed_at_document": "uuid",
            "retry_count": 3
        }
        """,
    )

    # Audit Trail (embedded user info)
    triggered_by_email = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Email of user who triggered the scan",
    )
    triggered_by_name = Column(
        String(255),
        nullable=True,
        comment="Name of user who triggered the scan",
    )
    trigger_source = Column(
        String(50),
        nullable=True,
        comment="How scan was triggered: manual, scheduled, webhook, api",
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<ScanJob(id={self.id}, framework={self.framework}, status={self.status})>"

    @property
    def is_running(self) -> bool:
        """Check if scan is currently running."""
        return self.status in [ScanStatus.RUNNING, ScanStatus.QUEUED]

    @property
    def is_complete(self) -> bool:
        """Check if scan has completed (successfully or not)."""
        return self.status in [
            ScanStatus.COMPLETED,
            ScanStatus.FAILED,
            ScanStatus.CANCELLED,
            ScanStatus.PARTIAL,
        ]

    @property
    def has_violations(self) -> bool:
        """Check if scan found any violations."""
        if self.results:
            return self.results.get("violations_found", 0) > 0
        return False

    @property
    def document_count(self) -> int:
        """Get number of documents in scan scope."""
        return len(self.document_ids) if self.document_ids else 0

    @property
    def violations_found(self) -> int:
        """Get number of violations found."""
        if self.results:
            return self.results.get("violations_found", 0)
        return 0

    @property
    def violation_ids(self) -> List[str]:
        """Get list of violation IDs found."""
        if self.results:
            return self.results.get("violation_ids", [])
        return []

    @property
    def success_rate(self) -> Optional[float]:
        """Calculate document processing success rate."""
        if self.results:
            processed = self.results.get("documents_processed", 0)
            failed = self.results.get("documents_failed", 0)
            total = processed + failed
            if total > 0:
                return processed / total
        return None

    def mark_as_running(self) -> None:
        """Mark scan as running and set start time."""
        self.status = ScanStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_as_completed(self, results: dict) -> None:
        """
        Mark scan as completed with results.

        Args:
            results: Scan results dictionary.
        """
        self.status = ScanStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        self.results = results
        if self.started_at:
            self.duration_seconds = int(
                (self.completed_at - self.started_at).total_seconds()
            )

    def mark_as_failed(self, error_message: str, error_details: Optional[dict] = None) -> None:
        """
        Mark scan as failed with error information.

        Args:
            error_message: Human-readable error message.
            error_details: Additional error details.
        """
        self.status = ScanStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message
        self.error_details = error_details
        if self.started_at:
            self.duration_seconds = int(
                (self.completed_at - self.started_at).total_seconds()
            )

    def mark_as_partial(self, results: dict, error_message: str) -> None:
        """
        Mark scan as partially completed.

        Args:
            results: Partial scan results.
            error_message: Error that caused partial completion.
        """
        self.status = ScanStatus.PARTIAL
        self.completed_at = datetime.utcnow()
        self.results = results
        self.error_message = error_message
        if self.started_at:
            self.duration_seconds = int(
                (self.completed_at - self.started_at).total_seconds()
            )

    def add_configuration(self, config: dict) -> None:
        """
        Add or update scan configuration.

        Args:
            config: Configuration dictionary to merge.
        """
        if not self.configuration:
            self.configuration = {}
        self.configuration.update(config)

    def to_summary_dict(self) -> dict:
        """
        Get a summary dictionary for API responses.

        Returns:
            Dictionary with key scan information.
        """
        return {
            "id": str(self.id),
            "framework": self.framework,
            "scan_type": self.scan_type,
            "status": self.status,
            "document_count": self.document_count,
            "violations_found": self.violations_found,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "triggered_by": self.triggered_by_email,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_detailed_dict(self) -> dict:
        """
        Get a detailed dictionary for full API responses.

        Returns:
            Dictionary with all scan information.
        """
        return {
            "id": str(self.id),
            "framework": self.framework,
            "scan_type": self.scan_type,
            "status": self.status,
            "document_ids": [str(doc_id) for doc_id in self.document_ids] if self.document_ids else [],
            "document_count": self.document_count,
            "configuration": self.configuration,
            "results": self.results,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "success_rate": self.success_rate,
            "triggered_by": {
                "email": self.triggered_by_email,
                "name": self.triggered_by_name,
            } if self.triggered_by_email else None,
            "trigger_source": self.trigger_source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }