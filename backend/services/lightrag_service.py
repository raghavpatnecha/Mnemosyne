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
    from lightrag.llm.openai import gpt_4o_mini_complete, openai_embed
    from lightrag.kg.shared_storage import initialize_pipeline_status
    LIGHTRAG_AVAILABLE = True
except ImportError:
    LIGHTRAG_AVAILABLE = False
    LightRAG = None
    QueryParam = None

from backend.config import settings
from backend.storage import storage_backend

logger = logging.getLogger(__name__)


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

        # Return cached instance if available
        if cache_key in self._instances and self._initialized.get(cache_key, False):
            logger.debug(f"Returning cached LightRAG instance for user {user_id}, collection {collection_id}")
            return self._instances[cache_key]

        # Create new instance
        logger.info(f"Creating new LightRAG instance for user {user_id}, collection {collection_id}")

        try:
            working_dir = self._get_working_dir(user_id, collection_id)

            instance = LightRAG(
                working_dir=working_dir,

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
                # TODO: Migrate to PostgreSQL storage for multi-user support
            )

            # Initialize storages
            await instance.initialize_storages()
            await initialize_pipeline_status()

            # Cache instance
            self._instances[cache_key] = instance
            self._initialized[cache_key] = True

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
            await instance.insert(content)

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
        mode: str = "hybrid"
    ) -> str:
        """
        Query user's collection knowledge graph

        Args:
            user_id: Owner user ID
            collection_id: Collection ID
            query: Query text
            mode: Query mode (local/global/hybrid/naive)

        Returns:
            Query response
        """
        if not self.enabled:
            return "LightRAG is disabled"

        instance = await self.get_instance(user_id, collection_id)
        if not instance:
            return "Failed to get LightRAG instance"

        logger.info(f"Querying LightRAG for user {user_id}, collection {collection_id} with mode '{mode}'")

        try:
            param = QueryParam(mode=mode)
            result = await instance.query(query, param=param)

            logger.info(f"LightRAG query completed successfully")
            return result

        except Exception as e:
            logger.error(f"LightRAG query failed: {e}", exc_info=True)
            return f"Query failed: {str(e)}"

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
