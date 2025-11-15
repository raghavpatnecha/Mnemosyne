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
    include=["backend.tasks.process_document"]
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
