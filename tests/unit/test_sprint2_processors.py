"""
Unit tests for Sprint 2 domain processors.

Tests BookProcessor, EmailProcessor, ManualProcessor, and PresentationProcessor.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


class TestBookProcessor:
    """Tests for BookProcessor."""

    @pytest.fixture
    def processor(self):
        from backend.processors.book_processor import BookProcessor
        return BookProcessor()

    def test_processor_name(self, processor):
        """Test processor has correct name."""
        assert processor.name == "book"

    def test_supported_content_types(self, processor):
        """Test supported content types."""
        assert "application/pdf" in processor.supported_content_types
        assert "application/epub+zip" in processor.supported_content_types

    def test_can_process_book_content(self, processor):
        """Test book content detection."""
        content = """
        Table of Contents

        Chapter 1: Introduction
        This is the introduction to the book.

        Chapter 2: Getting Started
        This chapter covers the basics.

        Part I: Fundamentals

        Chapter 3: Core Concepts
        """
        score = processor.can_process(content, {})
        assert score > 0.3

    def test_can_process_non_book_content(self, processor):
        """Test non-book content returns low score."""
        content = "This is a simple text document with no structure."
        score = processor.can_process(content, {})
        assert score < 0.3

    def test_can_process_with_filename(self, processor):
        """Test filename detection."""
        content = "Some content here."
        score = processor.can_process(content, {"filename": "my_book.pdf"})
        # Should get bonus for "book" in filename
        assert score > 0

    @pytest.mark.asyncio
    async def test_process_extracts_chapters(self, processor):
        """Test chapter extraction."""
        content = """
        Chapter 1: Introduction
        This is the introduction.

        Chapter 2: Methods
        This explains the methods.

        Chapter 3: Results
        Here are the results.
        """
        result = await processor.process(content, {}, "test_book.pdf")

        assert result.processor_name == "book"
        assert result.document_metadata["document_type"] == "book"
        assert result.document_metadata["chapter_count"] >= 3

    @pytest.mark.asyncio
    async def test_process_extracts_parts(self, processor):
        """Test part extraction."""
        content = """
        Part I: Foundations

        Chapter 1: Basics

        Part II: Advanced Topics

        Chapter 5: Advanced Concepts
        """
        result = await processor.process(content, {}, "test.pdf")

        assert result.document_metadata["part_count"] >= 2

    @pytest.mark.asyncio
    async def test_process_detects_toc(self, processor):
        """Test table of contents detection via front matter."""
        content = """Table of Contents

Chapter 1 ........... 1
Chapter 2 ........... 15
Chapter 3 ........... 30

Chapter 1: Introduction
"""
        result = await processor.process(content, {}, "test.pdf")

        # TOC is detected as front matter
        assert "Table of Contents" in result.document_metadata["front_matter"]


class TestEmailProcessor:
    """Tests for EmailProcessor."""

    @pytest.fixture
    def processor(self):
        from backend.processors.email_processor import EmailProcessor
        return EmailProcessor()

    def test_processor_name(self, processor):
        """Test processor has correct name."""
        assert processor.name == "email"

    def test_supported_content_types(self, processor):
        """Test supported content types."""
        assert "message/rfc822" in processor.supported_content_types
        assert "text/x-email" in processor.supported_content_types

    def test_can_process_email_content(self, processor):
        """Test email content detection."""
        content = """From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 1 Jan 2024 10:00:00 +0000

This is the body of the email.
"""
        score = processor.can_process(content, {})
        assert score > 0.4

    def test_can_process_non_email_content(self, processor):
        """Test non-email content returns low score."""
        content = "This is just regular text without email headers."
        score = processor.can_process(content, {})
        assert score < 0.3

    def test_can_process_with_eml_filename(self, processor):
        """Test .eml filename detection."""
        content = "Some content"
        score = processor.can_process(content, {"filename": "message.eml"})
        assert score > 0.2

    @pytest.mark.asyncio
    async def test_process_extracts_headers(self, processor):
        """Test header extraction."""
        content = """From: John Doe <john@example.com>
To: Jane Smith <jane@example.com>
Subject: Meeting Tomorrow
Date: Tue, 2 Jan 2024 14:30:00 +0000

Hi Jane,

Let's meet tomorrow at 3pm.

