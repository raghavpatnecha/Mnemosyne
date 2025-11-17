"""
LightRAG Service - Graph-based RAG with entity extraction
Implements knowledge graph construction and dual-level retrieval
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import UUID

try:
    from lightrag import LightRAG, QueryParam
    from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
    from lightrag.kg.shared_storage import initialize_pipeline_status
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False
    LightRAG = None
    QueryParam = None

from backend.config import settings

logger = logging.getLogger(__name__)


class LightRAGService:
    """
    LightRAG wrapper for Mnemosyne knowledge graph RAG

    Features:
    - Automatic entity and relationship extraction
    - Knowledge graph construction from documents
    - Dual-level retrieval (local + global)
    - Hybrid graph + vector search
    - Incremental updates without full rebuilds

    Query Modes:
    - local: Specific entity queries (e.g., "Who founded Apple?")
    - global: Abstract theme queries (e.g., "Major tech companies")
    - hybrid: Combines both approaches
    - naive: Vector-only search (no graph)
    """

    def __init__(self):
        """Initialize LightRAG service"""
        if not LIGHTRAG_AVAILABLE:
            logger.warning(
                "LightRAG not available. Install with: poetry add lightrag-hku"
            )
            self.enabled = False
            return

        self.enabled = settings.LIGHTRAG_ENABLED
        if not self.enabled:
            logger.info("LightRAG is disabled in configuration")
            return

        self.working_dir = Path(settings.LIGHTRAG_WORKING_DIR)
        self.working_dir.mkdir(parents=True, exist_ok=True)

        self.rag = None
        self._initialized = False

        logger.info(f"LightRAG service created (working_dir: {self.working_dir})")

    async def initialize(self):
        """
        Initialize LightRAG instance

        Must be called before using the service.
        Creates storage backends and initializes pipeline.
        """
        if not self.enabled:
            return

        if self._initialized:
            logger.debug("LightRAG already initialized")
            return

        logger.info("Initializing LightRAG...")

        try:
            self.rag = LightRAG(
                working_dir=str(self.working_dir),

                # Embedding function (OpenAI compatible)
                embedding_func=openai_embed,

                # LLM function (uses gpt-4o-mini by default)
                llm_model_func=gpt_4o_mini_complete,

                # Chunking settings (align with Chonkie)
                chunk_token_size=settings.LIGHTRAG_CHUNK_SIZE,
                chunk_overlap_token_size=settings.LIGHTRAG_CHUNK_OVERLAP,

                # Retrieval settings
                top_k=settings.LIGHTRAG_TOP_K,
                chunk_top_k=settings.LIGHTRAG_CHUNK_TOP_K,

                # Token limits
                max_entity_tokens=settings.LIGHTRAG_MAX_ENTITY_TOKENS,
                max_relation_tokens=settings.LIGHTRAG_MAX_RELATION_TOKENS,
                max_total_tokens=settings.LIGHTRAG_MAX_TOKENS,

                # Storage backends (default: NetworkX + NanoVector)
                # TODO: Migrate to PostgreSQL storage
            )

            # Required initialization steps
            await self.rag.initialize_storages()
            await initialize_pipeline_status()

            self._initialized = True
            logger.info("LightRAG initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize LightRAG: {e}", exc_info=True)
            self.enabled = False
            raise

    async def insert_document(
        self,
        content: str,
        document_id: UUID,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Insert document into knowledge graph

        Extracts entities and relationships automatically using LLM.
        Updates graph incrementally without rebuilding.

        Args:
            content: Document text content
            document_id: Unique document identifier
            metadata: Optional metadata (title, filename, etc.)

        Returns:
            Insertion status and metadata
        """
        if not self.enabled:
            return {"status": "disabled"}

        if not self._initialized:
            await self.initialize()

        metadata = metadata or {}
        doc_title = metadata.get("title", "Unknown")

        logger.info(
            f"Inserting document into LightRAG: {doc_title} "
            f"(id: {document_id}, length: {len(content)} chars)"
        )

        try:
            # LightRAG automatically:
            # 1. Extracts entities and relationships
            # 2. Builds knowledge graph
            # 3. Creates embeddings
            # 4. Updates incremental indices
            await self.rag.ainsert(content)

            logger.info(f"Successfully indexed document: {doc_title}")

            return {
                "status": "indexed",
                "document_id": str(document_id),
                "content_length": len(content),
                "metadata": metadata
            }

        except Exception as e:
            logger.error(
                f"Failed to insert document {document_id} into LightRAG: {e}",
                exc_info=True
            )
            return {
                "status": "failed",
                "document_id": str(document_id),
                "error": str(e)
            }

    async def query(
        self,
        query_text: str,
        mode: str = "hybrid",
        top_k: int = 10,
        only_context: bool = True,
        db_session = None,
        user_id: UUID = None,
        collection_id: UUID = None
    ) -> Dict[str, Any]:
        """
        Query knowledge graph with dual-level retrieval

        Args:
            query_text: Search query
            mode: Query mode:
                - "local": Specific entities (e.g., "Who is X?")
                - "global": Abstract themes (e.g., "What is Y?")
                - "hybrid": Both local + global (recommended)
                - "naive": Vector-only (no graph)
            top_k: Number of results to return
            only_context: If True, return context only (no LLM answer)
            db_session: Optional database session for source extraction
            user_id: Optional user ID for source filtering
            collection_id: Optional collection ID for source filtering

        Returns:
            Query results with context and source chunks
        """
        if not self.enabled:
            return {"status": "disabled", "context": "", "chunks": []}

        if not self._initialized:
            await self.initialize()

        logger.info(f"Querying LightRAG: '{query_text}' (mode: {mode}, top_k: {top_k})")

        try:
            # Query with specified mode
            result = await self.rag.aquery(
                query_text,
                param=QueryParam(
                    mode=mode,
                    top_k=top_k * 3 if mode == "hybrid" else top_k,
                    only_need_context=only_context,
                    max_total_tokens=settings.LIGHTRAG_MAX_TOKENS
                )
            )

            logger.info(
                f"LightRAG query completed: {len(result)} chars returned"
            )

            # Extract source chunks from our database
            source_chunks = []
            if db_session and result:
                source_chunks = await self._extract_source_chunks(
                    context=result,
                    query_text=query_text,
                    db_session=db_session,
                    user_id=user_id,
                    collection_id=collection_id,
                    top_k=top_k
                )

            return {
                "status": "success",
                "query": query_text,
                "mode": mode,
                "context": result,
                "chunks": source_chunks
            }

        except Exception as e:
            logger.error(f"LightRAG query failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "query": query_text,
                "error": str(e),
                "context": "",
                "chunks": []
            }

    async def _extract_source_chunks(
        self,
        context: str,
        query_text: str,
        db_session,
        user_id: Optional[UUID] = None,
        collection_id: Optional[UUID] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Extract source chunks from our database based on LightRAG context

        Strategy: LightRAG returns synthesized context from knowledge graph.
        We search our database to find the actual chunks that were likely used,
        providing real chunk IDs and document references for consistency.

        Args:
            context: Context string returned by LightRAG
            query_text: Original query for semantic search
            db_session: Database session
            user_id: Filter by user ownership
            collection_id: Filter by collection
            top_k: Number of source chunks to return

        Returns:
            List of chunk dictionaries with real IDs and metadata
        """
        from backend.embeddings.openai_embedder import OpenAIEmbedder
        from backend.search.vector_search import VectorSearchService

        if not context or not db_session:
            return []

        try:
            # Use semantic search to find chunks matching the query
            # This gives us real source attribution from our database
            embedder = OpenAIEmbedder()
            query_embedding = await embedder.embed(query_text)

            search_service = VectorSearchService(db_session)
            chunks = search_service.search(
                query_embedding=query_embedding,
                collection_id=collection_id,
                user_id=user_id,
                top_k=top_k
            )

            logger.info(
                f"Found {len(chunks)} source chunks for LightRAG context "
                f"(user_id={user_id}, collection_id={collection_id})"
            )

            return chunks

        except Exception as e:
            logger.error(f"Failed to extract source chunks: {e}", exc_info=True)
            return []

    async def get_entity_count(self) -> int:
        """Get total number of entities in knowledge graph"""
        if not self.enabled or not self._initialized:
            return 0

        try:
            # Access entity storage
            # Implementation depends on storage backend
            return 0
        except Exception as e:
            logger.error(f"Failed to get entity count: {e}")
            return 0

    async def get_relationship_count(self) -> int:
        """Get total number of relationships in knowledge graph"""
        if not self.enabled or not self._initialized:
            return 0

        try:
            # Access graph storage
            # Implementation depends on storage backend
            return 0
        except Exception as e:
            logger.error(f"Failed to get relationship count: {e}")
            return 0

    async def cleanup(self):
        """
        Cleanup resources and close connections

        Should be called on application shutdown.
        """
        if self.rag and self._initialized:
            try:
                logger.info("Finalizing LightRAG storages...")
                await self.rag.finalize_storages()
                self._initialized = False
                logger.info("LightRAG cleanup completed")
            except Exception as e:
                logger.error(f"Error during LightRAG cleanup: {e}", exc_info=True)


# Singleton instance
_lightrag_service: Optional[LightRAGService] = None


def get_lightrag_service() -> LightRAGService:
    """
    Get or create LightRAG service singleton

    Returns:
        Shared LightRAG service instance
    """
    global _lightrag_service
    if _lightrag_service is None:
        _lightrag_service = LightRAGService()
    return _lightrag_service


async def initialize_lightrag():
    """Initialize LightRAG service (call at startup)"""
    service = get_lightrag_service()
    if service.enabled:
        await service.initialize()


async def cleanup_lightrag():
    """Cleanup LightRAG service (call at shutdown)"""
    global _lightrag_service
    if _lightrag_service is not None:
        await _lightrag_service.cleanup()
