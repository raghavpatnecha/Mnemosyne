"""
Integration tests for new parsers - tests full parse -> chunk pipeline
"""

import pytest
import asyncio
from pathlib import Path

TEST_DOCS_DIR = Path(__file__).parent.parent.parent / "test_docs"


class TestParserChunkingPipeline:
    """Test that parsers integrate properly with chunking"""

    @pytest.fixture
    def factory(self):
        from backend.parsers import ParserFactory
        return ParserFactory()

    @pytest.fixture
    def chunker(self):
        from backend.chunking import ChonkieChunker
        return ChonkieChunker()

    @pytest.mark.asyncio
    async def test_json_parse_chunk_pipeline(self, factory, chunker):
        """Test JSON file through full pipeline"""
        test_file = TEST_DOCS_DIR / "sample.json"
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        # Parse
        parser = factory.get_parser("application/json")
        result = await parser.parse(str(test_file))

        assert "content" in result
        assert len(result["content"]) > 0
        assert result["metadata"]["format"] == "json"

        # Chunk
        chunks = chunker.chunk(result["content"])

        assert len(chunks) > 0
        for chunk in chunks:
            assert "content" in chunk
            assert "chunk_index" in chunk
            assert "metadata" in chunk
            assert "tokens" in chunk["metadata"]

    @pytest.mark.asyncio
    async def test_jsonl_parse_chunk_pipeline(self, factory, chunker):
        """Test JSONL file through full pipeline"""
        test_file = TEST_DOCS_DIR / "sample.jsonl"
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        # Parse
        parser = factory.get_parser("application/x-jsonlines")
        result = await parser.parse(str(test_file))

        assert "content" in result
        assert len(result["content"]) > 0
        assert result["metadata"]["format"] == "jsonl"

        # Chunk
        chunks = chunker.chunk(result["content"])

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_email_parse_chunk_pipeline(self, factory, chunker):
        """Test email file through full pipeline"""
        test_file = TEST_DOCS_DIR / "sample.eml"
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        # Parse
        parser = factory.get_parser("message/rfc822")
        result = await parser.parse(str(test_file))

        assert "content" in result
        assert len(result["content"]) > 0

        # Verify email structure
        assert "## Email Headers" in result["content"]
        assert "## Email Body" in result["content"]

        # Verify metadata
        assert "headers" in result["metadata"]
        assert "from" in result["metadata"]["headers"]
        assert "subject" in result["metadata"]["headers"]

        # Chunk
        chunks = chunker.chunk(result["content"])

        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_pptx_parse_chunk_pipeline(self, factory, chunker):
        """Test PowerPoint file through full pipeline"""
        test_file = TEST_DOCS_DIR / "Happy-Studies-Spaces.pptx"
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        # Parse - DoclingParser or PPTParser may handle this
        parser = factory.get_parser(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        result = await parser.parse(str(test_file))

        assert "content" in result
        assert len(result["content"]) > 0
        assert result["page_count"] > 0

        # Chunk
        chunks = chunker.chunk(result["content"])

        assert len(chunks) > 0


class TestDocumentTypeValidation:
    """Test document type validation in processors"""

    def test_all_new_document_types_valid(self):
        """Verify all new document types are in VALID_DOCUMENT_TYPES"""
        from backend.processors import VALID_DOCUMENT_TYPES

        new_types = {"book", "email", "manual", "presentation", "resume"}

        for doc_type in new_types:
            assert doc_type in VALID_DOCUMENT_TYPES, \
                f"Missing document type: {doc_type}"

    def test_retrieval_accepts_new_document_types(self):
        """Verify retrieval schema accepts new document types"""
        from backend.processors import VALID_DOCUMENT_TYPES

        # All types should be valid for filtering
        expected_types = {
            "legal", "academic", "qa", "table", "general",
            "book", "email", "manual", "presentation", "resume"
        }

        assert VALID_DOCUMENT_TYPES == expected_types


class TestParserFactoryCompleteness:
    """Test that ParserFactory has all required parsers"""

    def test_factory_has_new_parsers(self):
        """Verify new parsers are registered"""
        from backend.parsers import ParserFactory
        from backend.parsers.ppt_parser import PPTParser
        from backend.parsers.json_parser import JSONParser
        from backend.parsers.email_parser import EmailParser

        factory = ParserFactory()
        parser_types = [type(p) for p in factory.parsers]

        assert PPTParser in parser_types
        assert JSONParser in parser_types
        assert EmailParser in parser_types

    def test_factory_parser_count(self):
        """Verify total parser count"""
        from backend.parsers import ParserFactory

        factory = ParserFactory()

        # Should have: Docling, YouTube, Video, Audio, Excel, PPT, JSON, Email, Image, Text
        assert len(factory.parsers) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
