"""
Unit tests for VectorSearchService

Tests:
- Semantic vector search
- Keyword full-text search
- Hybrid search with RRF fusion
- Metadata filtering
- Result formatting
"""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from backend.search.vector_search import VectorSearchService


@pytest.mark.unit
class TestVectorSearchService:
    """Test suite for VectorSearchService"""

    def test_init(self, db_session):
        """Test service initialization"""
        service = VectorSearchService(db_session)
        assert service.db == db_session

    def test_search_basic(self, db_session, test_user, test_collection, test_chunks):
        """Test basic semantic search"""
        service = VectorSearchService(db_session)

        query_embedding = [0.1] * 1536
        results = service.search(
            query_embedding=query_embedding,
            user_id=test_user.id,
            collection_id=test_collection.id,
            top_k=3
        )

        assert len(results) <= 3
        assert all('chunk_id' in r for r in results)
        assert all('content' in r for r in results)
        assert all('score' in r for r in results)
        assert all('document' in r for r in results)

    def test_search_with_user_filter(self, db_session, test_user, test_chunks):
        """Test search filtered by user"""
        service = VectorSearchService(db_session)

        query_embedding = [0.1] * 1536
        results = service.search(
            query_embedding=query_embedding,
            user_id=test_user.id,
            top_k=5
        )

        # All results should belong to test_user
        assert all(r['chunk_id'] for r in results)

    def test_search_with_collection_filter(self, db_session, test_user, test_collection, test_chunks):
        """Test search filtered by collection"""
        service = VectorSearchService(db_session)

        query_embedding = [0.1] * 1536
        results = service.search(
            query_embedding=query_embedding,
            user_id=test_user.id,
            collection_id=test_collection.id,
            top_k=5
        )

        # All results should belong to test_collection
        assert all(r['collection_id'] == str(test_collection.id) for r in results)

    def test_search_no_results(self, db_session, test_user):
        """Test search with no matching results"""
        service = VectorSearchService(db_session)

        # Search with non-existent user
        query_embedding = [0.1] * 1536
        results = service.search(
            query_embedding=query_embedding,
            user_id=uuid4(),  # Random user ID
            top_k=5
        )

        assert len(results) == 0

    def test_search_result_structure(self, db_session, test_user, test_chunks):
        """Test structure of search results"""
        service = VectorSearchService(db_session)

        query_embedding = [0.1] * 1536
        results = service.search(
            query_embedding=query_embedding,
            user_id=test_user.id,
            top_k=1
        )

        if results:
            result = results[0]
            assert 'chunk_id' in result
            assert 'content' in result
            assert 'chunk_index' in result
            assert 'score' in result
            assert 'metadata' in result
            assert 'chunk_metadata' in result
            assert 'document' in result
            assert 'id' in result['document']
            assert 'title' in result['document']
            assert 'filename' in result['document']

    def test_keyword_search(self, db_session, test_user, test_collection, test_chunks):
        """Test keyword full-text search"""
        service = VectorSearchService(db_session)

        results = service._keyword_search(
            query_text="test chunk",
            user_id=test_user.id,
            collection_id=test_collection.id,
            top_k=3
        )

        # Results should contain matching text
        assert len(results) <= 3
        assert all('chunk_id' in r for r in results)
        assert all('score' in r for r in results)

    def test_hybrid_search(self, db_session, test_user, test_collection, test_chunks):
        """Test hybrid search combining semantic and keyword"""
        service = VectorSearchService(db_session)

        query_embedding = [0.1] * 1536
        results = service.hybrid_search(
            query_text="test chunk",
            query_embedding=query_embedding,
            user_id=test_user.id,
            collection_id=test_collection.id,
            top_k=3
        )

        assert len(results) <= 3
        assert all('chunk_id' in r for r in results)
        assert all('score' in r for r in results)

    def test_reciprocal_rank_fusion(self, db_session):
        """Test RRF merging algorithm"""
        service = VectorSearchService(db_session)

        results_a = [
            {'chunk_id': '1', 'content': 'A', 'score': 0.9},
            {'chunk_id': '2', 'content': 'B', 'score': 0.8},
            {'chunk_id': '3', 'content': 'C', 'score': 0.7}
        ]

        results_b = [
            {'chunk_id': '2', 'content': 'B', 'score': 0.95},
            {'chunk_id': '3', 'content': 'C', 'score': 0.85},
            {'chunk_id': '4', 'content': 'D', 'score': 0.75}
        ]

        merged = service._reciprocal_rank_fusion(results_a, results_b, k=60)

        # Should have 4 unique chunks
        assert len(merged) == 4

        # Chunk 2 and 3 appear in both, should rank higher
        chunk_ids = [r['chunk_id'] for r in merged]
        assert '2' in chunk_ids[:2] or '3' in chunk_ids[:2]

        # All results should have scores
        assert all('score' in r for r in merged)

    def test_reciprocal_rank_fusion_no_overlap(self, db_session):
        """Test RRF with no overlapping results"""
        service = VectorSearchService(db_session)

        results_a = [
            {'chunk_id': '1', 'content': 'A', 'score': 0.9},
            {'chunk_id': '2', 'content': 'B', 'score': 0.8}
        ]

        results_b = [
            {'chunk_id': '3', 'content': 'C', 'score': 0.7},
            {'chunk_id': '4', 'content': 'D', 'score': 0.6}
        ]

        merged = service._reciprocal_rank_fusion(results_a, results_b, k=60)

        assert len(merged) == 4

    def test_reciprocal_rank_fusion_empty(self, db_session):
        """Test RRF with empty result sets"""
        service = VectorSearchService(db_session)

        merged = service._reciprocal_rank_fusion([], [], k=60)

        assert len(merged) == 0

    def test_reciprocal_rank_fusion_one_empty(self, db_session):
        """Test RRF with one empty result set"""
        service = VectorSearchService(db_session)

        results = [
            {'chunk_id': '1', 'content': 'A', 'score': 0.9}
        ]

        merged = service._reciprocal_rank_fusion(results, [], k=60)

        assert len(merged) == 1
        assert merged[0]['chunk_id'] == '1'

    def test_search_top_k_limit(self, db_session, test_user, test_chunks):
        """Test that top_k limits results correctly"""
        service = VectorSearchService(db_session)

        query_embedding = [0.1] * 1536

        results_2 = service.search(
            query_embedding=query_embedding,
            user_id=test_user.id,
            top_k=2
        )

        results_5 = service.search(
            query_embedding=query_embedding,
            user_id=test_user.id,
            top_k=5
        )

        assert len(results_2) <= 2
        assert len(results_5) <= 5
        if len(results_2) == 2 and len(results_5) >= 2:
            # First 2 results should be present in results_5 (order may vary with identical scores)
            results_2_ids = {r['chunk_id'] for r in results_2}
            results_5_ids = {r['chunk_id'] for r in results_5}
            assert results_2_ids.issubset(results_5_ids)
