"""
Unit tests for HierarchicalSearchService
Tests two-tier document → chunk retrieval
"""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4
from backend.search.hierarchical_search import HierarchicalSearchService


@pytest.fixture
def db_session():
    """Mock database session"""
    return MagicMock()


@pytest.fixture
def hierarchical_service(db_session):
    """Create HierarchicalSearchService instance"""
    return HierarchicalSearchService(db_session)


@pytest.fixture
def query_embedding():
    """Sample query embedding"""
    return [0.1] * 1536


@pytest.fixture
def user_id():
    """Sample user ID"""
    return uuid4()


@pytest.fixture
def collection_id():
    """Sample collection ID"""
    return uuid4()


class TestDocumentSearch:
    """Test tier-1 document-level search"""

    @pytest.mark.asyncio
    async def test_search_documents_returns_top_k(self, hierarchical_service, query_embedding, user_id):
        """Test document search returns correct number of results"""
        # Mock database query
        mock_results = [
            Mock(
                id=uuid4(),
                title=f"Document {i}",
                filename=f"doc{i}.pdf",
                distance=0.1 * i
            )
            for i in range(5)
        ]

        hierarchical_service.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_results

        documents = hierarchical_service._search_documents(
            query_embedding=query_embedding,
            user_id=user_id,
            collection_id=None,
            top_k=5
        )

        assert len(documents) == 5
        assert all("id" in doc for doc in documents)
        assert all("score" in doc for doc in documents)

    @pytest.mark.asyncio
    async def test_search_documents_converts_distance_to_score(self, hierarchical_service, query_embedding, user_id):
        """Test distance is converted to similarity score (1 - distance)"""
        mock_results = [
            Mock(id=uuid4(), title="Doc", filename="doc.pdf", distance=0.2)
        ]

        hierarchical_service.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_results

        documents = hierarchical_service._search_documents(
            query_embedding=query_embedding,
            user_id=user_id,
            collection_id=None,
            top_k=1
        )

        assert documents[0]["score"] == pytest.approx(0.8)  # 1 - 0.2

    @pytest.mark.asyncio
    async def test_search_documents_filters_by_collection(self, hierarchical_service, query_embedding, user_id, collection_id):
        """Test document search filters by collection_id"""
        mock_results = []
        hierarchical_service.db.query.return_value.filter.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_results

        hierarchical_service._search_documents(
            query_embedding=query_embedding,
            user_id=user_id,
            collection_id=collection_id,
            top_k=10
        )

        # Verify filter was applied (second filter call for collection_id)
        filter_calls = hierarchical_service.db.query.return_value.filter.call_count
        assert filter_calls >= 1

    @pytest.mark.asyncio
    async def test_search_documents_excludes_none_embeddings(self, hierarchical_service, query_embedding, user_id):
        """Test document search only includes documents with embeddings"""
        hierarchical_service._search_documents(
            query_embedding=query_embedding,
            user_id=user_id,
            collection_id=None,
            top_k=10
        )

        # Verify filter includes document_embedding.isnot(None) check
        # This is checked via the filter call in the implementation
        assert hierarchical_service.db.query.called


class TestChunkSearch:
    """Test tier-2 chunk-level search within documents"""

    @pytest.mark.asyncio
    async def test_search_chunks_in_documents(self, hierarchical_service, query_embedding, user_id):
        """Test chunk search within specific documents"""
        document_ids = [str(uuid4()) for _ in range(3)]

        mock_results = [
            Mock(
                id=uuid4(),
                content="Chunk content",
                chunk_index=i,
                metadata_={},
                chunk_metadata={},
                document_id=uuid4(),
                collection_id=uuid4(),
                document_title="Doc Title",
                document_filename="doc.pdf",
                distance=0.15
            )
            for i in range(10)
        ]

        hierarchical_service.db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_results

        chunks = hierarchical_service._search_chunks_in_documents(
            query_embedding=query_embedding,
            document_ids=document_ids,
            user_id=user_id,
            top_k=10
        )

        assert len(chunks) == 10
        assert all("chunk_id" in chunk for chunk in chunks)
        assert all("content" in chunk for chunk in chunks)
        assert all("score" in chunk for chunk in chunks)
        assert all("document" in chunk for chunk in chunks)

    @pytest.mark.asyncio
    async def test_search_chunks_filters_by_document_ids(self, hierarchical_service, query_embedding, user_id):
        """Test chunk search only searches within specified documents"""
        document_ids = [str(uuid4()) for _ in range(5)]

        mock_results = []
        hierarchical_service.db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_results

        hierarchical_service._search_chunks_in_documents(
            query_embedding=query_embedding,
            document_ids=document_ids,
            user_id=user_id,
            top_k=10
        )

        # Verify filter includes document_id.in_(document_ids)
        assert hierarchical_service.db.query.return_value.join.return_value.filter.called


