"""
Pydantic schemas for violation-related API endpoints.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from complianceguard.schemas.base import BaseSchema, TimestampMixin


class ViolationEvidence(BaseSchema):
    """Evidence supporting a violation."""

    source_quote: str = Field(..., description="Quote from source document")
    source_page: Optional[int] = Field(None, description="Page number in source")
    source_section: Optional[str] = Field(None, description="Section in source")
    target_quote: str = Field(..., description="Quote from target document")
    target_page: Optional[int] = Field(None, description="Page number in target")
    target_section: Optional[str] = Field(None, description="Section in target")

    class Config:
        json_schema_extra = {
            "example": {
                "source_quote": "Ransomware attack confirmed. 47,000 customer records exfiltrated...",
                "source_page": 3,
                "source_section": "Impact Assessment",
                "target_quote": "We may be subject to hypothetical cyber risks in the future...",
                "target_page": 1,
                "target_section": "Item 1.05 - Risk Factors",
            }
        }


class ViolationRecommendation(BaseSchema):
    """Recommendation for remediation."""

    priority: str = Field(..., description="Priority level (immediate, high, medium, low)")
    description: str = Field(..., description="Recommended action")
    timeline: str = Field(..., description="Suggested timeline")
    responsible_party: Optional[str] = Field(None, description="Who should handle this")

    class Config:
        json_schema_extra = {
            "example": {
                "priority": "immediate",
                "description": "Alert General Counsel and Compliance Team",
                "timeline": "Within 2 hours",
                "responsible_party": "Chief Compliance Officer",
            }
        }


class ViolationSummary(BaseSchema, TimestampMixin):
    """Summary view of a violation for list endpoints."""

    id: UUID = Field(..., description="Unique violation identifier")
    severity: str = Field(..., description="Severity level")
    status: str = Field(..., description="Current status")
    violation_type: str = Field(..., description="Type of violation")
    finding_summary: str = Field(..., description="Brief summary")
    rule_citation: str = Field(..., description="Rule or regulation citation")
    confidence_score: Optional[float] = Field(None, description="AI confidence score (0-1)")
    source_document_name: str = Field(..., description="Source document file name")
    target_document_name: str = Field(..., description="Target document file name")
    assigned_to: Optional[str] = Field(None, description="Assigned user email")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "650e8400-e29b-41d4-a716-446655440001",
                "severity": "critical",
                "status": "open",
                "violation_type": "material_omission",
                "finding_summary": "Material cybersecurity incident not disclosed in SEC filing",
                "rule_citation": "SEC Regulation S-K Item 1C",
                "confidence_score": 0.95,
                "source_document_name": "CISO_Report_October_2024.pdf",
                "target_document_name": "Form_8K_Draft.docx",
                "assigned_to": None,
                "created_at": "2025-11-07T16:30:00Z",
                "updated_at": "2025-11-07T16:30:00Z",
            }
        }


class ViolationDetail(ViolationSummary):
    """Detailed view of a violation with full evidence and recommendations."""

    explanation: str = Field(..., description="Detailed explanation of the violation")
    evidence: ViolationEvidence = Field(..., description="Supporting evidence")
    recommendations: list[ViolationRecommendation] = Field(
        ..., description="Recommended actions"
    )
    suggested_language: Optional[str] = Field(
        None, description="Suggested compliant language"
    )
    financial_risk: dict = Field(..., description="Estimated financial risk")
    ai_metadata: dict = Field(..., description="AI analysis metadata")
    source_document_id: UUID = Field(..., description="Source document ID")
    target_document_id: UUID = Field(..., description="Target document ID")
    framework: str = Field(..., description="Compliance framework")
    resolved_at: Optional[datetime] = Field(None, description="Resolution timestamp")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "650e8400-e29b-41d4-a716-446655440001",
                "severity": "critical",
                "status": "open",
                "violation_type": "material_omission",
                "finding_summary": "Material cybersecurity incident not disclosed in SEC filing",
                "rule_citation": "SEC Regulation S-K Item 1C",
                "confidence_score": 0.95,
                "source_document_name": "CISO_Report_October_2024.pdf",
                "target_document_name": "Form_8K_Draft.docx",
                "assigned_to": None,
                "explanation": "The CISO report documents a material ransomware attack affecting 47,000 customer records on October 27, 2024. However, the Form 8-K filing only contains generic risk factor language about hypothetical future cyber risks, with no mention of this specific incident.",
                "evidence": {
                    "source_quote": "Ransomware attack confirmed. 47,000 customer records exfiltrated...",
                    "source_page": 3,
                    "source_section": "Impact Assessment",
                    "target_quote": "We may be subject to hypothetical cyber risks in the future...",
                    "target_page": 1,
                    "target_section": "Item 1.05 - Risk Factors",
                },
                "recommendations": [
                    {
                        "priority": "immediate",
                        "description": "Alert General Counsel and Board of Directors",
                        "timeline": "Within 2 hours",
                        "responsible_party": "Chief Compliance Officer",
                    },
                    {
                        "priority": "high",
                        "description": "File amended Form 8-K with accurate disclosure",
                        "timeline": "Within 4 business days",
                        "responsible_party": "Legal Department",
                    },
                ],
                "suggested_language": "On October 27, 2024, the Company experienced a cybersecurity incident involving unauthorized access to customer data. Approximately 47,000 customer records were potentially affected. The Company has engaged external cybersecurity experts and is working with law enforcement...",
                "financial_risk": {
                    "estimated_penalty_min": 1500000,
                    "estimated_penalty_max": 7000000,
                    "basis": "Recent SEC enforcement actions for similar violations",
                    "precedents": [
                        {"company": "Example Corp", "penalty": 3500000, "year": 2024}
                    ],
                },
                "ai_metadata": {
                    "model": "claude-3-sonnet",
                    "model_version": "20240229-v1:0",
                    "confidence_score": 0.95,
                    "processing_time_ms": 3420,
                    "prompt_tokens": 4500,
                    "completion_tokens": 1200,
                    "total_cost_usd": 0.0576,
                },
                "source_document_id": "550e8400-e29b-41d4-a716-446655440000",
                "target_document_id": "551e8400-e29b-41d4-a716-446655440001",
                "framework": "SEC_CYBER",
                "resolved_at": None,
                "resolution_notes": None,
                "created_at": "2025-11-07T16:30:00Z",
                "updated_at": "2025-11-07T16:30:00Z",
            }
        }


class ViolationListFilters(BaseSchema):
    """Filters for violation list endpoint."""

    severity: Optional[str] = Field(None, description="Filter by severity")
    status: Optional[str] = Field(None, description="Filter by status")
    violation_type: Optional[str] = Field(None, description="Filter by type")
    framework: Optional[str] = Field(None, description="Filter by framework")
    assigned_to: Optional[str] = Field(None, description="Filter by assignee")

    class Config:
        json_schema_extra = {
            "example": {
                "severity": "critical",
                "status": "open",
                "violation_type": "material_omission",
                "framework": "SEC_CYBER",
            }
        }


class ViolationUpdateRequest(BaseSchema):
    """Request to update violation status."""

    status: Optional[str] = Field(None, description="New status")
    assigned_to_email: Optional[str] = Field(None, description="Assignee email")
    assigned_to_name: Optional[str] = Field(None, description="Assignee name")
    resolution_notes: Optional[str] = Field(None, description="Resolution notes")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "remediated",
                "assigned_to_email": "compliance@company.com",
                "assigned_to_name": "Jane Smith",
                "resolution_notes": "Filed amended 8-K on November 8, 2024. Included full disclosure of incident.",
            }
        }


class ViolationStatsResponse(BaseSchema):
    """Violation statistics."""

    total_violations: int = Field(..., description="Total number of violations")
    by_severity: dict = Field(..., description="Count by severity level")
    by_status: dict = Field(..., description="Count by status")
    by_type: dict = Field(..., description="Count by violation type")
    total_financial_risk: dict = Field(..., description="Aggregated financial risk")
    avg_confidence_score: float = Field(..., description="Average AI confidence score")

    class Config:
        json_schema_extra = {
            "example": {
                "total_violations": 47,
                "by_severity": {
                    "critical": 12,
                    "high": 18,
                    "medium": 13,
                    "low": 4,
                },
                "by_status": {
                    "open": 23,
                    "assigned": 15,
                    "in_progress": 6,
                    "remediated": 3,
                },
                "by_type": {
                    "material_omission": 28,
                    "misleading_statement": 12,
                    "delayed_disclosure": 7,
                },
                "total_financial_risk": {
                    "min": 45000000,
                    "max": 210000000,
                    "currency": "USD",
                },
                "avg_confidence_score": 0.89,
            }
        }
