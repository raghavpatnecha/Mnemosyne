"""
LightRAG Service - Graph-based RAG with entity extraction
Implements knowledge graph construction and dual-level retrieval
WITH PER-USER, PER-COLLECTION ISOLATION
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID

try:
    from lightrag import LightRAG, QueryParam
    from lightrag.llm.openai import openai_embed, openai_complete_if_cache
    from lightrag.kg.shared_storage import initialize_pipeline_status
    from lightrag.rerank import jina_rerank
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False
    LightRAG = None
    QueryParam = None
    jina_rerank = None
    openai_complete_if_cache = None

from backend.config import settings
from backend.storage import storage_backend

logger = logging.getLogger(__name__)


async def lightrag_llm_complete(
    prompt: str,
    system_prompt: str = None,
    history_messages: list = [],
    **kwargs
) -> str:
    """
    Custom LLM completion function for LightRAG using configured CHAT_MODEL.

    Uses settings.CHAT_MODEL instead of hardcoded gpt-4o-mini.
    """
    if not openai_complete_if_cache:
        raise RuntimeError("LightRAG not available")

    return await openai_complete_if_cache(
        settings.CHAT_MODEL,  # Use configured model
        prompt,
        system_prompt=system_prompt,
        history_messages=history_messages,
        api_key=settings.OPENAI_API_KEY,
        **kwargs
    )


class LightRAGInstanceManager:
    """
    Manages per-user, per-collection LightRAG instances

    Features:
    - Complete user isolation (each user gets separate instances)
    - Per-collection knowledge graphs (no data mixing)
    - Automatic instance caching and reuse
    - User-scoped working directories (local or S3)
    - Resource cleanup and lifecycle management
    """

    def __init__(self):
        """Initialize instance manager"""
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

        # Cache: {(user_id, collection_id): LightRAG instance}
        self._instances: Dict[Tuple[UUID, UUID], LightRAG] = {}
        self._initialized: Dict[Tuple[UUID, UUID], bool] = {}
        # Track event loop ID to detect loop changes (Celery worker issue)
        self._event_loop_ids: Dict[Tuple[UUID, UUID], int] = {}

        logger.info("LightRAG instance manager created")

    def _get_working_dir(self, user_id: UUID, collection_id: UUID) -> str:
        """
        Get user-scoped working directory for LightRAG

        Uses storage backend to ensure proper isolation:
        - Local: ./data/lightrag/users/{user_id}/collections/{collection_id}
        - S3: (not yet supported for LightRAG, will use local for now)

        Args:
            user_id: Owner user ID
            collection_id: Collection ID

        Returns:
            str: Absolute path to working directory
        """
        # LightRAG currently requires local filesystem
        # Use storage backend to get user-scoped path
        base_path = Path(settings.LIGHTRAG_WORKING_DIR)
        working_dir = base_path / "users" / str(user_id) / "collections" / str(collection_id)

        # Create directory if it doesn't exist
        working_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"LightRAG working dir for user {user_id}, collection {collection_id}: {working_dir}")
        return str(working_dir)

    async def get_instance(
        self,
        user_id: UUID,
        collection_id: UUID
    ) -> Optional[LightRAG]:
        """
        Get or create LightRAG instance for user and collection

        Args:
            user_id: Owner user ID
            collection_id: Collection ID

        Returns:
            LightRAG instance (user-scoped and collection-scoped)
        """
        if not self.enabled:
            return None

        cache_key = (user_id, collection_id)

        # Get current event loop ID to detect loop changes
        # This is critical for Celery workers where each task may run in a different loop
        try:
            current_loop = asyncio.get_running_loop()
            current_loop_id = id(current_loop)
        except RuntimeError:
            current_loop_id = None

        # Check if we have a cached instance with the SAME event loop
        if cache_key in self._instances and self._initialized.get(cache_key, False):
            cached_loop_id = self._event_loop_ids.get(cache_key)
            if cached_loop_id == current_loop_id:
                logger.debug(f"Returning cached LightRAG instance for user {user_id}, collection {collection_id}")
                return self._instances[cache_key]
            else:
                # Event loop changed - must recreate instance to avoid PriorityQueue errors
                logger.warning(
                    f"Event loop changed for LightRAG instance (user {user_id}, collection {collection_id}). "
                    f"Old loop: {cached_loop_id}, New loop: {current_loop_id}. Recreating instance."
                )
                # Clean up old instance (don't await finalize as it's bound to old loop)
                del self._instances[cache_key]
                del self._initialized[cache_key]
                del self._event_loop_ids[cache_key]

        # Create new instance
        logger.info(f"Creating new LightRAG instance for user {user_id}, collection {collection_id}")

        try:
            working_dir = self._get_working_dir(user_id, collection_id)

            # Configure reranking if Jina API key is available
            rerank_func = None
            if settings.LIGHTRAG_RERANK_ENABLED and settings.JINA_API_KEY and jina_rerank:
                rerank_func = jina_rerank
                logger.info("LightRAG Jina reranker enabled")

            instance = LightRAG(
                working_dir=working_dir,

                # Embedding function (OpenAI compatible)
                embedding_func=openai_embed,

                # LLM function (uses settings.CHAT_MODEL)
                llm_model_func=lightrag_llm_complete,

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

                # Reranking (Jina if configured)
                rerank_model_func=rerank_func,

                # Storage backends (default: NetworkX + NanoVector)
                # TODO: Migrate to PostgreSQL storage for multi-user support
            )

            # Initialize storages
            await instance.initialize_storages()
            await initialize_pipeline_status()

            # Cache instance with event loop ID
            self._instances[cache_key] = instance
            self._initialized[cache_key] = True
            self._event_loop_ids[cache_key] = current_loop_id

            logger.info(f"LightRAG instance initialized for user {user_id}, collection {collection_id}")
            return instance

        except Exception as e:
            logger.error(f"Failed to create LightRAG instance: {e}", exc_info=True)
            return None

    async def insert_document(
        self,
        user_id: UUID,
        collection_id: UUID,
        content: str,
        document_id: UUID,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Insert document into user's collection knowledge graph

        Args:
            user_id: Owner user ID
            collection_id: Collection ID
            content: Document text content
            document_id: Unique document identifier
            metadata: Optional metadata (title, filename, etc.)

        Returns:
            Insertion status and metadata
        """
        if not self.enabled:
            return {"status": "disabled"}

        instance = await self.get_instance(user_id, collection_id)
        if not instance:
            return {"status": "error", "message": "Failed to get LightRAG instance"}

        metadata = metadata or {}
        doc_title = metadata.get("title", "Unknown")

        logger.info(f"Inserting document {document_id} into LightRAG for user {user_id}, collection {collection_id}")

        try:
            # Insert into knowledge graph (async)
            # This extracts entities, relationships, and builds the graph
            await instance.ainsert(content)

            logger.info(f"Document {document_id} inserted successfully into LightRAG")

            return {
                "status": "success",
                "document_id": str(document_id),
                "title": doc_title,
                "content_length": len(content)
            }

        except Exception as e:
            logger.error(f"Failed to insert document into LightRAG: {e}", exc_info=True)
            return {
                "status": "error",
                "message": str(e),
                "document_id": str(document_id)
            }

    async def query(
        self,
        user_id: UUID,
        collection_id: UUID,
        query: str,
        mode: str = "hybrid",
        only_need_context: bool = False
    ) -> Dict[str, Any]:
        """
        Query user's collection knowledge graph

        Args:
            user_id: Owner user ID
            collection_id: Collection ID
            query: Query text
            mode: Query mode (local/global/hybrid/naive)
            only_need_context: If False (default), LightRAG uses its LLM to generate
                               a coherent answer from the graph context. This provides
                               better entity-relationship synthesis at cost of extra LLM call.
                               If True, return raw context without LLM call.

        Returns:
            Dict with 'answer' (context text) and 'references' (source list)
        """
        if not self.enabled:
            return {"answer": "LightRAG is disabled", "references": []}

        instance = await self.get_instance(user_id, collection_id)
        if not instance:
            return {"answer": "Failed to get LightRAG instance", "references": []}

        logger.info(
            f"Querying LightRAG for user {user_id}, collection {collection_id} "
            f"with mode='{mode}', only_need_context={only_need_context}"
        )

        try:
            # Only enable reranking if Jina API key is configured
            enable_rerank = settings.LIGHTRAG_RERANK_ENABLED and bool(settings.JINA_API_KEY)
            param = QueryParam(
                mode=mode,
                enable_rerank=enable_rerank,
                include_references=True,
                only_need_context=only_need_context
            )
            result = await instance.aquery(query, param=param)

            # Handle different return types from LightRAG
            # Could be string (old versions) or QueryResult object (new versions)
            if isinstance(result, str):
                answer = result
                references = []
            elif hasattr(result, 'content'):
                # QueryResult object
                answer = result.content if result.content else ""
                # Extract references if available
                references = []
                if hasattr(result, 'reference_list') and result.reference_list:
                    references = result.reference_list
                elif hasattr(result, 'raw_data') and result.raw_data:
                    # Try to extract from raw_data
                    raw = result.raw_data
                    if isinstance(raw, dict) and 'references' in raw:
                        references = raw['references']
            else:
                # Fallback - treat as string
                answer = str(result)
                references = []

            logger.info(f"LightRAG query completed: {len(answer)} chars, {len(references)} references")
            return {"answer": answer, "references": references}

        except Exception as e:
            logger.error(f"LightRAG query failed: {e}", exc_info=True)
            return {"answer": f"Query failed: {str(e)}", "references": []}

    async def delete_collection(self, user_id: UUID, collection_id: UUID):
        """
        Delete LightRAG instance for a collection

        Args:
            user_id: Owner user ID
            collection_id: Collection ID to delete
        """
        cache_key = (user_id, collection_id)

        # Cleanup instance if cached
        if cache_key in self._instances:
            try:
                instance = self._instances[cache_key]
                await instance.finalize_storages()
                logger.info(f"Finalized LightRAG instance for user {user_id}, collection {collection_id}")
            except Exception as e:
                logger.error(f"Error finalizing LightRAG instance: {e}")

            # Remove from cache
            del self._instances[cache_key]
            if cache_key in self._initialized:
                del self._initialized[cache_key]
            if cache_key in self._event_loop_ids:
                del self._event_loop_ids[cache_key]

        # Delete working directory
        try:
            working_dir = Path(self._get_working_dir(user_id, collection_id))
            if working_dir.exists():
                import shutil
                shutil.rmtree(working_dir)
                logger.info(f"Deleted LightRAG working directory: {working_dir}")
        except Exception as e:
            logger.error(f"Error deleting LightRAG working directory: {e}")

    async def delete_user_data(self, user_id: UUID):
        """
        Delete all LightRAG instances for a user

        Args:
            user_id: User ID to delete data for
        """
        # Find all instances for this user
        user_keys = [key for key in self._instances.keys() if key[0] == user_id]

        for cache_key in user_keys:
            try:
                instance = self._instances[cache_key]
                await instance.finalize_storages()
                logger.info(f"Finalized LightRAG instance: {cache_key}")
            except Exception as e:
                logger.error(f"Error finalizing LightRAG instance {cache_key}: {e}")

            # Remove from cache
            del self._instances[cache_key]
            if cache_key in self._initialized:
                del self._initialized[cache_key]
            if cache_key in self._event_loop_ids:
                del self._event_loop_ids[cache_key]

        # Delete user's LightRAG directory
        try:
            base_path = Path(settings.LIGHTRAG_WORKING_DIR)
            user_dir = base_path / "users" / str(user_id)
            if user_dir.exists():
                import shutil
                shutil.rmtree(user_dir)
                logger.info(f"Deleted user's LightRAG directory: {user_dir}")
        except Exception as e:
            logger.error(f"Error deleting user's LightRAG directory: {e}")

    async def cleanup(self):
        """
        Cleanup all resources and close connections

        Should be called on application shutdown.
        """
        logger.info("Cleaning up all LightRAG instances...")

        for cache_key, instance in list(self._instances.items()):
            try:
                await instance.finalize_storages()
                logger.info(f"Finalized LightRAG instance: {cache_key}")
            except Exception as e:
                logger.error(f"Error finalizing LightRAG instance {cache_key}: {e}")

        self._instances.clear()
        self._initialized.clear()
        self._event_loop_ids.clear()
        logger.info("LightRAG cleanup completed")


# Global instance manager
_lightrag_manager: Optional[LightRAGInstanceManager] = None


def get_lightrag_manager() -> LightRAGInstanceManager:
    """
    Get or create LightRAG instance manager

    Returns:
        Shared LightRAG instance manager
    """
    global _lightrag_manager
    if _lightrag_manager is None:
        _lightrag_manager = LightRAGInstanceManager()
    return _lightrag_manager


async def initialize_lightrag():
    """Initialize LightRAG manager (call at startup)"""
    manager = get_lightrag_manager()
    if manager.enabled:
        logger.info("LightRAG manager initialized")


async def cleanup_lightrag():
    """Cleanup LightRAG manager (call at shutdown)"""
    global _lightrag_manager
    if _lightrag_manager is not None:
        await _lightrag_manager.cleanup()