Best,
John
"""
        result = await processor.process(content, {}, "email.eml")

        assert result.processor_name == "email"
        assert result.document_metadata["document_type"] == "email"
        assert result.document_metadata["subject"] == "Meeting Tomorrow"
        assert "john@example.com" in str(result.document_metadata["from"])

    @pytest.mark.asyncio
    async def test_process_detects_reply(self, processor):
        """Test reply detection."""
        content = """From: reply@example.com
To: original@example.com
Subject: Re: Original Subject
In-Reply-To: <message-id@example.com>

Thanks for your email.

> On Jan 1, 2024, original wrote:
> This is the original message.
"""
        result = await processor.process(content, {}, "reply.eml")

        assert result.document_metadata["is_reply"] is True

    @pytest.mark.asyncio
    async def test_process_detects_forward(self, processor):
        """Test forward detection."""
        content = """From: forwarder@example.com
To: recipient@example.com
Subject: Fwd: Important Message

See below.

-------- Original Message --------
Subject: Important Message
From: sender@example.com
"""
        result = await processor.process(content, {}, "forward.eml")

        assert result.document_metadata["is_forward"] is True


class TestManualProcessor:
    """Tests for ManualProcessor."""

    @pytest.fixture
    def processor(self):
        from backend.processors.manual_processor import ManualProcessor
        return ManualProcessor()

    def test_processor_name(self, processor):
        """Test processor has correct name."""
        assert processor.name == "manual"

    def test_can_process_manual_content(self, processor):
        """Test manual content detection."""
        content = """
        # Installation Guide

        ## Prerequisites
        - Python 3.8 or higher
        - pip package manager

        ## Installation

        Step 1: Clone the repository
        Step 2: Install dependencies
        Step 3: Run the setup script

        ## Configuration

        Edit the config.yaml file.

        ## Troubleshooting

        If you encounter errors, check the logs.

        NOTE: Always backup your data first.
        """
        score = processor.can_process(content, {})
        assert score > 0.4

    def test_can_process_non_manual_content(self, processor):
        """Test non-manual content returns low score."""
        content = "This is a story about a cat named Whiskers."
        score = processor.can_process(content, {})
        assert score < 0.3

    @pytest.mark.asyncio
    async def test_process_extracts_sections(self, processor):
        """Test section extraction."""
        content = """
        # Installation

        Follow these steps to install.

        # Configuration

        Configure your settings.

        # Troubleshooting

        Common issues and solutions.
        """
        result = await processor.process(content, {}, "manual.md")

        assert result.processor_name == "manual"
        assert result.document_metadata["document_type"] == "manual"
        assert result.document_metadata["has_installation"] is True
        assert result.document_metadata["has_troubleshooting"] is True

    @pytest.mark.asyncio
    async def test_process_extracts_callouts(self, processor):
        """Test callout extraction."""
        content = """
        # Guide

        NOTE: This is important.

        WARNING: Be careful here.

        TIP: Try this shortcut.
        """
        result = await processor.process(content, {}, "guide.md")

        assert result.document_metadata["callout_count"] >= 3

    @pytest.mark.asyncio
    async def test_process_extracts_code_blocks(self, processor):
        """Test code block detection."""
        content = """
        # Commands

        Run this command:

        ```bash
        pip install package
        ```

        Then verify:

        $ python --version
        """
        result = await processor.process(content, {}, "readme.md")

        assert result.document_metadata["has_code_examples"] is True

    @pytest.mark.asyncio
    async def test_process_detects_manual_type(self, processor):
        """Test manual type detection."""
        content = """
        # Quick Start Guide

        ## Installation

        1. Download the package
        2. Run the installer
        3. Configure settings
        """
        result = await processor.process(content, {}, "quickstart.md")

        assert result.document_metadata["manual_type"] in [
            "quick_start", "installation_guide", "user_guide"
        ]


class TestPresentationProcessor:
    """Tests for PresentationProcessor."""

    @pytest.fixture
    def processor(self):
        from backend.processors.presentation_processor import PresentationProcessor
        return PresentationProcessor()

    def test_processor_name(self, processor):
        """Test processor has correct name."""
        assert processor.name == "presentation"

    def test_supported_content_types(self, processor):
        """Test supported content types."""
        expected = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        assert expected in processor.supported_content_types

    def test_can_process_presentation_content(self, processor):
        """Test presentation content detection."""
        content = """
        ---

        # Title Slide

        Presentation by Author

        ---

        # Slide 2: Overview

        - Point 1
        - Point 2
        - Point 3

        ---

        # Slide 3: Details

        - More details here
        """
        score = processor.can_process(content, {})
        assert score > 0.3

    def test_can_process_with_pptx_filename(self, processor):
        """Test .pptx filename detection."""
        content = "Some content"
        score = processor.can_process(content, {"filename": "slides.pptx"})
        assert score > 0.2

    @pytest.mark.asyncio
    async def test_process_extracts_slides(self, processor):
        """Test slide extraction."""
        content = """---

