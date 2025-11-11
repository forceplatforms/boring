"""
Violation model for storing compliance violations with denormalized document data.
Stores all violation details and evidence in a single row for efficient querying.
"""

from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import Column, ForeignKey, Index, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgresUUID

from complianceguard.models.base import BaseModel


class ViolationSeverity(str, Enum):
    """Violation severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ViolationType(str, Enum):
    """Types of compliance violations."""

    MATERIAL_OMISSION = "material_omission"
    MISLEADING_STATEMENT = "misleading_statement"
    DELAYED_DISCLOSURE = "delayed_disclosure"
    INCOMPLETE_DISCLOSURE = "incomplete_disclosure"
    INCONSISTENT_REPORTING = "inconsistent_reporting"
    RISK_DOWNPLAYING = "risk_downplaying"
    OTHER = "other"


class ViolationStatus(str, Enum):
    """Status of violation remediation."""

    OPEN = "open"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    REMEDIATED = "remediated"
    FALSE_POSITIVE = "false_positive"
    ACKNOWLEDGED = "acknowledged"


class ComplianceFramework(str, Enum):
    """Compliance frameworks."""

    SEC_CYBER = "SEC_CYBER"
    SOX = "SOX"
    GDPR = "GDPR"
    CCPA = "CCPA"
    HIPAA = "HIPAA"


class Violation(BaseModel):
    """
    Violation model with denormalized structure for efficient querying.

    Stores all violation data including embedded document context,
    evidence, AI analysis metadata, and recommendations in a single row.
    """

    __tablename__ = "violations"

    # Related Documents (with embedded data for denormalization)
    source_document_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("ingested_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the source document (e.g., CISO report)",
    )
    source_document_data = Column(
        JSONB,
        nullable=False,
        comment="""
        Denormalized source document data. Example:
        {
            "id": "uuid",
            "file_name": "CISO_Report_Oct2024.pdf",
            "doc_type": "ciso_report",
            "file_size_bytes": 2457600,
            "created_at": "2025-11-07T14:32:00Z",
            "uploaded_by": "security@company.com"
        }
        """,
    )

    target_document_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("ingested_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="ID of the target document (e.g., SEC filing)",
    )
    target_document_data = Column(
        JSONB,
        nullable=False,
        comment="""
        Denormalized target document data. Example:
        {
            "id": "uuid",
            "file_name": "Form_8K_Draft.docx",
            "doc_type": "sec_filing",
            "doc_category": "Form_8K",
            "created_at": "2025-11-07T14:45:00Z",
            "uploaded_by": "legal@company.com"
        }
        """,
    )

    # Framework & Rule
    framework = Column(
        String(50),
        nullable=False,
        default=ComplianceFramework.SEC_CYBER,
        index=True,
        comment="Compliance framework",
    )
    rule_citation = Column(
        Text,
        nullable=False,
        comment="Specific rule or regulation citation (e.g., 'SEC Regulation S-K Item 1C')",
    )

    # Violation Details
    severity = Column(
        String(20),
        nullable=False,
        index=True,
        comment="Severity level: critical, high, medium, low",
    )
    violation_type = Column(
        String(100),
        nullable=False,
        index=True,
        comment="Type of violation: material_omission, misleading_statement, etc.",
    )
    finding_summary = Column(
        Text,
        nullable=False,
        comment="Brief summary of the violation finding",
    )
    explanation = Column(
        Text,
        nullable=False,
        comment="Detailed explanation of why this is a violation",
    )

    # Evidence (denormalized - store quotes directly)
    evidence = Column(
        JSONB,
        nullable=False,
        comment="""
        Evidence supporting the violation. Example:
        {
            "source_quote": "Ransomware attack confirmed. 47,000 records exfiltrated...",
            "source_page": 3,
            "source_section": "Impact Assessment",
            "source_context": "Full paragraph for context...",
            "target_quote": "We may be subject to hypothetical cyber risks...",
            "target_page": 1,
            "target_section": "Item 1.05",
            "target_context": "Full paragraph for context...",
            "discrepancy_type": "omission",
            "timeline_mismatch": {
                "internal_date": "2024-10-27",
                "disclosed_date": null,
                "delay_days": null
            }
        }
        """,
    )

    # AI Analysis Metadata
    ai_metadata = Column(
        JSONB,
        nullable=False,
        comment="""
        AI processing metadata. Example:
        {
            "model": "claude-3-sonnet",
            "model_version": "20240229-v1:0",
            "confidence_score": 0.95,
            "processing_time_ms": 3420,
            "prompt_tokens": 4500,
            "completion_tokens": 1200,
            "total_cost_usd": 0.0576,
            "analysis_timestamp": "2025-11-07T16:30:00Z",
            "prompt_template_version": "v1.2"
        }
        """,
    )

    # Recommendations (denormalized - store all in JSONB)
    recommendations = Column(
        JSONB,
        nullable=False,
        comment="""
        Recommendations for remediation. Example:
        {
            "actions": [
                {
                    "priority": "immediate",
                    "description": "Alert General Counsel",
                    "timeline": "Next 2 hours",
                    "responsible_party": "Compliance Officer"
                },
                {
                    "priority": "high",
                    "description": "File amended 8-K",
                    "timeline": "Within 4 business days",
                    "responsible_party": "Legal Department"
                }
            ],
            "suggested_language": "On October 27, 2024, the Company experienced a cybersecurity incident...",
            "financial_risk": {
                "estimated_penalty_min": 1500000,
                "estimated_penalty_max": 7000000,
                "basis": "Recent SEC enforcement actions",
                "precedents": [
                    {"company": "Example Corp", "penalty": 3500000, "year": 2024}
                ]
            },
            "regulatory_deadlines": {
                "form_8k_deadline": "2024-10-31T23:59:59Z",
                "days_remaining": 2
            }
        }
        """,
    )

    # Status & Assignment
    status = Column(
        String(20),
        default=ViolationStatus.OPEN,
        nullable=False,
        index=True,
        comment="Current status of the violation",
    )
    assigned_to_email = Column(
        String(255),
        nullable=True,
        index=True,
        comment="Email of person assigned to remediate",
    )
    assigned_to_name = Column(
        String(255),
        nullable=True,
        comment="Name of person assigned to remediate",
    )
    resolved_at = Column(
        TIMESTAMP(timezone=True),
        nullable=True,
        comment="When the violation was resolved",
    )
    resolution_notes = Column(
        Text,
        nullable=True,
        comment="Notes about how the violation was resolved",
    )

    # Define indexes for better query performance
    __table_args__ = (
        Index("idx_violations_severity_status", "severity", "status"),
        Index("idx_violations_type_framework", "violation_type", "framework"),
        Index("idx_violations_assigned", "assigned_to_email", "status"),
        # GIN indexes for JSONB queries
        Index(
            "idx_violations_evidence_gin",
            "evidence",
            postgresql_using="gin",
        ),
        Index(
            "idx_violations_recommendations_gin",
            "recommendations",
            postgresql_using="gin",
        ),
        Index(
            "idx_violations_ai_metadata_gin",
            "ai_metadata",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        """String representation."""
        return f"<Violation(id={self.id}, severity={self.severity}, type={self.violation_type})>"

    @property
    def is_critical(self) -> bool:
        """Check if violation is critical severity."""
        return self.severity == ViolationSeverity.CRITICAL

    @property
    def is_open(self) -> bool:
        """Check if violation is still open."""
        return self.status in [ViolationStatus.OPEN, ViolationStatus.ASSIGNED, ViolationStatus.IN_PROGRESS]

    @property
    def is_resolved(self) -> bool:
        """Check if violation has been resolved."""
        return self.status in [ViolationStatus.REMEDIATED, ViolationStatus.FALSE_POSITIVE]

    @property
    def confidence_score(self) -> Optional[float]:
        """Get AI confidence score for this violation."""
        if self.ai_metadata:
            return self.ai_metadata.get("confidence_score")
        return None

    @property
    def estimated_penalty_range(self) -> tuple[Optional[float], Optional[float]]:
        """Get estimated penalty range."""
        if self.recommendations and "financial_risk" in self.recommendations:
            risk = self.recommendations["financial_risk"]
            return (
                risk.get("estimated_penalty_min"),
                risk.get("estimated_penalty_max")
            )
        return (None, None)

    def assign_to(self, email: str, name: str) -> None:
        """
        Assign violation to a person for remediation.

        Args:
            email: Email address of assignee.
            name: Name of assignee.
        """
        self.assigned_to_email = email
        self.assigned_to_name = name
        self.status = ViolationStatus.ASSIGNED

    def mark_as_remediated(self, notes: str) -> None:
        """
        Mark violation as remediated.

        Args:
            notes: Resolution notes.
        """
        self.status = ViolationStatus.REMEDIATED
        self.resolution_notes = notes
        from datetime import datetime
        self.resolved_at = datetime.utcnow()

    def mark_as_false_positive(self, notes: str) -> None:
        """
        Mark violation as false positive.

        Args:
            notes: Explanation of why it's a false positive.
        """
        self.status = ViolationStatus.FALSE_POSITIVE
        self.resolution_notes = notes
        from datetime import datetime
        self.resolved_at = datetime.utcnow()

    def get_evidence_quote(self, source: str = "source") -> Optional[str]:
        """
        Get evidence quote from source or target.

        Args:
            source: Either "source" or "target".

        Returns:
            The quote if available.
        """
        if self.evidence:
            return self.evidence.get(f"{source}_quote")
        return None

    def to_summary_dict(self) -> Dict[str, Any]:
        """
        Get a summary dictionary for API responses.

        Returns:
            Dictionary with key violation information.
        """
        return {
            "id": str(self.id),
            "severity": self.severity,
            "status": self.status,
            "violation_type": self.violation_type,
            "finding_summary": self.finding_summary,
            "rule_citation": self.rule_citation,
            "confidence_score": self.confidence_score,
            "source_document": self.source_document_data,
            "target_document": self.target_document_data,
            "evidence": {
                "source_quote": self.get_evidence_quote("source"),
                "target_quote": self.get_evidence_quote("target"),
            },
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "assigned_to": self.assigned_to_email,
        }

    def to_detailed_dict(self) -> Dict[str, Any]:
        """
        Get a detailed dictionary for full API responses.

        Returns:
            Dictionary with all violation information.
        """
        return {
            "id": str(self.id),
            "severity": self.severity,
            "status": self.status,
            "framework": self.framework,
            "rule_citation": self.rule_citation,
            "violation_type": self.violation_type,
            "finding_summary": self.finding_summary,
            "explanation": self.explanation,
            "evidence": self.evidence,
            "source_document": self.source_document_data,
            "target_document": self.target_document_data,
            "recommendations": self.recommendations,
            "ai_metadata": self.ai_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "assigned_to": {
                "email": self.assigned_to_email,
                "name": self.assigned_to_name,
            } if self.assigned_to_email else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution_notes": self.resolution_notes,
        }