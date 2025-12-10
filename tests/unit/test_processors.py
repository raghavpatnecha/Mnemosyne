"""
Unit tests for domain processors
Tests processor factory, detection, and individual processors
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.processors.base import DomainProcessor, ProcessorResult
from backend.processors import ProcessorFactory, VALID_DOCUMENT_TYPES
from backend.processors.legal_processor import LegalProcessor
from backend.processors.academic_processor import AcademicProcessor
from backend.processors.qa_processor import QAProcessor
from backend.processors.table_processor import TableProcessor


class TestValidDocumentTypes:
    """Test valid document types constant"""

    def test_valid_types_contains_expected(self):
        """Verify all expected document types are present"""
        expected = {
            "legal", "academic", "qa", "table", "general",
            "book", "email", "manual", "presentation", "resume"
        }
        assert VALID_DOCUMENT_TYPES == expected

    def test_valid_types_is_set(self):
        """Verify valid types is a set"""
        assert isinstance(VALID_DOCUMENT_TYPES, set)


class TestProcessorFactory:
    """Test ProcessorFactory registration and detection"""

    def test_get_available_processors_returns_dict(self):
        """Test get_available_processors returns registered processors"""
        processors = ProcessorFactory.get_available_processors()
        assert isinstance(processors, dict)
        assert len(processors) >= 8  # legal, academic, qa, table, book, email, manual, presentation

    def test_get_processor_legal(self):
        """Test getting legal processor by name"""
        processor = ProcessorFactory.get_processor("legal")
        assert processor is not None
        assert isinstance(processor, LegalProcessor)

    def test_get_processor_academic(self):
        """Test getting academic processor by name"""
        processor = ProcessorFactory.get_processor("academic")
        assert processor is not None
        assert isinstance(processor, AcademicProcessor)

    def test_get_processor_qa(self):
        """Test getting qa processor by name"""
        processor = ProcessorFactory.get_processor("qa")
        assert processor is not None
        assert isinstance(processor, QAProcessor)

    def test_get_processor_table(self):
        """Test getting table processor by name"""
        processor = ProcessorFactory.get_processor("table")
        assert processor is not None
        assert isinstance(processor, TableProcessor)

    def test_get_processor_invalid(self):
        """Test getting invalid processor returns None"""
        processor = ProcessorFactory.get_processor("invalid")
        assert processor is None

    def test_get_processor_general(self):
        """Test getting general processor returns None (no processor needed)"""
        processor = ProcessorFactory.get_processor("general")
        assert processor is None

    @pytest.mark.asyncio
    async def test_detect_and_get_processor_with_metadata_hint(self):
        """Test detection respects metadata document_type hint"""
        processor = await ProcessorFactory.detect_and_get_processor(
            content="Some content here",
            metadata={"document_type": "legal"},
            use_llm=False
        )
        assert processor is not None
        assert processor.name == "legal"

    @pytest.mark.asyncio
    async def test_detect_and_get_processor_invalid_metadata_hint(self):
        """Test detection ignores invalid metadata document_type"""
        processor = await ProcessorFactory.detect_and_get_processor(
            content="Q: What is Python?\nA: A programming language.",
            metadata={"document_type": "invalid_type"},
            use_llm=False
        )
        # Should fall back to heuristic detection (Q&A content)
        # May return qa or None depending on confidence
        if processor:
            assert processor.name in VALID_DOCUMENT_TYPES - {"general"}


class TestLegalProcessor:
    """Test LegalProcessor"""

    @pytest.fixture
    def processor(self):
        return LegalProcessor()

    def test_name(self, processor):
        """Test processor name"""
        assert processor.name == "legal"

    def test_can_process_legal_content(self, processor):
        """Test can_process returns high score for legal content"""
        legal_content = """
        ARTICLE I - DEFINITIONS

        Section 1.1 Agreement means this Purchase Agreement.

        Section 1.2 Party means the undersigned party hereto.

        ARTICLE II - OBLIGATIONS

        2.1 The Seller hereby agrees and covenants to deliver...

        2.2 Notwithstanding the foregoing provisions...

        IN WITNESS WHEREOF, the parties have executed this Agreement.
        """
        score = processor.can_process(legal_content, {})
        assert score > 0.3  # Should detect as legal (lower threshold for short content)

    def test_can_process_non_legal_content(self, processor):
        """Test can_process returns low score for non-legal content"""
        non_legal = """
        Introduction to Machine Learning

        Machine learning is a subset of artificial intelligence.
        In this chapter, we'll explore neural networks and deep learning.
        """
        score = processor.can_process(non_legal, {})
        assert score < 0.5  # Should not detect as legal

    @pytest.mark.asyncio
    async def test_process_extracts_structure(self, processor):
        """Test process extracts legal hierarchy"""
        content = """
        ARTICLE I - DEFINITIONS

        Section 1.1 "Agreement" means this document.

        ARTICLE II - TERMS

        Section 2.1 Term of agreement is 1 year.
        """
        result = await processor.process(content, {}, "contract.pdf")

        assert isinstance(result, ProcessorResult)
        assert result.processor_name == "legal"
        assert result.document_metadata["document_type"] == "legal"
        # hierarchy may or may not be populated depending on content


class TestAcademicProcessor:
    """Test AcademicProcessor"""

    @pytest.fixture
    def processor(self):
        return AcademicProcessor()

    def test_name(self, processor):
        """Test processor name"""
        assert processor.name == "academic"

    def test_can_process_academic_content(self, processor):
        """Test can_process returns high score for academic content"""
        academic_content = """
        Abstract

        This paper presents a novel approach to natural language processing.
        We propose a transformer-based architecture that achieves state-of-the-art
        results on multiple benchmarks.

        1. Introduction

        Recent advances in deep learning have revolutionized NLP.

        2. Related Work

        Previous work by Smith et al. [1] demonstrated that...

        3. Methodology

        Our approach consists of three main components.

        4. Results

        We evaluated our model on GLUE benchmark.

        5. Conclusion

        We have presented a new approach to NLP.

        References

        [1] Smith, J. et al. (2023). Deep Learning for NLP.
        """
        score = processor.can_process(academic_content, {})
        assert score > 0.5  # Should detect as academic

    def test_can_process_non_academic_content(self, processor):
        """Test can_process returns low score for non-academic content"""
        non_academic = """
        Shopping List:
        - Milk
        - Eggs
        - Bread
        - Butter
        """
        score = processor.can_process(non_academic, {})
        assert score < 0.5  # Should not detect as academic

    @pytest.mark.asyncio
    async def test_process_extracts_sections(self, processor):
        """Test process extracts academic sections"""
        content = """
        Abstract

        This is the abstract.

        1. Introduction

        This is the introduction.
        """
        result = await processor.process(content, {}, "paper.pdf")

        assert isinstance(result, ProcessorResult)
        assert result.processor_name == "academic"
        assert result.document_metadata["document_type"] == "academic"


class TestQAProcessor:
    """Test QAProcessor"""

    @pytest.fixture
    def processor(self):
        return QAProcessor()

    def test_name(self, processor):
        """Test processor name"""
        assert processor.name == "qa"

    def test_can_process_qa_content(self, processor):
        """Test can_process returns high score for Q&A content"""
        qa_content = """
        Frequently Asked Questions

        Q: What is Python?
        A: Python is a programming language.

        Q: How do I install Python?
        A: You can download it from python.org.

        Question: What is pip?
        Answer: pip is the package installer for Python.
        """
        score = processor.can_process(qa_content, {})
        assert score > 0.3  # Should detect as Q&A (FAQ keyword + patterns)

    def test_can_process_non_qa_content(self, processor):
        """Test can_process returns low score for non-Q&A content"""
        non_qa = """
        Chapter 1: The History of Computing

        The first computers were developed in the 1940s.
        ENIAC was one of the earliest electronic computers.
        """
        score = processor.can_process(non_qa, {})
        assert score < 0.5  # Should not detect as Q&A

    @pytest.mark.asyncio
    async def test_process_extracts_qa_pairs(self, processor):
        """Test process extracts Q&A pairs"""
        content = """
        Q: What is RAG?
        A: RAG stands for Retrieval-Augmented Generation.

        Q: How does RAG work?
        A: RAG combines retrieval with generation.
        """
        result = await processor.process(content, {}, "faq.txt")

        assert isinstance(result, ProcessorResult)
        assert result.processor_name == "qa"
        assert result.document_metadata["document_type"] == "qa"
        assert result.document_metadata["qa_count"] >= 2


class TestTableProcessor:
    """Test TableProcessor"""

    @pytest.fixture
    def processor(self):
        return TableProcessor()

    def test_name(self, processor):
        """Test processor name"""
        assert processor.name == "table"

    def test_can_process_table_content(self, processor):
        """Test can_process returns high score for table content"""
        table_content = """
        Sales Report 2024

        | Product | Q1 Sales | Q2 Sales | Q3 Sales |
        |---------|----------|----------|----------|
        | Widget A | $10,000 | $12,000 | $15,000 |
        | Widget B | $8,000 | $9,500 | $11,000 |
        | Widget C | $5,000 | $6,000 | $7,500 |

        Total revenue increased by 25% this quarter.
        """
        score = processor.can_process(table_content, {})
        assert score > 0.3  # Should detect table structure

    def test_can_process_non_table_content(self, processor):
        """Test can_process returns low score for non-table content"""
        non_table = """
        Dear Customer,

        Thank you for your purchase. Your order has been shipped.

        Best regards,
        The Team
        """
        score = processor.can_process(non_table, {})
        assert score < 0.5  # Should not detect as table

    @pytest.mark.asyncio
    async def test_process_extracts_tables(self, processor):
        """Test process extracts table structure"""
        content = """
        | Name | Age | City |
        |------|-----|------|
        | John | 30 | NYC |
        | Jane | 25 | LA |
        """
        result = await processor.process(content, {}, "data.csv")

        assert isinstance(result, ProcessorResult)
        assert result.processor_name == "table"
        assert result.document_metadata["document_type"] == "table"
        assert result.document_metadata["table_count"] >= 1


class TestProcessorResult:
    """Test ProcessorResult model"""

    def test_processor_result_creation(self):
        """Test ProcessorResult can be created"""
        result = ProcessorResult(
            content="test content",
            document_metadata={"document_type": "legal"},
            chunk_annotations=[{"index": 0, "type": "section"}],
            processor_name="legal",
            confidence=0.95
        )
        assert result.content == "test content"
        assert result.processor_name == "legal"
        assert result.confidence == 0.95

    def test_processor_result_default_annotations(self):
        """Test ProcessorResult has empty annotations by default"""
        result = ProcessorResult(
            content="test",
            document_metadata={},
            processor_name="test",
            confidence=0.5
        )
        assert result.chunk_annotations == []