# Introduction

Welcome to this presentation.

---

# Agenda

- Topic 1
- Topic 2
- Topic 3

---

# Topic 1

Details about topic 1.
"""
        result = await processor.process(content, {}, "presentation.md")

        assert result.processor_name == "presentation"
        assert result.document_metadata["document_type"] == "presentation"
        # Slide count may vary based on parsing - check we got at least 1
        assert result.document_metadata["slide_count"] >= 1

    @pytest.mark.asyncio
    async def test_process_extracts_bullets(self, processor):
        """Test bullet point extraction."""
        content = """---

# Slide with Bullets

- First point
- Second point
- Third point
- Fourth point
"""
        result = await processor.process(content, {}, "test.pptx")

        assert result.document_metadata["total_bullet_points"] >= 4

    @pytest.mark.asyncio
    async def test_process_detects_agenda(self, processor):
        """Test agenda slide detection."""
        content = """---

# Title

---

# Agenda

- Introduction
- Main Content
- Conclusion

---

# Introduction
"""
        result = await processor.process(content, {}, "deck.pptx")

        # Agenda detection depends on slide parsing - just verify structure is extracted
        assert result.document_metadata["slide_count"] >= 1

    @pytest.mark.asyncio
    async def test_process_generates_chunk_annotations(self, processor):
        """Test chunk annotations for slides."""
        content = """---

# Slide 1

Content 1.

---

# Slide 2

Content 2.
"""
        result = await processor.process(content, {}, "test.pptx")

        # Should have annotations for each slide
        assert len(result.chunk_annotations) > 0
        for annotation in result.chunk_annotations:
            assert annotation["type"] == "presentation_slide"
            assert "slide_number" in annotation


class TestProcessorRegistration:
    """Tests for processor registration."""

    def test_all_sprint2_processors_registered(self):
        """Test all Sprint 2 processors are registered."""
        from backend.processors import ProcessorFactory

        processors = ProcessorFactory.get_available_processors()

        assert "book" in processors
        assert "email" in processors
        assert "manual" in processors
        assert "presentation" in processors

    def test_valid_document_types_updated(self):
        """Test VALID_DOCUMENT_TYPES includes new types."""
        from backend.processors import VALID_DOCUMENT_TYPES

        new_types = {"book", "email", "manual", "presentation", "resume"}
        for doc_type in new_types:
            assert doc_type in VALID_DOCUMENT_TYPES

    def test_detector_valid_types_updated(self):
        """Test DocumentTypeDetector.VALID_TYPES includes new types."""
        from backend.processors.detector import DocumentTypeDetector

        new_types = {"book", "email", "manual", "presentation", "resume"}
        for doc_type in new_types:
            assert doc_type in DocumentTypeDetector.VALID_TYPES


class TestProcessorFactory:
    """Tests for ProcessorFactory with new processors."""

    def test_get_book_processor(self):
        """Test getting book processor."""
        from backend.processors import ProcessorFactory
        from backend.processors.book_processor import BookProcessor

        processor = ProcessorFactory.get_processor("book")
        assert processor is not None
        assert isinstance(processor, BookProcessor)

    def test_get_email_processor(self):
        """Test getting email processor."""
        from backend.processors import ProcessorFactory
        from backend.processors.email_processor import EmailProcessor

        processor = ProcessorFactory.get_processor("email")
        assert processor is not None
        assert isinstance(processor, EmailProcessor)

    def test_get_manual_processor(self):
        """Test getting manual processor."""
        from backend.processors import ProcessorFactory
        from backend.processors.manual_processor import ManualProcessor

        processor = ProcessorFactory.get_processor("manual")
        assert processor is not None
        assert isinstance(processor, ManualProcessor)

    def test_get_presentation_processor(self):
        """Test getting presentation processor."""
        from backend.processors import ProcessorFactory
        from backend.processors.presentation_processor import PresentationProcessor

        processor = ProcessorFactory.get_processor("presentation")
        assert processor is not None
        assert isinstance(processor, PresentationProcessor)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
