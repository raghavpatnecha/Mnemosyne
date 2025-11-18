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
from backend.storage import storage_backend
from backend.parsers import ParserFactory
from backend.chunking import ChonkieChunker
from backend.embeddings import OpenAIEmbedder
from backend.services.document_summary_service import DocumentSummaryService
from backend.services.lightrag_service import get_lightrag_manager
from backend.config import settings
import os
import tempfile

logger = logging.getLogger(__name__)


class ProcessDocumentTask(Task):
    """Celery task for processing documents"""

    def __init__(self):
        super().__init__()
        self._parser_factory = None
        self._chunker = None
        self._embedder = None
        self._summary_service = None

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

    @property
    def summary_service(self):
        if self._summary_service is None:
            self._summary_service = DocumentSummaryService()
        return self._summary_service

    async def run(self, document_id: str):
        """
        Process document: parse → chunk → embed → store

        Args:
            document_id: UUID of document to process
        """
        db = SessionLocal()
        temp_file_path = None

        try:
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                logger.error(f"Document {document_id} not found")
                return

            document.status = "processing"
            document.processing_info["started_at"] = datetime.utcnow().isoformat()
            db.commit()

            logger.info(f"Parsing document {document_id}")
            # Get local file path (downloads from S3 if needed)
            temp_file_path = storage_backend.get_local_path(
                storage_path=document.processing_info["file_path"],
                user_id=document.user_id
            )
            parser = self.parser_factory.get_parser(document.content_type)
            parsed = await parser.parse(temp_file_path)

            # Store extracted images (if any)
            extracted_images = []
            if "images" in parsed and parsed["images"]:
                logger.info(f"Saving {len(parsed['images'])} extracted images")
                for img in parsed["images"]:
                    try:
                        img_path = storage_backend.save_extracted_content(
                            content=img["data"],
                            user_id=document.user_id,
                            collection_id=document.collection_id,
                            document_id=document.id,
                            content_type="image/png",
                            filename=img["filename"]
                        )
                        extracted_images.append({
                            "path": img_path,
                            "page": img.get("page"),
                            "filename": img["filename"]
                        })
                        logger.info(f"Saved image: {img['filename']}")
                    except Exception as e:
                        logger.warning(f"Failed to save image {img['filename']}: {e}")

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

            # Generate document-level summary and embedding for hierarchical search
            logger.info(f"Generating document summary and embedding")
            summary_result = await self.summary_service.generate_summary_and_embedding(
                content=parsed["content"],
                metadata={
                    "title": document.title,
                    "filename": document.filename
                },
                strategy="concat"  # Fast strategy, suitable for production
            )

            document.summary = summary_result["summary"]
            document.document_embedding = summary_result["embedding"]

            # Index in LightRAG if enabled (per-user, per-collection)
            if settings.LIGHTRAG_ENABLED:
                try:
                    logger.info(f"Indexing document in LightRAG for user {document.user_id}, collection {document.collection_id}")
                    lightrag_manager = get_lightrag_manager()
                    await lightrag_manager.insert_document(
                        user_id=document.user_id,
                        collection_id=document.collection_id,
                        content=parsed["content"],
                        document_id=document.id,
                        metadata={
                            "title": document.title,
                            "filename": document.filename,
                            "content_type": document.content_type
                        }
                    )
                except Exception as e:
                    logger.warning(f"LightRAG indexing failed (non-critical): {e}")

            document.status = "completed"
            document.processed_at = datetime.utcnow()
            document.chunk_count = len(chunks)
            document.total_tokens = sum(c["metadata"]["tokens"] for c in chunks)
            document.processing_info["completed_at"] = datetime.utcnow().isoformat()

            # Store extracted images metadata
            if extracted_images:
                document.processing_info["extracted_images"] = extracted_images
                logger.info(f"Stored metadata for {len(extracted_images)} extracted images")

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
            # Clean up temp file if it was downloaded from S3
            if temp_file_path:
                # Check if file is in temp directory and has our prefix
                temp_dir = tempfile.gettempdir()
                if (temp_file_path.startswith(temp_dir) and
                    "mnemosyne_s3_" in os.path.basename(temp_file_path)):
                    try:
                        if os.path.exists(temp_file_path):
                            os.unlink(temp_file_path)
                            logger.info(f"Cleaned up S3 temp file: {temp_file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to clean up temp file {temp_file_path}: {e}")

            db.close()


process_document_task = celery_app.task(
    bind=True,
    base=ProcessDocumentTask,
    name="process_document",
    max_retries=3,
    default_retry_delay=60
)
