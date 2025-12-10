"""
Unit tests for new parsers (PPT, JSON, Email)
Tests parsing functionality with sample files
"""

import pytest
import asyncio
import os
from pathlib import Path

# Test file directory
TEST_DOCS_DIR = Path(__file__).parent.parent.parent / "test_docs"


class TestPPTParser:
    """Tests for PowerPoint parser"""

    @pytest.fixture
    def parser(self):
        from backend.parsers.ppt_parser import PPTParser
        return PPTParser()

    def test_can_parse_pptx(self, parser):
        """Test PPTX MIME type detection"""
        assert parser.can_parse(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )

    def test_can_parse_ppt(self, parser):
        """Test PPT MIME type detection"""
        assert parser.can_parse("application/vnd.ms-powerpoint")

    def test_cannot_parse_pdf(self, parser):
        """Test non-PPT rejection"""
        assert not parser.can_parse("application/pdf")

    @pytest.mark.asyncio
    async def test_parse_pptx_file(self, parser):
        """Test parsing actual PPTX file"""
        test_file = TEST_DOCS_DIR / "Happy-Studies-Spaces.pptx"
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        result = await parser.parse(str(test_file))

        assert "content" in result
        assert "metadata" in result
        assert "page_count" in result
        assert result["page_count"] > 0
        assert len(result["content"]) > 0
        assert "slide_count" in result["metadata"]

    @pytest.mark.asyncio
    async def test_parse_extracts_slide_content(self, parser):
        """Test that slide content is extracted"""
        test_file = TEST_DOCS_DIR / "Happy-Studies-Spaces.pptx"
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        result = await parser.parse(str(test_file))

        # Check slide markers in content
        assert "## Slide" in result["content"]


class TestJSONParser:
    """Tests for JSON parser"""

    @pytest.fixture
    def parser(self):
        from backend.parsers.json_parser import JSONParser
        return JSONParser()

    def test_can_parse_json(self, parser):
        """Test JSON MIME type detection"""
        assert parser.can_parse("application/json")

    def test_can_parse_jsonl(self, parser):
        """Test JSONL MIME type detection"""
        assert parser.can_parse("application/x-jsonlines")

    def test_cannot_parse_xml(self, parser):
        """Test non-JSON rejection"""
        assert not parser.can_parse("application/xml")

    @pytest.mark.asyncio
    async def test_parse_json_file(self, parser):
        """Test parsing actual JSON file"""
        test_file = TEST_DOCS_DIR / "sample.json"
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        result = await parser.parse(str(test_file))

        assert "content" in result
        assert "metadata" in result
        assert "page_count" in result
        assert len(result["content"]) > 0
        assert result["metadata"]["format"] == "json"

    @pytest.mark.asyncio
    async def test_parse_jsonl_file(self, parser):
        """Test parsing JSONL file"""
        test_file = TEST_DOCS_DIR / "sample.jsonl"
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        result = await parser.parse(str(test_file))

        assert "content" in result
        assert result["metadata"]["format"] == "jsonl"
        assert result["metadata"]["section_count"] >= 1

    def test_jsonl_format_detection(self, parser):
        """Test JSONL format detection"""
        jsonl_text = '{"id": 1}\n{"id": 2}\n{"id": 3}'
        assert parser._is_jsonl_format(jsonl_text)

        json_text = '{"id": 1, "data": [1, 2, 3]}'
        assert not parser._is_jsonl_format(json_text)


class TestEmailParser:
    """Tests for Email parser"""

    @pytest.fixture
    def parser(self):
        from backend.parsers.email_parser import EmailParser
        return EmailParser()

    def test_can_parse_eml(self, parser):
        """Test EML MIME type detection"""
        assert parser.can_parse("message/rfc822")

    def test_can_parse_outlook(self, parser):
        """Test Outlook MIME type detection"""
        assert parser.can_parse("application/vnd.ms-outlook")

    def test_cannot_parse_pdf(self, parser):
        """Test non-email rejection"""
        assert not parser.can_parse("application/pdf")

    @pytest.mark.asyncio
    async def test_parse_eml_file(self, parser):
        """Test parsing actual EML file"""
        test_file = TEST_DOCS_DIR / "sample.eml"
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        result = await parser.parse(str(test_file))

        assert "content" in result
        assert "metadata" in result
        assert "page_count" in result
        assert result["page_count"] == 1

        # Check headers extracted
        assert "headers" in result["metadata"]
        headers = result["metadata"]["headers"]
        assert "from" in headers
        assert "to" in headers
        assert "subject" in headers

    @pytest.mark.asyncio
    async def test_parse_extracts_body(self, parser):
        """Test that email body is extracted"""
        test_file = TEST_DOCS_DIR / "sample.eml"
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")

        result = await parser.parse(str(test_file))

        assert "## Email Headers" in result["content"]
        assert "## Email Body" in result["content"]


class TestParserFactoryIntegration:
    """Test ParserFactory with new parsers"""

    @pytest.fixture
    def factory(self):
        from backend.parsers import ParserFactory
        return ParserFactory()

    def test_factory_handles_pptx(self, factory):
        """Test factory can handle PPTX (DoclingParser or PPTParser)"""
        from backend.parsers.ppt_parser import PPTParser
        from backend.parsers.docling_parser import DoclingParser
        parser = factory.get_parser(
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
        # DoclingParser handles PPTX first, PPTParser is fallback
        assert isinstance(parser, (DoclingParser, PPTParser))

    def test_factory_returns_json_parser(self, factory):
        """Test factory returns JSONParser for JSON"""
        from backend.parsers.json_parser import JSONParser
        parser = factory.get_parser("application/json")
        assert isinstance(parser, JSONParser)

    def test_factory_returns_email_parser(self, factory):
        """Test factory returns EmailParser for EML"""
        from backend.parsers.email_parser import EmailParser
        parser = factory.get_parser("message/rfc822")
        assert isinstance(parser, EmailParser)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
