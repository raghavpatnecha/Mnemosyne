"""
Unit tests for DocumentSummaryService
Tests document summarization and embedding generation
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from backend.services.document_summary_service import DocumentSummaryService


@pytest.fixture
def summary_service():
    """Create DocumentSummaryService instance"""
    with patch('backend.services.document_summary_service.OpenAIEmbedder'):
        service = DocumentSummaryService()
        service.embedder.embed = AsyncMock(return_value=[0.1] * 1536)
        return service


@pytest.fixture
def sample_content():
    """Sample document content"""
    return """
    This is a comprehensive document about machine learning.
    It covers supervised and unsupervised learning techniques.
    The document explains neural networks, decision trees, and clustering algorithms.
    """ * 10  # Make it longer


@pytest.fixture
def sample_metadata():
    """Sample document metadata"""
    return {
        "title": "Introduction to Machine Learning",
        "filename": "ml_intro.pdf"
    }


class TestConcatStrategy:
    """Test concatenation-based summarization strategy"""

    @pytest.mark.asyncio
    async def test_concat_strategy_with_title_and_filename(self, summary_service, sample_content, sample_metadata):
        """Test concat strategy includes title and filename"""
        summary = await summary_service.generate_document_summary(
            content=sample_content,
            metadata=sample_metadata,
            strategy="concat"
        )

        assert "Title: Introduction to Machine Learning" in summary
        assert "File: ml_intro.pdf" in summary
        assert len(summary) > 0

    @pytest.mark.asyncio
    async def test_concat_strategy_truncates_content(self, summary_service, sample_metadata):
        """Test concat strategy truncates long content to 2000 chars"""
        long_content = "A" * 5000

        summary = await summary_service.generate_document_summary(
            content=long_content,
            metadata=sample_metadata,
            strategy="concat"
        )

        # Summary should not exceed metadata + 2000 chars significantly
        # Title + File lines are about 60 chars, so max ~2060
        assert len(summary) < 2100

    @pytest.mark.asyncio
    async def test_concat_strategy_handles_empty_metadata(self, summary_service, sample_content):
        """Test concat strategy with empty metadata"""
        summary = await summary_service.generate_document_summary(
            content=sample_content,
            metadata={},
            strategy="concat"
        )

        assert len(summary) > 0
        assert "This is a comprehensive document" in summary

    @pytest.mark.asyncio
    async def test_concat_strategy_handles_empty_content(self, summary_service, sample_metadata):
        """Test concat strategy with empty content"""
        summary = await summary_service.generate_document_summary(
            content="",
            metadata=sample_metadata,
            strategy="concat"
        )

        # Should still include metadata
        assert "Title: Introduction to Machine Learning" in summary
        assert "File: ml_intro.pdf" in summary


class TestLLMStrategy:
    """Test LLM-based summarization strategy"""

    @pytest.mark.asyncio
    async def test_llm_strategy_calls_litellm(self, summary_service, sample_content, sample_metadata):
        """Test LLM strategy calls acompletion"""
        with patch('backend.services.document_summary_service.acompletion') as mock_completion:
            mock_completion.return_value = Mock(
                choices=[Mock(message=Mock(content="This document covers ML basics."))]
            )

            summary = await summary_service.generate_document_summary(
                content=sample_content,
                metadata=sample_metadata,
                strategy="llm"
            )

            # Verify acompletion was called
            assert mock_completion.called
            call_args = mock_completion.call_args

            # Verify prompt contains title and filename
            messages = call_args.kwargs['messages']
            assert len(messages) == 1
            assert "Introduction to Machine Learning" in messages[0]['content']
            assert "ml_intro.pdf" in messages[0]['content']

            # Verify summary includes LLM output and metadata
            assert "This document covers ML basics" in summary
            assert "Title: Introduction to Machine Learning" in summary

    @pytest.mark.asyncio
    async def test_llm_strategy_truncates_long_content(self, summary_service, sample_metadata):
        """Test LLM strategy truncates content to 8000 chars"""
        long_content = "X" * 20000

        with patch('backend.services.document_summary_service.acompletion') as mock_completion:
            mock_completion.return_value = Mock(
                choices=[Mock(message=Mock(content="Summary of long doc."))]
            )

            await summary_service.generate_document_summary(
                content=long_content,
                metadata=sample_metadata,
                strategy="llm"
            )

            # Verify content was truncated
            messages = mock_completion.call_args.kwargs['messages']
            prompt_content = messages[0]['content']
            # Should contain truncated content (8000 chars) + prompt text
            assert len(prompt_content) < 8500

    @pytest.mark.asyncio
    async def test_llm_strategy_fallback_on_error(self, summary_service, sample_content, sample_metadata):
        """Test LLM strategy falls back to concat on error"""
        with patch('backend.services.document_summary_service.acompletion') as mock_completion:
            mock_completion.side_effect = Exception("API Error")

            summary = await summary_service.generate_document_summary(
                content=sample_content,
                metadata=sample_metadata,
                strategy="llm"
            )

            # Should fallback to concat strategy
            assert "Title: Introduction to Machine Learning" in summary
            assert len(summary) > 0


class TestGenerateEmbedding:
    """Test document embedding generation"""

    @pytest.mark.asyncio
    async def test_generate_document_embedding(self, summary_service):
        """Test embedding generation from summary"""
        summary = "This is a document summary."

        embedding = await summary_service.generate_document_embedding(summary)

        # Verify embedder was called
        assert summary_service.embedder.embed.called
        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)

    @pytest.mark.asyncio
    async def test_generate_document_embedding_caches(self, summary_service):
        """Test embedding generation uses cache"""
        summary = "This is a document summary."

        # Call twice
        embedding1 = await summary_service.generate_document_embedding(summary)
        embedding2 = await summary_service.generate_document_embedding(summary)

        assert embedding1 == embedding2


class TestGenerateSummaryAndEmbedding:
    """Test combined summary and embedding generation"""

    @pytest.mark.asyncio
    async def test_generate_summary_and_embedding(self, summary_service, sample_content, sample_metadata):
        """Test combined generation returns both summary and embedding"""
        result = await summary_service.generate_summary_and_embedding(
            content=sample_content,
            metadata=sample_metadata,
            strategy="concat"
        )

        assert "summary" in result
        assert "embedding" in result
        assert len(result["summary"]) > 0
        assert len(result["embedding"]) == 1536

    @pytest.mark.asyncio
    async def test_generate_summary_and_embedding_llm_strategy(self, summary_service, sample_content, sample_metadata):
        """Test combined generation with LLM strategy"""
        with patch('backend.services.document_summary_service.acompletion') as mock_completion:
            mock_completion.return_value = Mock(
                choices=[Mock(message=Mock(content="LLM summary."))]
            )

            result = await summary_service.generate_summary_and_embedding(
                content=sample_content,
                metadata=sample_metadata,
                strategy="llm"
            )

            assert "LLM summary" in result["summary"]
            assert len(result["embedding"]) == 1536


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_unknown_strategy_defaults_to_concat(self, summary_service, sample_content, sample_metadata):
        """Test unknown strategy defaults to concat"""
        summary = await summary_service.generate_document_summary(
            content=sample_content,
            metadata=sample_metadata,
            strategy="unknown_strategy"
        )

        # Should use concat strategy
        assert "Title: Introduction to Machine Learning" in summary

    @pytest.mark.asyncio
    async def test_none_values_in_metadata(self, summary_service, sample_content):
        """Test handling None values in metadata"""
        summary = await summary_service.generate_document_summary(
            content=sample_content,
            metadata={"title": None, "filename": None},
            strategy="concat"
        )

        assert len(summary) > 0

    @pytest.mark.asyncio
    async def test_very_short_content(self, summary_service, sample_metadata):
        """Test with very short content"""
        short_content = "Hi"

        summary = await summary_service.generate_document_summary(
            content=short_content,
            metadata=sample_metadata,
            strategy="concat"
        )

        assert "Title: Introduction to Machine Learning" in summary
        assert "Hi" in summary
