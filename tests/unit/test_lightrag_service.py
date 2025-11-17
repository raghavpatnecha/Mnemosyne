"""
Unit tests for LightRAG Service
Tests knowledge graph construction and retrieval
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from backend.services.lightrag_service import (
    LightRAGService,
    get_lightrag_service,
    LIGHTRAG_AVAILABLE
)


@pytest.fixture
def mock_lightrag():
    """Mock LightRAG instance"""
    with patch("backend.services.lightrag_service.LightRAG") as mock:
        mock_instance = AsyncMock()
        mock_instance.initialize_storages = AsyncMock()
        mock_instance.finalize_storages = AsyncMock()
        mock_instance.ainsert = AsyncMock()
        mock_instance.aquery = AsyncMock(return_value="Test context")
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_pipeline_status():
    """Mock pipeline status initialization"""
    with patch("backend.services.lightrag_service.initialize_pipeline_status") as mock:
        mock.return_value = AsyncMock()
        yield mock


@pytest.mark.skipif(not LIGHTRAG_AVAILABLE, reason="LightRAG not installed")
class TestLightRAGService:
    """Test LightRAG service functionality"""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_lightrag, mock_pipeline_status):
        """Test LightRAG service initialization"""
        service = LightRAGService()

        # Should not be initialized yet
        assert not service._initialized

        # Initialize
        await service.initialize()

        # Should be initialized
        assert service._initialized
        mock_lightrag.initialize_storages.assert_called_once()
        mock_pipeline_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_insert_document(self, mock_lightrag, mock_pipeline_status):
        """Test document insertion into knowledge graph"""
        service = LightRAGService()
        await service.initialize()

        # Insert test document
        doc_id = uuid4()
        result = await service.insert_document(
            content="Apple Inc. was founded by Steve Jobs in 1976.",
            document_id=doc_id,
            metadata={"title": "Apple History"}
        )

        # Verify insertion
        assert result["status"] == "indexed"
        assert result["document_id"] == str(doc_id)
        mock_lightrag.ainsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_local_mode(self, mock_lightrag, mock_pipeline_status):
        """Test local query mode (specific entities)"""
        service = LightRAGService()
        await service.initialize()

        # Query for specific entity
        result = await service.query(
            query_text="Who founded Apple?",
            mode="local",
            top_k=5
        )

        # Verify query
        assert result["status"] == "success"
        assert result["mode"] == "local"
        assert "context" in result
        mock_lightrag.aquery.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_global_mode(self, mock_lightrag, mock_pipeline_status):
        """Test global query mode (abstract themes)"""
        service = LightRAGService()
        await service.initialize()

        # Query for abstract theme
        result = await service.query(
            query_text="What are major tech companies?",
            mode="global",
            top_k=10
        )

        # Verify query
        assert result["status"] == "success"
        assert result["mode"] == "global"
        assert "context" in result

    @pytest.mark.asyncio
    async def test_query_hybrid_mode(self, mock_lightrag, mock_pipeline_status):
        """Test hybrid query mode (local + global)"""
        service = LightRAGService()
        await service.initialize()

        # Query with hybrid mode
        result = await service.query(
            query_text="Tell me about Apple and tech industry",
            mode="hybrid",
            top_k=10
        )

        # Verify query
        assert result["status"] == "success"
        assert result["mode"] == "hybrid"

        # Hybrid should use 3x top_k
        call_args = mock_lightrag.aquery.call_args
        query_param = call_args[1]["param"]
        assert query_param.top_k == 30  # 10 * 3

    @pytest.mark.asyncio
    async def test_disabled_service(self):
        """Test service behavior when disabled"""
        with patch("backend.services.lightrag_service.settings") as mock_settings:
            mock_settings.LIGHTRAG_ENABLED = False

            service = LightRAGService()

            # Should be disabled
            assert not service.enabled

            # Operations should return disabled status
            result = await service.insert_document(
                content="Test",
                document_id=uuid4()
            )
            assert result["status"] == "disabled"

            result = await service.query("Test query")
            assert result["status"] == "disabled"

    @pytest.mark.asyncio
    async def test_cleanup(self, mock_lightrag, mock_pipeline_status):
        """Test service cleanup"""
        service = LightRAGService()
        await service.initialize()

        # Cleanup
        await service.cleanup()

        # Should finalize storages
        mock_lightrag.finalize_storages.assert_called_once()
        assert not service._initialized

    @pytest.mark.asyncio
    async def test_singleton_pattern(self):
        """Test that get_lightrag_service returns singleton"""
        service1 = get_lightrag_service()
        service2 = get_lightrag_service()

        # Should be same instance
        assert service1 is service2

    @pytest.mark.asyncio
    async def test_error_handling_insert(self, mock_lightrag, mock_pipeline_status):
        """Test error handling during document insertion"""
        service = LightRAGService()
        await service.initialize()

        # Mock insertion error
        mock_lightrag.ainsert.side_effect = Exception("Insert failed")

        # Should handle error gracefully
        result = await service.insert_document(
            content="Test",
            document_id=uuid4()
        )

        assert result["status"] == "failed"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_error_handling_query(self, mock_lightrag, mock_pipeline_status):
        """Test error handling during query"""
        service = LightRAGService()
        await service.initialize()

        # Mock query error
        mock_lightrag.aquery.side_effect = Exception("Query failed")

        # Should handle error gracefully
        result = await service.query("Test query")

        assert result["status"] == "failed"
        assert "error" in result
        assert result["context"] == ""


@pytest.mark.skipif(LIGHTRAG_AVAILABLE, reason="Test for when LightRAG is not available")
class TestLightRAGServiceUnavailable:
    """Test service behavior when LightRAG is not installed"""

    def test_service_disabled_when_unavailable(self):
        """Service should be disabled if LightRAG not installed"""
        service = LightRAGService()
        assert not service.enabled
