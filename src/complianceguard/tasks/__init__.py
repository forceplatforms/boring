"""
Background tasks for ComplianceGuard.

This module contains Celery tasks for asynchronous processing of documents
and other long-running operations.
"""

from complianceguard.tasks.compliance_scan import process_compliance_scan
from complianceguard.tasks.ingest import process_document_indexing

__all__ = ["process_document_indexing", "process_compliance_scan"]