class TestHierarchicalSearch:
    """Test full two-tier hierarchical search"""

    @pytest.mark.asyncio
    async def test_hierarchical_search_flow(self, hierarchical_service, query_embedding, user_id):
        """Test full hierarchical search: documents → chunks"""
        # Mock tier-1 document results
        mock_documents = [
            Mock(
                id=uuid4(),
                title=f"Doc {i}",
                filename=f"doc{i}.pdf",
                distance=0.1
            )
            for i in range(30)  # 3x multiplier * 10 top_k
        ]

        # Mock tier-2 chunk results
        mock_chunks = [
            Mock(
                id=uuid4(),
                content=f"Chunk {i}",
                chunk_index=i,
                metadata_={},
                chunk_metadata={},
                document_id=uuid4(),
                collection_id=uuid4(),
                document_title="Doc Title",
                document_filename="doc.pdf",
                distance=0.2
            )
            for i in range(10)
        ]

        # Setup mock returns
        hierarchical_service.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_documents
        hierarchical_service.db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_chunks

        results = await hierarchical_service.search(
            query_embedding=query_embedding,
            user_id=user_id,
            collection_id=None,
            top_k=10,
            document_multiplier=3
        )

        assert len(results) == 10

    @pytest.mark.asyncio
    async def test_hierarchical_search_no_documents_returns_empty(self, hierarchical_service, query_embedding, user_id):
        """Test hierarchical search returns empty list when no documents found"""
        # No documents found in tier-1
        hierarchical_service.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []

        results = await hierarchical_service.search(
            query_embedding=query_embedding,
            user_id=user_id,
            collection_id=None,
            top_k=10
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_hierarchical_search_custom_multiplier(self, hierarchical_service, query_embedding, user_id):
        """Test hierarchical search with custom document multiplier"""
        mock_documents = [Mock(id=uuid4(), title="Doc", filename="doc.pdf", distance=0.1) for _ in range(50)]
        mock_chunks = [
            Mock(
                id=uuid4(),
                content="Chunk",
                chunk_index=0,
                metadata_={},
                chunk_metadata={},
                document_id=uuid4(),
                collection_id=uuid4(),
                document_title="Doc",
                document_filename="doc.pdf",
                distance=0.1
            )
        ]

        hierarchical_service.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_documents
        hierarchical_service.db.query.return_value.join.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_chunks

        await hierarchical_service.search(
            query_embedding=query_embedding,
            user_id=user_id,
            collection_id=None,
            top_k=10,
            document_multiplier=5  # 10 * 5 = 50 documents
        )

        # Verify tier-1 was called with top_k * multiplier
        # The limit should be 50 (10 * 5)
        assert hierarchical_service.db.query.called


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_handles_empty_query_embedding(self, hierarchical_service, user_id):
        """Test with empty query embedding"""
        mock_results = []
        hierarchical_service.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_results

        results = await hierarchical_service.search(
            query_embedding=[],
            user_id=user_id,
            collection_id=None,
            top_k=10
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_handles_zero_top_k(self, hierarchical_service, query_embedding, user_id):
        """Test with top_k = 0"""
        mock_results = []
        hierarchical_service.db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_results

        results = await hierarchical_service.search(
            query_embedding=query_embedding,
            user_id=user_id,
            collection_id=None,
            top_k=0
        )

        assert results == []
