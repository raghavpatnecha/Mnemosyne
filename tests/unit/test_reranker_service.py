"""
Unit tests for RerankerService

Tests:
- Reranker initialization with different providers
- Reranking with mocked rerankers library
- Batch reranking
- Threshold filtering
- Score extraction
- Provider availability checks
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import List, Dict

from backend.services.reranker_service import RerankerService
from backend.config import settings


@pytest.mark.unit
class TestRerankerService:
    """Test suite for RerankerService"""

    @patch('backend.services.reranker_service.settings')
    def test_init_disabled(self, mock_settings):
        """Test initialization when reranking is disabled"""
        mock_settings.RERANK_ENABLED = False

        service = RerankerService()

        assert service.reranker is None
        assert not service.is_available()

    @patch('backend.services.reranker_service.settings')
    @patch('backend.services.reranker_service.Reranker')
    def test_init_flashrank_provider(self, mock_reranker_class, mock_settings):
        """Test initialization with Flashrank provider"""
        mock_settings.RERANK_ENABLED = True
        mock_settings.RERANK_PROVIDER = 'flashrank'
        mock_settings.RERANK_MODEL = 'ms-marco-MultiBERT-L-12'
        mock_settings.RERANK_API_KEY = None

        mock_reranker = MagicMock()
        mock_reranker_class.return_value = mock_reranker

        service = RerankerService()

        assert service.reranker is not None
        mock_reranker_class.assert_called_once_with(
            model_name='ms-marco-MultiBERT-L-12',
            model_type='flashrank',
            cache_dir='./models'
        )

    @patch('backend.services.reranker_service.settings')
    @patch('backend.services.reranker_service.Reranker')
    def test_init_cohere_provider(self, mock_reranker_class, mock_settings):
        """Test initialization with Cohere provider"""
        mock_settings.RERANK_ENABLED = True
        mock_settings.RERANK_PROVIDER = 'cohere'
        mock_settings.RERANK_MODEL = 'rerank-english-v2.0'
        mock_settings.RERANK_API_KEY = 'test_api_key'

        mock_reranker = MagicMock()
        mock_reranker_class.return_value = mock_reranker

        service = RerankerService()

        assert service.reranker is not None
        mock_reranker_class.assert_called_once_with(
            model_name='rerank-english-v2.0',
            model_type='api',
            api_key='test_api_key'
        )

    @patch('backend.services.reranker_service.settings')
    def test_init_unsupported_provider(self, mock_settings):
        """Test initialization with unsupported provider"""
        mock_settings.RERANK_ENABLED = True
        mock_settings.RERANK_PROVIDER = 'unsupported_provider'

        service = RerankerService()

        assert service.reranker is None

    @patch('backend.services.reranker_service.Document')
    def test_rerank_basic(self, mock_document_class):
        """Test basic reranking functionality"""
        service = RerankerService()
        service.reranker = MagicMock()

        # Mock Document class
        def create_doc(text, doc_id, metadata):
            doc = MagicMock()
            doc.text = text
            doc.doc_id = doc_id
            doc.metadata = metadata
            return doc

        mock_document_class.side_effect = create_doc

        # Mock rank results
        mock_result = MagicMock()
        mock_result.results = []

        chunks = [
            {'chunk_id': 'chunk_1', 'content': 'First chunk'},
            {'chunk_id': 'chunk_2', 'content': 'Second chunk'},
            {'chunk_id': 'chunk_3', 'content': 'Third chunk'}
        ]

        for i, chunk in enumerate(chunks):
            rank_item = MagicMock()
            rank_item.document = MagicMock()
            rank_item.document.metadata = chunk.copy()
            rank_item.score = 1.0 - (i * 0.2)
            rank_item.rank = i + 1
            mock_result.results.append(rank_item)

        service.reranker.rank.return_value = mock_result

        results = service.rerank(
            query="test query",
            chunks=chunks
        )

        assert len(results) == 3
        assert results[0]['rerank_score'] == 1.0
        assert results[1]['rerank_score'] == 0.8
        assert results[2]['rerank_score'] == 0.6
        assert all('rerank_rank' in r for r in results)

    def test_rerank_no_reranker(self):
        """Test reranking when reranker is not available"""
        service = RerankerService()
        service.reranker = None

        chunks = [{'chunk_id': 'chunk_1', 'content': 'Test'}]
        results = service.rerank(query="test", chunks=chunks)

        assert results == chunks

    def test_rerank_empty_chunks(self):
        """Test reranking with empty chunks list"""
        service = RerankerService()
        service.reranker = MagicMock()

        results = service.rerank(query="test", chunks=[])

        assert results == []

    @patch('backend.services.reranker_service.Document')
    def test_rerank_with_top_k(self, mock_document_class):
        """Test reranking with top_k parameter"""
        service = RerankerService()
        service.reranker = MagicMock()

        # Mock Document class
        def create_doc(text, doc_id, metadata):
            doc = MagicMock()
            doc.text = text
            doc.doc_id = doc_id
            doc.metadata = metadata
            return doc

        mock_document_class.side_effect = create_doc

        mock_result = MagicMock()
        mock_result.results = []

        chunks = [
            {'chunk_id': f'chunk_{i}', 'content': f'Chunk {i}'}
            for i in range(5)
        ]

        for i, chunk in enumerate(chunks):
            rank_item = MagicMock()
            rank_item.document = MagicMock()
            rank_item.document.metadata = chunk.copy()
            rank_item.score = 1.0 - (i * 0.1)
            rank_item.rank = i + 1
            mock_result.results.append(rank_item)

        service.reranker.rank.return_value = mock_result

        results = service.rerank(
            query="test query",
            chunks=chunks,
            top_k=3
        )

        assert len(results) == 3

    @patch('backend.services.reranker_service.Document')
    def test_rerank_with_threshold(self, mock_document_class):
        """Test threshold-based reranking"""
        service = RerankerService()
        service.reranker = MagicMock()

        def create_doc(text, doc_id, metadata):
            doc = MagicMock()
            doc.text = text
            doc.doc_id = doc_id
            doc.metadata = metadata
            return doc

        mock_document_class.side_effect = create_doc

        mock_result = MagicMock()
        mock_result.results = []

        chunks = [
            {'chunk_id': f'chunk_{i}', 'content': f'Chunk {i}'}
            for i in range(5)
        ]

        for i, chunk in enumerate(chunks):
            rank_item = MagicMock()
            rank_item.document = MagicMock()
            rank_item.document.metadata = chunk.copy()
            rank_item.score = 1.0 - (i * 0.3)  # Scores: 1.0, 0.7, 0.4, 0.1, -0.2
            rank_item.rank = i + 1
            mock_result.results.append(rank_item)

        service.reranker.rank.return_value = mock_result

        results = service.rerank_with_threshold(
            query="test query",
            chunks=chunks,
            threshold=0.5
        )

        # Only first 2 chunks should pass threshold
        assert len(results) == 2
        assert all(r['rerank_score'] >= 0.5 for r in results)

    def test_batch_rerank(self):
        """Test batch reranking"""
        service = RerankerService()
        service.rerank = MagicMock(side_effect=lambda q, c, **kwargs: c)

        queries = ["query1", "query2"]
        chunks_list = [
            [{'chunk_id': '1', 'content': 'Chunk 1'}],
            [{'chunk_id': '2', 'content': 'Chunk 2'}]
        ]

        results = service.batch_rerank(queries, chunks_list)

        assert len(results) == 2
        assert service.rerank.call_count == 2

    def test_batch_rerank_length_mismatch(self):
        """Test batch rerank with mismatched lengths"""
        service = RerankerService()

        queries = ["query1"]
        chunks_list = [
            [{'chunk_id': '1'}],
            [{'chunk_id': '2'}]
        ]

        with pytest.raises(ValueError, match="same length"):
            service.batch_rerank(queries, chunks_list)

    @patch('backend.services.reranker_service.Document')
    def test_get_rerank_scores(self, mock_document_class):
        """Test extracting rerank scores"""
        service = RerankerService()
        service.reranker = MagicMock()

        def create_doc(text, doc_id, metadata):
            doc = MagicMock()
            doc.text = text
            doc.doc_id = doc_id
            doc.metadata = metadata
            return doc

        mock_document_class.side_effect = create_doc

        mock_result = MagicMock()
        mock_result.results = []

        chunks = [
            {'chunk_id': 'chunk_1', 'content': 'First'},
            {'chunk_id': 'chunk_2', 'content': 'Second'}
        ]

        for i, chunk in enumerate(chunks):
            rank_item = MagicMock()
            rank_item.document = MagicMock()
            rank_item.document.metadata = chunk.copy()
            rank_item.score = 0.9 - (i * 0.2)
            rank_item.rank = i + 1
            mock_result.results.append(rank_item)

        service.reranker.rank.return_value = mock_result

        scores = service.get_rerank_scores("test", chunks)

        assert len(scores) == 2
        assert scores[0] == 0.9
        assert scores[1] == 0.7

    @patch('backend.services.reranker_service.settings')
    def test_get_provider_info(self, mock_settings):
        """Test getting provider information"""
        mock_settings.RERANK_ENABLED = True
        mock_settings.RERANK_PROVIDER = 'cohere'
        mock_settings.RERANK_MODEL = 'rerank-english-v2.0'

        service = RerankerService()
        service.reranker = MagicMock()

        info = service.get_provider_info()

        assert info['enabled'] is True
        assert info['provider'] == 'cohere'
        assert info['model'] == 'rerank-english-v2.0'
        assert info['requires_api_key'] is True
        assert info['available'] is True
