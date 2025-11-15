"""
Celery tasks for compliance scanning.

This module contains background tasks that handle the time-consuming process
of running compliance checks against documents.
"""

import asyncio
import logging
import time
from typing import Optional
from uuid import UUID

from complianceguard.celery_app import app
from complianceguard.config import get_settings
from complianceguard.database import get_async_db
from complianceguard.services.compliance_analyzer import ComplianceAnalyzer

logger = logging.getLogger(__name__)
settings = get_settings()


@app.task(
    bind=True,
    name="process_compliance_scan",
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=3600,  # 1 hour
    retry_jitter=True,
)
def process_compliance_scan(
    self,
    scan_job_id: str,
    framework_id: str,
    document_ids: list[str],
    triggered_by_email: Optional[str] = None,
    triggered_by_name: Optional[str] = None,
) -> dict:
    """
    Background task to run compliance scan.

    This task performs the following steps:
    1. Load scan job from database
    2. Mark as 'running'
    3. For each compliance requirement:
       - Query Milvus for relevant pages
       - Extract text from pages
       - Analyze compliance using Gemini
       - Create violation records if non-compliant
    4. Update scan job status to 'completed' or 'failed'

    Args:
        self: Task instance (bound)
        scan_job_id: UUID of the scan job
        framework_id: UUID of the compliance framework
        document_ids: List of document UUIDs to analyze
        triggered_by_email: Email of user who triggered scan
        triggered_by_name: Name of user who triggered scan

    Returns:
        dict: Task result with status and metadata
    """
    task_id = self.request.id
    logger.info(f"[TASK {task_id}] Starting compliance scan for job {scan_job_id}")

    # Run async compliance scan in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            _async_run_compliance_scan(
                scan_job_id=UUID(scan_job_id),
                framework_id=UUID(framework_id),
                document_ids=[UUID(doc_id) for doc_id in document_ids],
                triggered_by_email=triggered_by_email,
                triggered_by_name=triggered_by_name,
                task_id=task_id,
            )
        )
        logger.info(f"[TASK {task_id}] ✓ Compliance scan completed successfully")
        return result
    except Exception as e:
        logger.error(f"[TASK {task_id}] ✗ Compliance scan failed: {e}")
        raise
    finally:
        loop.close()


async def _async_run_compliance_scan(
    scan_job_id: UUID,
    framework_id: UUID,
    document_ids: list[UUID],
    triggered_by_email: Optional[str],
    triggered_by_name: Optional[str],
    task_id: str,
) -> dict:
    """
    Async helper function to perform compliance scanning.

    This function contains the actual compliance check logic.
    """
    scan_start = time.time()

    # Create new database session for this task
    async for db in get_async_db():
        try:
            logger.info(f"[TASK {task_id}] Creating ComplianceAnalyzer")

            # Create analyzer instance
            analyzer = ComplianceAnalyzer(db)

            # Run compliance check
            # Note: The analyzer will update the scan job status internally
            logger.info(f"[TASK {task_id}] Running compliance check for scan job {scan_job_id}")
            result_scan_job_id = await analyzer.run_compliance_check(
                framework_id=framework_id,
                document_ids=document_ids,
                triggered_by_email=triggered_by_email,
                triggered_by_name=triggered_by_name,
            )

            scan_total_time = time.time() - scan_start
            logger.info(
                f"[TASK {task_id}] ✓ Complete compliance scan finished in {scan_total_time:.3f}s"
            )

            # Get final scan job results
            from complianceguard.crud import scan_job as scan_job_crud
            final_scan_job = await scan_job_crud.get_scan_job(db, result_scan_job_id)

            return {
                "status": final_scan_job.status if final_scan_job else "completed",
                "scan_job_id": str(result_scan_job_id),
                "violations_found": final_scan_job.violations_found if final_scan_job else 0,
                "scan_time": scan_total_time,
            }

        except Exception as scan_error:
            # Log error - the ComplianceAnalyzer should have updated the scan job status
            scan_error_time = time.time() - scan_start
            logger.error(
                f"[TASK {task_id}] ✗ Compliance scan failed after {scan_error_time:.3f}s"
            )
            logger.error(f"[TASK {task_id}] Error: {type(scan_error).__name__}: {scan_error}")
            logger.exception(f"[TASK {task_id}] Full traceback:")

            # Re-raise exception for Celery to handle retries
            raise scan_error

        finally:
            # Ensure DB session is closed
            await db.close()
