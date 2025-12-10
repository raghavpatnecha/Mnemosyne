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
from sqlalchemy.orm.attributes import flag_modified

from backend.worker import celery_app
from backend.database import SessionLocal
from backend.models.document import Document
from backend.models.chunk import DocumentChunk, normalize_for_search
from backend.storage import storage_backend
from backend.parsers import ParserFactory
from backend.parsers.content_cleaner import clean_content_for_rag
from backend.chunking import ChonkieChunker
from backend.embeddings import OpenAIEmbedder
from backend.services.document_summary_service import DocumentSummaryService
from backend.services.lightrag_service import get_lightrag_manager
from backend.processors import ProcessorFactory
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

    async def process(self, document_id: str):
        """
        Process document: parse → chunk → embed → store

        Args:
            document_id: UUID of document to process
        """
        db = SessionLocal()
        temp_file_path = None

        try:
            # Use row-level locking to prevent concurrent processing (Issue #2 fix)
            document = db.query(Document).filter(
                Document.id == document_id
            ).with_for_update().first()

            if not document:
                logger.error(f"Document {document_id} not found")
                return

            # Validate state transition (only pending documents can be processed)
            if document.status != "pending":
                logger.warning(
                    f"Document {document_id} already has status '{document.status}', "
                    "skipping processing to prevent race condition"
                )
                return

            # Atomically update status to processing
            document.status = "processing"
            document.processing_info["started_at"] = datetime.utcnow().isoformat()
            flag_modified(document, 'processing_info')  # Force SQLAlchemy to detect JSON mutation
            db.commit()

            logger.info(f"Parsing document {document_id}")
            # Get local file path (downloads from S3 if needed)
            temp_file_path = storage_backend.get_local_path(
                storage_path=document.processing_info["file_path"],
                user_id=document.user_id
            )
            parser = self.parser_factory.get_parser(document.content_type)

            # Track which parser is being used
            parser_name = parser.__class__.__name__
            document.processing_info["parser_used"] = parser_name
            flag_modified(document, 'processing_info')  # Force SQLAlchemy to detect JSON mutation
            db.commit()
            logger.info(f"Using parser: {parser_name} for {document.filename}")

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

            # Describe extracted images with GPT-4o Vision for RAG retrieval
            # This makes charts, graphs, diagrams searchable via semantic search
            if parsed.get("images") and settings.FIGURE_DESCRIPTION_ENABLED:
                try:
                    from backend.parsers.figure_parser import FigureParser

                    # Filter out tiny images (likely icons/decorations)
                    significant_images = [
                        img for img in parsed["images"]
                        if len(img.get("data", b"")) >= settings.FIGURE_MIN_SIZE_BYTES
                    ]

                    if significant_images:
                        logger.info(
                            f"Describing {len(significant_images)} figures with GPT-4o Vision"
                        )

                        figure_parser = FigureParser(
                            model=settings.FIGURE_DESCRIPTION_MODEL,
                            max_concurrent=settings.FIGURE_MAX_CONCURRENT
                        )

                        # Prepare figures for description
                        figures = [{
                            "data": img["data"],
                            "page": img.get("page"),
                            "index": idx,
                            "format": img.get("format", "png"),
                            "filename": img["filename"]
                        } for idx, img in enumerate(significant_images)]

                        # Get semantic descriptions with document context
                        figure_results = await figure_parser.process_figures(
                            figures,
                            context=parsed["content"][:1500]  # Provide document context
                        )

                        # Format descriptions and append to content
                        if figure_results:
                            figure_markdown = FigureParser.format_figures_as_markdown(
                                figure_results
                            )
                            parsed["content"] += (
                                "\n\n## Figures and Visualizations\n\n" + figure_markdown
                            )
                            logger.info(
                                f"Added descriptions for {len(figure_results)} figures "
                                f"({len(figure_markdown)} chars)"
                            )

                            # Store figure descriptions in processing info
                            document.processing_info["figure_descriptions"] = [
                                r.to_dict() for r in figure_results
                            ]
                except Exception as e:
                    logger.warning(f"Figure description failed (non-critical): {e}")

            # Domain processor detection and processing
            # Extracts domain-specific structure (legal hierarchy, academic sections, Q&A pairs, etc.)
            processor_result = None
            if settings.DOMAIN_PROCESSORS_ENABLED:
                try:
                    processor = await ProcessorFactory.detect_and_get_processor(
                        content=parsed["content"],
                        metadata=document.metadata_ or {},
                        use_llm=settings.DOMAIN_DETECTION_USE_LLM
                    )

                    if processor:
                        logger.info(f"Using domain processor: {processor.name}")
                        processor_result = await processor.process(
                            content=parsed["content"],
                            metadata=document.metadata_ or {},
                            filename=document.filename
                        )

                        # Store processor metadata in document
                        document.processing_info = document.processing_info or {}
                        document.processing_info["domain_processor"] = processor.name
                        document.processing_info["domain_metadata"] = processor_result.document_metadata
                        document.processing_info["processor_confidence"] = processor_result.confidence

                        # Use processed content if modified by processor
                        if processor_result.content != parsed["content"]:
                            parsed["content"] = processor_result.content
                            logger.info(f"Content transformed by {processor.name} processor")
                except Exception as e:
                    logger.warning(f"Domain processing failed (non-critical): {e}")

            # Clean content before chunking (removes table artifacts, HTML comments, etc.)
            # This is critical for RAG quality - garbage in = garbage out
            logger.info(f"Cleaning parsed content for RAG optimization")
            cleaned_content = clean_content_for_rag(parsed["content"])

            logger.info(f"Chunking document {document_id}")
            chunks = self.chunker.chunk(cleaned_content)

            logger.info(f"Generating embeddings for {len(chunks)} chunks")
            texts = [chunk["content"] for chunk in chunks]
            embeddings = await self.embedder.embed_batch(texts)

            logger.info(f"Storing {len(chunks)} chunks")
            for chunk_data, embedding in zip(chunks, embeddings):
                # Normalize content at index time for full-text search
                # This transforms "Myndro/Moodahead" → "Myndro Moodahead"
                raw_content = chunk_data["content"]
                search_content = normalize_for_search(raw_content)

                # Build chunk metadata including domain annotations
                chunk_metadata = chunk_data.get("metadata", {})

                # Add domain-specific annotations to chunk metadata if available
                if processor_result and processor_result.chunk_annotations:
                    chunk_idx = chunk_data["chunk_index"]
                    # Find matching annotation for this chunk (if any)
                    for annotation in processor_result.chunk_annotations:
                        if annotation.get("index") == chunk_idx:
                            chunk_metadata["domain_annotation"] = annotation
                            break

                # Build base metadata with optional domain type
                base_metadata = {
                    "source": document.filename,
                    "title": document.title,
                    "content_type": document.content_type,
                }

                # Add document type if domain processor was used
                if processor_result:
                    base_metadata["document_type"] = processor_result.document_metadata.get(
                        "document_type", "general"
                    )

                chunk = DocumentChunk(
                    document_id=document.id,
                    collection_id=document.collection_id,
                    user_id=document.user_id,
                    content=raw_content,  # Original content for display
                    search_content=search_content,  # Normalized for FTS
                    chunk_index=chunk_data["chunk_index"],
                    embedding=embedding,
                    metadata_=base_metadata,
                    chunk_metadata=chunk_metadata
                )
                db.add(chunk)

            # Generate document-level summary and embedding for hierarchical search
            # Use cleaned content for better summary quality
            logger.info(f"Generating document summary and embedding")
            summary_result = await self.summary_service.generate_summary_and_embedding(
                content=cleaned_content,  # Use cleaned content
                metadata={
                    "title": document.title,
                    "filename": document.filename
                },
                strategy="concat"  # Fast strategy, suitable for production
            )

            document.summary = summary_result["summary"]
            document.document_embedding = summary_result["embedding"]

            # Index in LightRAG if enabled (per-user, per-collection)
            # Use cleaned content for better graph quality
            if settings.LIGHTRAG_ENABLED:
                try:
                    logger.info(f"Indexing document in LightRAG for user {document.user_id}, collection {document.collection_id}")
                    lightrag_manager = get_lightrag_manager()
                    await lightrag_manager.insert_document(
                        user_id=document.user_id,
                        collection_id=document.collection_id,
                        content=cleaned_content,  # Use cleaned content
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

            flag_modified(document, 'processing_info')  # Force SQLAlchemy to detect JSON mutation
            db.commit()
            logger.info(f"Document {document_id} processed successfully")

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {e}", exc_info=True)

            if document:
                try:
                    document.status = "failed"
                    document.error_message = str(e)
                    document.processing_info["error"] = str(e)
                    document.processing_info["failed_at"] = datetime.utcnow().isoformat()
                    flag_modified(document, 'processing_info')  # Force SQLAlchemy to detect JSON mutation
                    db.commit()
                except Exception as commit_error:
                    logger.error(f"Failed to update document status to failed: {commit_error}")
                    db.rollback()

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


@celery_app.task(
    bind=True,
    base=ProcessDocumentTask,
    name="process_document",
    max_retries=3,
    default_retry_delay=60
)
def process_document_task(self, document_id: str):
    """
    Celery task wrapper for processing documents

    Args:
        document_id: UUID of document to process
    """
    return asyncio.run(self.process(document_id))
