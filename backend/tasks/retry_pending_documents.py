"""
Retry Pending Documents Task
Periodic Celery task to automatically retry stuck or failed document processing
"""

import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.worker import celery_app
from backend.database import SessionLocal
from backend.models.document import Document
from backend.tasks.process_document import process_document_task

logger = logging.getLogger(__name__)

# Configuration
STUCK_THRESHOLD_MINUTES = 15  # Documents pending for >15 min are considered stuck
PROCESSING_TIMEOUT_MINUTES = 30  # Documents processing for >30 min are considered crashed
MAX_RETRY_ATTEMPTS = 3  # Max retry attempts before giving up
RETRY_STATUSES = ["pending", "processing", "failed"]  # Statuses eligible for retry


@celery_app.task(name="retry_pending_documents")
def retry_pending_documents_task():
    """
    Periodic task to retry processing for stuck/failed documents

    Runs every 10 minutes to catch:
    - Documents stuck in 'pending' for >15 minutes (task never picked up)
    - Documents stuck in 'processing' for >30 minutes (worker crash during processing)
    - Documents in 'failed' status with retry count < max_retries

    Tracks retry attempts in processing_info.retry_count to avoid infinite loops.
    The 'processing' recovery is critical for production reliability - when a worker
    crashes or restarts mid-task, the document gets stuck at 'processing' forever
    since the task was already dequeued from Redis.
    """
    db: Session = SessionLocal()

    try:
        # Calculate timestamp thresholds for stuck documents (timezone-aware)
        stuck_threshold = datetime.now(timezone.utc) - timedelta(minutes=STUCK_THRESHOLD_MINUTES)
        processing_threshold = datetime.now(timezone.utc) - timedelta(minutes=PROCESSING_TIMEOUT_MINUTES)

        logger.info(f"[Retry Task] Starting retry scan for stuck/failed documents...")

        # Query for documents eligible for retry
        # 1. Stuck pending documents: status='pending' AND updated_at < threshold
        stuck_pending = db.query(Document).filter(
            and_(
                Document.status == "pending",
                Document.updated_at < stuck_threshold
            )
        ).all()

        # 2. Stuck processing documents: status='processing' AND updated_at < processing_threshold
        # These are documents where the worker crashed/restarted mid-processing
        stuck_processing = db.query(Document).filter(
            and_(
                Document.status == "processing",
                Document.updated_at < processing_threshold
            )
        ).all()

        # 3. Failed documents: status='failed' (will filter by retry_count in Python)
        failed_docs = db.query(Document).filter(
            Document.status == "failed"
        ).all()

        # Filter failed documents by retry_count in Python (simpler than SQL JSON queries)
        failed_with_retries = [
            doc for doc in failed_docs
            if doc.processing_info.get('retry_count', 0) < MAX_RETRY_ATTEMPTS
        ]

        # Combine all lists
        documents_to_retry = stuck_pending + stuck_processing + failed_with_retries

        if stuck_processing:
            logger.warning(
                f"[Retry Task] Found {len(stuck_processing)} documents stuck in 'processing' "
                f"for >{PROCESSING_TIMEOUT_MINUTES} min (worker crash recovery)"
            )

        if not documents_to_retry:
            logger.info("[Retry Task] No stuck/failed documents found. All clear!")
            return {
                "status": "success",
                "retried_count": 0,
                "message": "No documents to retry"
            }

        logger.info(f"[Retry Task] Found {len(documents_to_retry)} documents to retry")

        retried_count = 0
        skipped_count = 0

        for document in documents_to_retry:
            try:
                # Get current retry count from processing_info
                retry_count = document.processing_info.get('retry_count', 0)

                # Increment retry count
                new_retry_count = retry_count + 1

                # Safety check: Skip if somehow exceeded max retries (shouldn't happen)
                if new_retry_count > MAX_RETRY_ATTEMPTS:
                    logger.warning(
                        f"[Retry Task] Document {document.id} ({document.filename}) "
                        f"would exceed max retries ({new_retry_count}/{MAX_RETRY_ATTEMPTS}), skipping"
                    )
                    skipped_count += 1
                    continue

                # Update processing_info with retry metadata
                document.processing_info['retry_count'] = new_retry_count
                document.processing_info['last_retry_at'] = datetime.now(timezone.utc).isoformat()
                # Determine retry reason based on current status
                if document.status == "pending":
                    retry_reason = "stuck_pending"
                elif document.status == "processing":
                    retry_reason = "stuck_processing"  # Worker crashed mid-processing
                else:
                    retry_reason = "failed_processing"
                document.processing_info['retry_reason'] = retry_reason

                # Reset status to pending for retry
                document.status = "pending"
                document.error_message = None  # Clear previous error

                db.commit()

                # Trigger async processing task
                process_document_task.delay(str(document.id))

                logger.info(
                    f"[Retry Task] ✅ Retrying document {document.id} ({document.filename}) "
                    f"- Attempt {new_retry_count}/{MAX_RETRY_ATTEMPTS}"
                )
                retried_count += 1

            except Exception as doc_error:
                logger.error(
                    f"[Retry Task] ❌ Failed to retry document {document.id}: {doc_error}",
                    exc_info=True
                )
                db.rollback()
                continue

        logger.info(
            f"[Retry Task] Completed: {retried_count} retried, {skipped_count} skipped"
        )

        return {
            "status": "success",
            "retried_count": retried_count,
            "skipped_count": skipped_count,
            "total_found": len(documents_to_retry)
        }

    except Exception as e:
        logger.error(f"[Retry Task] Fatal error in retry task: {e}", exc_info=True)
        db.rollback()
        return {
            "status": "error",
            "error": str(e)
        }

    finally:
        db.close()
