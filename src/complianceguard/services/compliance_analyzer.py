"""
Compliance Analyzer service - orchestrates compliance checking workflow.

This service coordinates the entire compliance checking process:
1. Queries Milvus for relevant pages (framework + user docs)
2. Extracts text from pages using Landing AI (with DB caching)
3. Analyzes compliance using Gemini API
4. Creates violation records for non-compliant findings
5. Tracks progress via ScanJob
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from complianceguard.config import get_settings
from complianceguard.crud.compliance_framework import get_compliance_framework
from complianceguard.crud.document import get_document
from complianceguard.crud.document_chunk import get_chunks_by_page
from complianceguard.crud.scan_job import create_scan_job, update_scan_job_status
from complianceguard.crud.violation import create_violation
from complianceguard.indexing import DocumentIndex
from complianceguard.services.gemini import (
    ComplianceCheckResult,
    get_gemini_client,
)
from complianceguard.services.landing_ai import get_landing_ai_client

logger = logging.getLogger(__name__)
settings = get_settings()


class ComplianceAnalyzer:
    """
    Main orchestrator for compliance checking workflow.

    Example:
        >>> analyzer = ComplianceAnalyzer(db_session)
        >>> scan_job = await analyzer.run_compliance_check(
        ...     framework_id=framework_uuid,
        ...     document_ids=[doc1_uuid, doc2_uuid],
        ...     triggered_by_email="user@example.com"
        ... )
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the compliance analyzer.

        Args:
            db: Database session
        """
        self.db = db
        self.gemini_client = get_gemini_client()
        self.landing_ai_client = get_landing_ai_client()
        self.settings = get_settings()

    async def run_compliance_check(
        self,
        framework_id: UUID,
        document_ids: list[UUID],
        triggered_by_email: Optional[str] = None,
        triggered_by_name: Optional[str] = None,
        topk_per_query: int = 5,
    ) -> UUID:
        """
        Run compliance check for documents against a framework.

        Args:
            framework_id: UUID of the compliance framework
            document_ids: List of document UUIDs to check
            triggered_by_email: Email of user who triggered the scan
            triggered_by_name: Name of user who triggered the scan
            topk_per_query: Number of top pages to retrieve per query (default: 5)

        Returns:
            UUID of the created scan job

        Raises:
            ValueError: If framework not found or inactive
            Exception: If compliance check fails
        """
        # Get framework
        framework = await get_compliance_framework(self.db, framework_id)
        if not framework:
            raise ValueError(f"Compliance framework {framework_id} not found")
        if not framework.is_active:
            raise ValueError(f"Compliance framework {framework.name} is not active")

        logger.info(
            f"[COMPLIANCE] Starting compliance check for framework '{framework.name}' "
            f"with {len(document_ids)} document(s)"
        )

        # Create scan job
        scan_job = await create_scan_job(
            self.db,
            framework=framework.name,
            scan_type="targeted",
            document_ids=document_ids,
            configuration={
                "framework_id": str(framework_id),
                "framework_index_name": framework.framework_index_name,
                "topk_per_query": topk_per_query,
                "total_todos": len(framework.compliance_todos),
            },
            triggered_by_email=triggered_by_email,
            triggered_by_name=triggered_by_name,
            trigger_source="api",
        )

        logger.info(f"[COMPLIANCE] Created scan job {scan_job.id}")

        # Mark as running
        await update_scan_job_status(
            self.db,
            scan_job.id,
            status="running",
        )

        try:
            # Run the compliance analysis
            results = await self._analyze_compliance(
                framework=framework,
                document_ids=document_ids,
                topk_per_query=topk_per_query,
            )

            # Mark as completed
            await update_scan_job_status(
                self.db,
                scan_job.id,
                status="completed",
                results=results,
            )

            logger.info(
                f"[COMPLIANCE] Scan job {scan_job.id} completed successfully. "
                f"Found {results['violations_found']} violation(s)"
            )

            return scan_job.id

        except Exception as e:
            logger.error(f"[COMPLIANCE] Scan job {scan_job.id} failed: {e}", exc_info=True)

            # Mark as failed
            await update_scan_job_status(
                self.db,
                scan_job.id,
                status="failed",
                error_message=str(e),
                error_details={"error_type": type(e).__name__},
            )

            raise

    async def _analyze_compliance(
        self,
        framework,
        document_ids: list[UUID],
        topk_per_query: int,
    ) -> dict:
        """
        Perform the actual compliance analysis.

        Args:
            framework: ComplianceFramework instance
            document_ids: List of document UUIDs to check
            topk_per_query: Number of top pages per query

        Returns:
            Dictionary with analysis results
        """
        violation_ids = []
        documents_processed = 0
        documents_failed = 0
        total_todos = len(framework.compliance_todos)

        logger.info(f"[COMPLIANCE] Analyzing {total_todos} compliance requirement(s)")

        # Get framework index name from ComplianceFramework
        framework_index_name = framework.framework_index_name

        # For user documents, we need to determine the index name
        # Assuming documents were ingested with a specific index name
        # For now, we'll use the default or a convention
        # TODO: This should come from IngestedDocument table mapping
        user_docs_index_name = self.settings.indexing_default_collection

        # Create document indexes
        framework_index = DocumentIndex(index_name=framework_index_name)
        user_docs_index = DocumentIndex(index_name=user_docs_index_name)

        # Process each compliance todo
        for todo_idx, todo in enumerate(framework.compliance_todos, 1):
            logger.info(
                f"[COMPLIANCE] Processing todo {todo_idx}/{total_todos}: {todo[:100]}..."
            )

            try:
                # Query both indexes in parallel
                framework_results, user_docs_results = await asyncio.gather(
                    framework_index.search(query=todo, topk=topk_per_query),
                    user_docs_index.search(query=todo, topk=topk_per_query),
                    return_exceptions=True,
                )

                # Check for exceptions
                if isinstance(framework_results, Exception):
                    logger.error(
                        f"[COMPLIANCE] Framework index search failed: {framework_results}"
                    )
                    framework_results = []
                if isinstance(user_docs_results, Exception):
                    logger.error(
                        f"[COMPLIANCE] User docs index search failed: {user_docs_results}"
                    )
                    user_docs_results = []

                logger.info(
                    f"[COMPLIANCE] Found {len(framework_results)} framework pages, "
                    f"{len(user_docs_results)} user doc pages"
                )

                # Extract text from framework pages
                framework_text = await self._extract_text_from_results(framework_results)

                # Extract text from user doc pages
                user_docs_text = await self._extract_text_from_results(user_docs_results)

                logger.info(
                    f"[COMPLIANCE] Extracted {len(framework_text)} chars from framework, "
                    f"{len(user_docs_text)} chars from user docs"
                )

                # Analyze with Gemini
                compliance_result = await self.gemini_client.check_compliance(
                    requirement=todo,
                    framework_text=framework_text,
                    document_text=user_docs_text,
                )

                logger.info(
                    f"[COMPLIANCE] Gemini analysis complete. "
                    f"Status: {compliance_result.status}, "
                    f"Confidence: {compliance_result.confidence_score:.2f}"
                )

                # Create violation if non-compliant or partial
                if compliance_result.status in ["non_compliant", "partial"]:
                    violation_id = await self._create_violation_from_result(
                        framework=framework,
                        todo=todo,
                        compliance_result=compliance_result,
                        framework_results=framework_results,
                        user_docs_results=user_docs_results,
                        document_ids=document_ids,
                    )
                    violation_ids.append(str(violation_id))

                    logger.info(
                        f"[COMPLIANCE] Created violation {violation_id} "
                        f"for todo {todo_idx}/{total_todos}"
                    )

            except Exception as e:
                logger.error(
                    f"[COMPLIANCE] Error processing todo {todo_idx}/{total_todos}: {e}",
                    exc_info=True,
                )
                documents_failed += 1
                continue

        documents_processed = len(document_ids) - documents_failed

        # Count violations by severity
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        # Note: Would need to query violations to get exact counts
        # For now, just return the total

        results = {
            "violations_found": len(violation_ids),
            "documents_processed": documents_processed,
            "documents_failed": documents_failed,
            "violation_ids": violation_ids,
            "failed_document_ids": [],
            "todos_processed": total_todos,
            **{f"{k}_count": v for k, v in severity_counts.items()},
        }

        return results

    async def _extract_text_from_results(
        self, search_results: list[tuple]
    ) -> str:
        """
        Extract text from search results using cached LandingAI extraction.

        Args:
            search_results: List of (score, doc_id, filepath, page_url, file_hash) tuples

        Returns:
            Combined text from all pages with extracted content from LandingAI
        """
        if not search_results:
            return ""

        from complianceguard.crud import document_chunk as chunk_crud
        from complianceguard.crud.ingested_document import get_ingested_document_by_hash

        text_parts = []

        for score, milvus_doc_id, filepath, page_url, file_hash in search_results:
            logger.info(
                f"[COMPLIANCE] Extracting text from milvus_doc_id {milvus_doc_id} "
                f"(score: {score:.4f}, file_hash: {file_hash[:16]}...)"
            )

            try:
                # First, get the actual document UUID using file_hash
                document = await get_ingested_document_by_hash(self.db, file_hash)
                if not document:
                    logger.warning(
                        f"[COMPLIANCE] No document found with file_hash {file_hash[:16]}..."
                    )
                    text_parts.append(
                        f"[Document: {filepath}, Relevance: {score:.2f}]\n"
                        f"[Document not found in database]"
                    )
                    continue

                document_uuid = document.id

                # Extract page number from page_url
                # page_url format: /path/to/file.pdf#page=N
                page_number = 1  # Default to page 1
                if "#page=" in page_url:
                    try:
                        page_number = int(page_url.split("#page=")[1])
                    except (IndexError, ValueError):
                        logger.warning(f"Could not parse page number from {page_url}")

                # Query DocumentChunk table for the extracted LandingAI text
                try:
                    chunks = await chunk_crud.get_chunks_by_page(
                        db=self.db,
                        document_id=document_uuid,
                        page_number=page_number,
                    )
                except Exception as db_error:
                    logger.error(
                        f"[COMPLIANCE] Database error querying chunks for doc {document_uuid}, "
                        f"page {page_number}: {db_error}"
                    )
                    # Rollback the transaction on error
                    await self.db.rollback()
                    chunks = []

                if chunks:
                    # Combine all chunks from this page
                    page_text = "\n\n".join([chunk.content for chunk in chunks])
                    text_parts.append(
                        f"[Document: {filepath}, Page {page_number}, Relevance: {score:.2f}]\n"
                        f"{page_text}"
                    )
                    logger.info(
                        f"[COMPLIANCE] ✓ Extracted {len(page_text)} characters from "
                        f"{len(chunks)} chunk(s) on page {page_number}"
                    )
                else:
                    # No chunks found - provide detailed diagnostic info
                    logger.warning(
                        f"[COMPLIANCE] ⚠ No chunks found for document {document_uuid}, page {page_number}"
                    )
                    logger.info(
                        f"[COMPLIANCE] Diagnostic info: file_hash={file_hash[:16]}..., "
                        f"filepath={filepath}, milvus_doc_id={milvus_doc_id}"
                    )

                    # Check if document has any chunks at all
                    try:
                        from sqlalchemy import select, func
                        from complianceguard.models.document_chunk import DocumentChunk as ChunkModel

                        total_chunks_query = select(func.count(ChunkModel.id)).where(
                            ChunkModel.document_id == document_uuid
                        )
                        total_chunks_result = await self.db.execute(total_chunks_query)
                        total_chunks = total_chunks_result.scalar()

                        if total_chunks == 0:
                            logger.warning(
                                f"[COMPLIANCE] ⚠ Document {document_uuid} has NO chunks in database - "
                                f"LandingAI extraction may have failed during ingestion"
                            )
                        else:
                            logger.info(
                                f"[COMPLIANCE] Document has {total_chunks} total chunks, "
                                f"but none on page {page_number}"
                            )
                    except Exception as diag_error:
                        logger.error(f"[COMPLIANCE] Error checking chunk count: {diag_error}")

                    text_parts.append(
                        f"[Document: {filepath}, Page {page_number}, Relevance: {score:.2f}]\n"
                        f"[No extracted text available - document may not be fully indexed yet]"
                    )

            except Exception as e:
                logger.error(
                    f"[COMPLIANCE] Error extracting text from milvus_doc_id {milvus_doc_id} "
                    f"(file_hash: {file_hash[:16]}...): {e}"
                )
                # Rollback on any error
                try:
                    await self.db.rollback()
                except:
                    pass
                text_parts.append(
                    f"[Document: {filepath}, Relevance: {score:.2f}]\n"
                    f"[Error extracting text: {str(e)}]"
                )

        return "\n\n".join(text_parts)

    async def _create_violation_from_result(
        self,
        framework,
        todo: str,
        compliance_result: ComplianceCheckResult,
        framework_results: list[tuple],
        user_docs_results: list[tuple],
        document_ids: list[UUID],
    ) -> UUID:
        """
        Create a violation record from Gemini analysis result.

        Args:
            framework: ComplianceFramework instance
            todo: The compliance requirement that was checked
            compliance_result: Result from Gemini analysis
            framework_results: Search results from framework index
            user_docs_results: Search results from user docs index
            document_ids: List of document UUIDs being checked

        Returns:
            UUID of created violation
        """
        # Get document metadata for the first user doc (simplified)
        source_doc_id = document_ids[0] if document_ids else None
        target_doc_id = document_ids[0] if document_ids else None

        # Get actual document records
        source_doc = None
        target_doc = None
        if source_doc_id:
            source_doc = await get_document(self.db, source_doc_id)
        if target_doc_id:
            target_doc = await get_document(self.db, target_doc_id)

        # Build evidence from search results
        evidence = {
            "source_quote": compliance_result.framework_evidence,
            "source_pages": [
                {"page": doc_id, "filepath": filepath, "score": float(score)}
                for score, doc_id, filepath, page_url, file_hash in framework_results[:3]
            ],
            "target_quote": compliance_result.document_evidence,
            "target_pages": [
                {"page": doc_id, "filepath": filepath, "score": float(score)}
                for score, doc_id, filepath, page_url, file_hash in user_docs_results[:3]
            ],
            "discrepancy_type": "compliance_gap",
            "gap_analysis": compliance_result.gap_analysis,
        }

        # Build AI metadata
        ai_metadata = {
            "model": "google-gemini",
            "model_version": self.settings.gemini_model,
            "confidence_score": compliance_result.confidence_score,
            "analysis_timestamp": datetime.utcnow().isoformat(),
            "prompt_template_version": "v1.0",
        }

        # Build recommendations
        recommendations = {
            "actions": [
                {
                    "priority": "high" if compliance_result.risk_level == "critical" else "medium",
                    "description": compliance_result.remediation,
                    "timeline": "Immediate" if compliance_result.risk_level == "critical" else "Within 30 days",
                    "responsible_party": "Compliance Officer",
                }
            ],
        }

        # Create denormalized document data
        source_document_data = {
            "id": str(source_doc.id) if source_doc else "unknown",
            "file_name": source_doc.file_name if source_doc else "unknown",
            "doc_type": source_doc.doc_type if source_doc else "unknown",
        }

        target_document_data = {
            "id": str(target_doc.id) if target_doc else "unknown",
            "file_name": target_doc.file_name if target_doc else "unknown",
            "doc_type": target_doc.doc_type if target_doc else "unknown",
        }

        # Create violation
        violation = await create_violation(
            self.db,
            source_document_id=source_doc_id or document_ids[0],
            source_document_data=source_document_data,
            target_document_id=target_doc_id or document_ids[0],
            target_document_data=target_document_data,
            framework=framework.name,
            rule_citation=todo,
            severity=compliance_result.risk_level,
            violation_type="compliance_gap",
            finding_summary=f"{compliance_result.status}: {todo[:100]}...",
            explanation=compliance_result.explanation,
            evidence=evidence,
            ai_metadata=ai_metadata,
            recommendations=recommendations,
            status="open",
        )

        return violation.id


async def analyze_compliance(
    db: AsyncSession,
    framework_id: UUID,
    document_ids: list[UUID],
    triggered_by_email: Optional[str] = None,
    triggered_by_name: Optional[str] = None,
) -> UUID:
    """
    Convenience function to run compliance analysis.

    Args:
        db: Database session
        framework_id: UUID of compliance framework
        document_ids: List of document UUIDs to analyze
        triggered_by_email: Email of user who triggered the scan
        triggered_by_name: Name of user who triggered the scan

    Returns:
        UUID of created scan job
    """
    analyzer = ComplianceAnalyzer(db)
    return await analyzer.run_compliance_check(
        framework_id=framework_id,
        document_ids=document_ids,
        triggered_by_email=triggered_by_email,
        triggered_by_name=triggered_by_name,
    )
