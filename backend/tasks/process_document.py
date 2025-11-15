"""
Document Processing Task
Celery task for parsing, chunking, embedding, and storing documents
"""

import asyncio
import logging
from datetime import datetime
from typing import List
from celery import Task
from sqlalchemy.orm import Session

from backend.worker import celery_app
from backend.database import SessionLocal
from backend.models.document import Document
from backend.models.chunk import DocumentChunk
from backend.storage.local import LocalStorage
from backend.parsers import ParserFactory
from backend.chunking import ChonkieChunker
from backend.embeddings import OpenAIEmbedder

logger = logging.getLogger(__name__)


class ProcessDocumentTask(Task):
    """Celery task for processing documents"""

    def __init__(self):
        super().__init__()
        self._storage = None
        self._parser_factory = None
        self._chunker = None
        self._embedder = None

    @property
    def storage(self):
        if self._storage is None:
            self._storage = LocalStorage()
        return self._storage

    @property
    def parser_factory(self):
        if self._parser_factory is None:
            self._parser_factory = ParserFactory()
        return self._parser_factory

    @property
    def chunker(self):
        if self._chunker is None:
            self._chunker = ChonkieChunker()
        return self._chunker

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = OpenAIEmbedder()
        return self._embedder

    async def run(self, document_id: str):
        """
        Process document: parse → chunk → embed → store

        Args:
            document_id: UUID of document to process
        """
        db = SessionLocal()

        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document {document_id} not found")
                return

            document.status = "processing"
            document.processing_info["started_at"] = datetime.utcnow().isoformat()
            db.commit()

            logger.info(f"Parsing document {document_id}")
            file_path = self.storage.get_path(document.processing_info["file_path"])
            parser = self.parser_factory.get_parser(document.content_type)
            parsed = await parser.parse(str(file_path))

            logger.info(f"Chunking document {document_id}")
            chunks = self.chunker.chunk(parsed["content"])

            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            texts = [chunk["content"] for chunk in chunks]
            embeddings = await self.embedder.embed_batch(texts)

            logger.info(f"Storing {len(chunks)} chunks")
            for chunk_data, embedding in zip(chunks, embeddings):
                chunk = DocumentChunk(
                    document_id=document.id,
                    collection_id=document.collection_id,
                    user_id=document.user_id,
                    content=chunk_data["content"],
                    chunk_index=chunk_data["chunk_index"],
                    embedding=embedding,
                    chunk_metadata=chunk_data["metadata"]
                )
                db.add(chunk)

            document.status = "completed"
            document.processed_at = datetime.utcnow()
            document.chunk_count = len(chunks)
            document.total_tokens = sum(c["metadata"]["tokens"] for c in chunks)
            document.processing_info["completed_at"] = datetime.utcnow().isoformat()

            db.commit()
            logger.info(f"Document {document_id} processed successfully")

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}", exc_info=True)

            if document:
                document.status = "failed"
                document.error_message = str(e)
                document.processing_info["error"] = str(e)
                document.processing_info["failed_at"] = datetime.utcnow().isoformat()
                db.commit()

            raise

        finally:
            db.close()


process_document_task = celery_app.task(
    bind=True,
    base=ProcessDocumentTask,
    name="process_document",
    max_retries=3,
    default_retry_delay=60
)
