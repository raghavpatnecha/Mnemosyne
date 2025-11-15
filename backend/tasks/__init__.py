"""
Celery Tasks
Asynchronous background processing tasks
"""

from backend.tasks.process_document import process_document_task

__all__ = ["process_document_task"]
