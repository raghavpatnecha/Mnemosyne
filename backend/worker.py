"""
Celery worker configuration
Task queue for asynchronous document processing
"""

from celery import Celery
from backend.config import settings

celery_app = Celery(
    "mnemosyne",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "backend.tasks.process_document",
        "backend.tasks.retry_pending_documents"
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
    worker_max_tasks_per_child=1000,
    worker_prefetch_multiplier=4,
)

# Celery Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'retry-pending-documents': {
        'task': 'retry_pending_documents',
        'schedule': 600.0,  # Run every 10 minutes (600 seconds)
        'options': {
            'expires': 300.0,  # Task expires after 5 minutes if not executed
        }
    },
}
