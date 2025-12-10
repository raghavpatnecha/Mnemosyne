"""
Unit tests for LightRAG Service
Tests multi-tenant knowledge graph construction and retrieval
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from uuid import uuid4

from backend.services.lightrag_service import (
    LightRAGInstanceManager,
    get_lightrag_manager,
    LIGHTRAG_AVAILABLE
)


@pytest.fixture
def mock_lightrag_class():
    """Mock LightRAG class"""
    with patch("backend.services.lightrag_service.LightRAG") as mock_class:
        mock_instance = AsyncMock()
        mock_instance.initialize_storages = AsyncMock()
        mock_instance.finalize_storages = AsyncMock()
        mock_instance.ainsert = AsyncMock()
        mock_instance.aquery = AsyncMock(return_value="Test context from knowledge graph")
        mock_class.return_value = mock_instance
        yield mock_class, mock_instance


@pytest.fixture
def mock_pipeline_status():
    """Mock pipeline status initialization"""
    with patch("backend.services.lightrag_service.initialize_pipeline_status") as mock:
        mock.return_value = AsyncMock()
        yield mock


@pytest.fixture
def mock_settings():
    """Mock settings for LightRAG"""
    with patch("backend.services.lightrag_service.settings") as mock:
        mock.LIGHTRAG_ENABLED = True
        mock.LIGHTRAG_WORKING_DIR = "./data/lightrag"
        mock.LIGHTRAG_CHUNK_SIZE = 512
        mock.LIGHTRAG_CHUNK_OVERLAP = 50
        mock.LIGHTRAG_TOP_K = 5
        mock.LIGHTRAG_CHUNK_TOP_K = 3
        mock.LIGHTRAG_MAX_ENTITY_TOKENS = 1500
        mock.LIGHTRAG_MAX_RELATION_TOKENS = 1500
        mock.LIGHTRAG_MAX_TOKENS = 8000
        mock.LIGHTRAG_RERANK_ENABLED = False
        mock.JINA_API_KEY = None
        yield mock


@pytest.mark.skipif(not LIGHTRAG_AVAILABLE, reason="LightRAG not installed")
class TestLightRAGInstanceManager:
    """Test LightRAG instance manager functionality"""

    def test_init_disabled(self):
        """Test manager initialization when disabled"""
        with patch("backend.services.lightrag_service.settings") as mock_settings:
            mock_settings.LIGHTRAG_ENABLED = False
            manager = LightRAGInstanceManager()
            assert not manager.enabled

    def test_init_enabled(self, mock_settings):
        """Test manager initialization when enabled"""
        manager = LightRAGInstanceManager()
        assert manager.enabled
        assert manager._instances == {}
        assert manager._initialized == {}

    @pytest.mark.asyncio
    async def test_get_instance_creates_new(
        self, mock_lightrag_class, mock_pipeline_status, mock_settings
    ):
        """Test get_instance creates new LightRAG instance"""
        mock_class, mock_instance = mock_lightrag_class

        manager = LightRAGInstanceManager()
        user_id = uuid4()
        collection_id = uuid4()

        instance = await manager.get_instance(user_id, collection_id)

        assert instance is not None
        mock_class.assert_called_once()
        mock_instance.initialize_storages.assert_called_once()
        mock_pipeline_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_instance_caches(
        self, mock_lightrag_class, mock_pipeline_status, mock_settings
    ):
        """Test get_instance returns cached instance"""
        mock_class, mock_instance = mock_lightrag_class

        manager = LightRAGInstanceManager()
        user_id = uuid4()
        collection_id = uuid4()

        # First call creates instance
        instance1 = await manager.get_instance(user_id, collection_id)
        # Second call returns cached
        instance2 = await manager.get_instance(user_id, collection_id)

        assert instance1 is instance2
        # Should only be called once due to caching
        assert mock_class.call_count == 1

    @pytest.mark.asyncio
    async def test_get_instance_isolation(
        self, mock_lightrag_class, mock_pipeline_status, mock_settings
    ):
        """Test different users/collections get different instances"""
        mock_class, mock_instance = mock_lightrag_class

        manager = LightRAGInstanceManager()
        user1_id = uuid4()
        user2_id = uuid4()
        collection_id = uuid4()

        # Different users get different instances
        await manager.get_instance(user1_id, collection_id)
        await manager.get_instance(user2_id, collection_id)

        # Should create two separate instances
        assert mock_class.call_count == 2

    @pytest.mark.asyncio
    async def test_get_instance_disabled(self, mock_settings):
        """Test get_instance returns None when disabled"""
        mock_settings.LIGHTRAG_ENABLED = False
        manager = LightRAGInstanceManager()

        instance = await manager.get_instance(uuid4(), uuid4())
        assert instance is None

    @pytest.mark.asyncio
    async def test_insert_document(
        self, mock_lightrag_class, mock_pipeline_status, mock_settings
    ):
        """Test document insertion into knowledge graph"""
        mock_class, mock_instance = mock_lightrag_class

        manager = LightRAGInstanceManager()
        user_id = uuid4()
        collection_id = uuid4()
        doc_id = uuid4()

        result = await manager.insert_document(
            user_id=user_id,
            collection_id=collection_id,
            content="Apple Inc. was founded by Steve Jobs in 1976.",
            document_id=doc_id,
            metadata={"title": "Apple History"}
        )

        assert result["status"] == "success"
        assert result["document_id"] == str(doc_id)
        mock_instance.ainsert.assert_called_once_with(
            "Apple Inc. was founded by Steve Jobs in 1976."
        )

    @pytest.mark.asyncio
    async def test_insert_document_disabled(self, mock_settings):
        """Test insert returns disabled status when LightRAG disabled"""
        mock_settings.LIGHTRAG_ENABLED = False
        manager = LightRAGInstanceManager()

        result = await manager.insert_document(
            user_id=uuid4(),
            collection_id=uuid4(),
            content="Test content",
            document_id=uuid4()
        )

        assert result["status"] == "disabled"

    @pytest.mark.asyncio
    async def test_query(
        self, mock_lightrag_class, mock_pipeline_status, mock_settings
    ):
        """Test knowledge graph query"""
        mock_class, mock_instance = mock_lightrag_class
        mock_instance.aquery = AsyncMock(return_value="Steve Jobs founded Apple in 1976")

        manager = LightRAGInstanceManager()
        user_id = uuid4()
        collection_id = uuid4()

        # Insert first to create instance
        await manager.insert_document(
            user_id=user_id,
            collection_id=collection_id,
            content="Test content",
            document_id=uuid4()
        )

        result = await manager.query(
            user_id=user_id,
            collection_id=collection_id,
            query="Who founded Apple?",
            mode="hybrid"
        )

        assert "answer" in result
        mock_instance.aquery.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_disabled(self, mock_settings):
        """Test query returns disabled message when LightRAG disabled"""
        mock_settings.LIGHTRAG_ENABLED = False
        manager = LightRAGInstanceManager()

        result = await manager.query(
            user_id=uuid4(),
            collection_id=uuid4(),
            query="Test query"
        )

        assert "disabled" in result["answer"].lower()

    @pytest.mark.asyncio
    async def test_query_modes(
        self, mock_lightrag_class, mock_pipeline_status, mock_settings
    ):
        """Test different query modes"""
        mock_class, mock_instance = mock_lightrag_class

        manager = LightRAGInstanceManager()
        user_id = uuid4()
        collection_id = uuid4()

        for mode in ["local", "global", "hybrid", "naive"]:
            await manager.query(
                user_id=user_id,
                collection_id=collection_id,
                query="Test query",
                mode=mode
            )

    def test_get_working_dir(self, mock_settings):
        """Test working directory path generation"""
        manager = LightRAGInstanceManager()
        user_id = uuid4()
        collection_id = uuid4()

        working_dir = manager._get_working_dir(user_id, collection_id)

        assert str(user_id) in working_dir
        assert str(collection_id) in working_dir
        assert "users" in working_dir
        assert "collections" in working_dir


class TestLightRAGNotAvailable:
    """Test behavior when LightRAG is not available"""

    def test_manager_disabled_when_not_available(self):
        """Test manager is disabled when LightRAG not installed"""
        with patch("backend.services.lightrag_service.LIGHTRAG_AVAILABLE", False):
            # Re-import to get fresh class with patched constant
            manager = LightRAGInstanceManager()
            assert not manager.enabled


class TestGetLightRAGManager:
    """Test singleton manager accessor"""

    def test_get_manager_returns_instance(self, mock_settings):
        """Test get_lightrag_manager returns manager instance"""
        manager = get_lightrag_manager()
        assert isinstance(manager, LightRAGInstanceManager)

    def test_get_manager_returns_same_instance(self, mock_settings):
        """Test get_lightrag_manager returns same singleton"""
        manager1 = get_lightrag_manager()
        manager2 = get_lightrag_manager()
        assert manager1 is manager2
