"""
Comprehensive tests for RAGFlow-ported patterns.

Tests the ported patterns for:
- Q&A processor: question bullet patterns (qbullets_category)
- Academic processor: bullet patterns and hierarchy detection
- Table processor: cell classification, header detection, multi-level headers
- Vision module: ONNX table structure recognition (when available)
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch

from backend.processors.qa_processor import (
    QAProcessor,
    QUESTION_PATTERNS,
)
from backend.processors.academic_processor import (
    AcademicProcessor,
    BULLET_PATTERNS,
)
from backend.processors.table_processor import (
    TableProcessor,
    BLOCK_TYPE_PATTERNS,
    _classify_cell_type,
    _looks_like_header,
    _looks_like_data,
)
# Import RAGFlow utilities for testing
from backend.processors.ragflow_utils import (
    not_bullet,
    bullets_category,
    title_frequency,
    qbullets_category,
    index_int,
    BULLET_PATTERNS as BASE_BULLET_PATTERNS,
    QUESTION_PATTERNS as BASE_QUESTION_PATTERNS,
)


class TestQAProcessorPatterns:
    """Test Q&A processor question bullet patterns."""

    def test_question_patterns_exist(self):
        """Verify QUESTION_PATTERNS list is populated."""
        assert len(QUESTION_PATTERNS) >= 4
        # Should have QUESTION and numbered patterns
        assert any("QUESTION" in p or "[0-9]" in p for p in QUESTION_PATTERNS)

    def test_not_bullet_rejects_zero_start(self):
        """Lines starting with 0 are not question bullets."""
        assert not_bullet("0. Not a question")
        assert not_bullet("0123 test")

    def test_not_bullet_rejects_number_ranges(self):
        """Number ranges are not question bullets."""
        assert not_bullet("1 2-5 items")

    def test_not_bullet_rejects_ellipsis(self):
        """Ellipsis patterns are not question bullets."""
        assert not_bullet("1....")
        assert not_bullet("2...")

    def test_not_bullet_accepts_valid(self):
        """Valid question bullets pass the filter."""
        assert not not_bullet("Q1: What is Python?")
        assert not not_bullet("1. First question")

    def test_qbullets_category_finds_patterns(self):
        """Should detect question bullet category."""
        sections = [
            "1. What is Python?",
            "2. How does it work?",
            "3. Where to download?",
        ]
        best_idx, best_pattern = qbullets_category(sections)
        assert best_idx >= 0
        assert best_pattern

    def test_qbullets_category_no_match(self):
        """Should return -1 for non-question content."""
        sections = [
            "This is regular text.",
            "Another paragraph here.",
            "No questions at all.",
        ]
        best_idx, best_pattern = qbullets_category(sections)
        assert best_idx == -1
        assert best_pattern == ""

    def test_index_int_arabic(self):
        """Should convert Arabic numerals."""
        assert index_int("1") == 1
        assert index_int("10") == 10
        assert index_int("99") == 99

    def test_index_int_roman(self):
        """Should convert Roman numerals."""
        assert index_int("I") == 1
        assert index_int("V") == 5
        assert index_int("X") == 10
        assert index_int("III") == 3


class TestQAProcessorIntegration:
    """Test Q&A processor with RAGFlow patterns."""

    @pytest.fixture
    def processor(self):
        return QAProcessor()

    def test_can_process_numbered_questions(self, processor):
        """Should detect numbered question format."""
        content = """
        QUESTION ONE: What is machine learning?
        Machine learning is a subset of AI.

        QUESTION TWO: How does it work?
        It uses algorithms to learn patterns.

        QUESTION THREE: What are the applications?
        Many applications in various fields.
        """
        score = processor.can_process(content, {})
        assert score > 0.2

    def test_can_process_q_numbered(self, processor):
        """Should detect Q1/Q2/Q3 format."""
        content = """
        Q1: What is Python?
        Python is a programming language.

        Q2: Is Python easy to learn?
        Yes, Python has simple syntax.

        Q3: What can I build with Python?
        Web apps, data science, automation.
        """
        score = processor.can_process(content, {})
        assert score > 0.2

    @pytest.mark.asyncio
    async def test_process_extracts_bullet_qa(self, processor):
        """Should extract Q&A pairs using bullet detection."""
        content = """
        1. What is RAG?
        RAG stands for Retrieval-Augmented Generation.

        2. How does RAG work?
        RAG combines retrieval with generation.

        3. Why use RAG?
        RAG improves accuracy with external knowledge.
        """
        result = await processor.process(content, {}, "faq.txt")
        assert result.document_metadata["qa_count"] >= 1


class TestAcademicProcessorPatterns:
    """Test Academic processor bullet patterns."""

    def test_bullet_patterns_exist(self):
        """Verify BULLET_PATTERNS list is populated."""
        assert len(BULLET_PATTERNS) >= 3
        # Should have numeric, legal, and markdown patterns
        # BULLET_PATTERNS is a list of pattern sets (lists of regex strings)
        assert any(
            any("Section" in p or "[0-9]" in p or "#" in p for p in pattern_set)
            for pattern_set in BULLET_PATTERNS
        )

    def test_not_bullet_rejects_zero_start(self):
        """Lines starting with 0 are not bullets."""
        assert not_bullet("0.1 is not a bullet")
        assert not_bullet("0123 test")

    def test_not_bullet_rejects_number_ranges(self):
        """Number ranges are not bullets."""
        assert not_bullet("1 2-5 items")

    def test_not_bullet_rejects_ellipsis(self):
        """Ellipsis patterns are not bullets."""
        assert not_bullet("1....")
        assert not_bullet("2...")

    def test_not_bullet_accepts_valid(self):
        """Valid bullets pass the filter."""
        assert not not_bullet("1. Introduction")
        assert not not_bullet("1.1 Background")
        assert not not_bullet("Section 1")

    def test_bullets_category_numeric(self):
        """Should detect numeric pattern set."""
        sections = [
            "1. Introduction",
            "1.1 Background",
            "1.1.1 Context",
            "2. Methods",
        ]
        category = bullets_category(sections)
        assert category == 0  # NUMERIC_PATTERNS

    def test_bullets_category_english_legal(self):
        """Should detect English legal pattern set."""
        sections = [
            "PART ONE GENERAL PROVISIONS",
            "Chapter I Definitions",
            "Section 1 Purpose",
            "Article 1 Scope",
        ]
        category = bullets_category(sections)
        assert category == 1  # ENGLISH_LEGAL_PATTERNS

    def test_bullets_category_markdown(self):
        """Should detect markdown pattern set."""
        sections = [
            "# Main Title",
            "## Chapter 1",
            "### Section 1.1",
            "#### Subsection",
        ]
        category = bullets_category(sections)
        assert category == 2  # MARKDOWN_PATTERNS

    def test_title_frequency_detects_levels(self):
        """Should detect title frequency for hierarchy levels."""
        sections = [
            ("1. Introduction", ""),
            ("1.1 Background", ""),
            ("1.1.1 Context", ""),
            ("1.2 Motivation", ""),
            ("2. Methods", ""),
            ("2.1 Data", ""),
        ]
        max_level, level_counts = title_frequency(0, sections)
        assert max_level >= 0
        assert len(level_counts) > 0


class TestAcademicProcessorIntegration:
    """Test Academic processor with RAGFlow patterns."""

    @pytest.fixture
    def processor(self):
        return AcademicProcessor()

    def test_can_process_numbered_sections(self, processor):
        """Should detect numbered section format."""
        content = """
        1. INTRODUCTION

        1.1 Background
        This section provides background information.

        1.1.1 Historical Context
        The history of this field dates back...

        1.2 Motivation
        The motivation for this work is...

        2. METHODOLOGY

        2.1 Data Collection
        We collected data from multiple sources.
        """
        score = processor.can_process(content, {})
        assert score >= 0.1

    @pytest.mark.asyncio
    async def test_process_detects_hierarchy(self, processor):
        """Should detect hierarchical structure."""
        content = """
        # Introduction

        ## Background

        ### Historical Context

        ## Motivation

        # Methods

        ## Data Collection
        """
        result = await processor.process(content, {}, "paper.pdf")
        assert result.document_metadata["document_type"] == "academic"


class TestTableProcessorPatterns:
    """Test Table processor cell classification patterns."""

    def test_block_type_patterns_exist(self):
        """Verify BLOCK_TYPE_PATTERNS list is populated."""
        assert len(BLOCK_TYPE_PATTERNS) >= 5
        # Should have date, numeric, code patterns
        types = [p[1] for p in BLOCK_TYPE_PATTERNS]
        assert "date" in types
        assert "numeric" in types

    def test_classify_cell_type_empty(self):
        """Empty cells should be classified as empty."""
        assert _classify_cell_type("") == "empty"
        assert _classify_cell_type("   ") == "empty"

    def test_classify_cell_type_date(self):
        """Should classify date values."""
        assert _classify_cell_type("2024-01-15") == "date"
        assert _classify_cell_type("2024/01/15") == "date"
        assert _classify_cell_type("Q1 2024") == "date"

    def test_classify_cell_type_numeric(self):
        """Should classify numeric values."""
        assert _classify_cell_type("123") == "numeric"
        assert _classify_cell_type("12.34") == "numeric"
        assert _classify_cell_type("-456") == "numeric"
        assert _classify_cell_type("1,234.56") == "numeric"

    def test_classify_cell_type_code(self):
        """Should classify code/ID values."""
        assert _classify_cell_type("ABC-123") == "code"
        assert _classify_cell_type("ID_001") == "code"

    def test_classify_cell_type_text(self):
        """Should classify text values."""
        # Lowercase text with spaces matches text_en pattern
        assert _classify_cell_type("Hello world") == "text_en"
        assert _classify_cell_type("product description here") == "text_en"
        # Mixed case text that doesn't match specific patterns
        # but has enough words is classified as text
        mixed_text = "Product123 with Numbers456 and Symbols!@#"
        result = _classify_cell_type(mixed_text)
        # This text doesn't match text_en, numeric, date, or code patterns
        # so it should fall through to word count classification
        assert result in ("text", "long_text", "other")

    def test_looks_like_header_with_text(self):
        """Should identify header-like values."""
        assert _looks_like_header("Product Name")
        assert _looks_like_header("Date (UTC)")
        assert _looks_like_header("Price/Unit")

    def test_looks_like_header_rejects_empty(self):
        """Should reject empty values as headers."""
        assert not _looks_like_header("")

    def test_looks_like_data_numeric(self):
        """Should identify data-like numeric values."""
        assert _looks_like_data("123")
        assert _looks_like_data("12.34")
        assert _looks_like_data("-456")

    def test_looks_like_data_single_char(self):
        """Should identify single character codes as data."""
        assert _looks_like_data("Y")
        assert _looks_like_data("N")
        assert _looks_like_data("-")


class TestTableProcessorIntegration:
    """Test Table processor with RAGFlow patterns."""

    @pytest.fixture
    def processor(self):
        return TableProcessor(use_onnx=False)

    def test_init_without_onnx(self, processor):
        """Should initialize without ONNX."""
        assert not processor._onnx_enabled
        assert processor._recognizer is None

    def test_can_process_markdown_table(self, processor):
        """Should detect markdown table format."""
        content = """
        | Name | Age | City |
        |------|-----|------|
        | John | 30  | NYC  |
        | Jane | 25  | LA   |
        | Bob  | 35  | SF   |
        """
        score = processor.can_process(content, {})
        assert score > 0.3

    @pytest.mark.asyncio
    async def test_process_extracts_headers(self, processor):
        """Should extract table headers correctly."""
        content = """
        | Product | Price | Stock |
        |---------|-------|-------|
        | Widget  | $10   | 100   |
        | Gadget  | $20   | 50    |
        """
        result = await processor.process(content, {}, "data.csv")

        assert result.document_metadata["table_count"] >= 1
        tables = result.document_metadata["tables"]
        assert len(tables) >= 1
        assert "Product" in tables[0]["headers"]

    @pytest.mark.asyncio
    async def test_process_detects_column_types(self, processor):
        """Should detect column types from data."""
        content = """
        | Date       | Amount  | Status |
        |------------|---------|--------|
        | 2024-01-01 | $100.00 | Active |
        | 2024-01-02 | $200.00 | Active |
        """
        result = await processor.process(content, {}, "report.csv")

        tables = result.document_metadata["tables"]
        assert len(tables) >= 1
        column_types = tables[0]["column_types"]
        # Date column should be detected as date
        assert "Date" in column_types

    @pytest.mark.asyncio
    async def test_process_multi_level_headers(self, processor):
        """Should handle tables with multi-level headers."""
        content = """
        | Category | Q1 Sales | Q2 Sales |
        | Type     | Jan-Mar  | Apr-Jun  |
        |----------|----------|----------|
        | A        | 1000     | 1200     |
        | B        | 800      | 950      |
        """
        result = await processor.process(content, {}, "sales.csv")
        assert result.document_metadata["table_count"] >= 1

    def test_onnx_available_property(self, processor):
        """Should report ONNX availability."""
        assert not processor.onnx_available

    def test_process_table_image_without_onnx(self, processor):
        """Should return empty result when ONNX not available."""
        dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
        result = processor.process_table_image(dummy_image)
        assert result["rows"] == []
        assert result["columns"] == []


class TestVisionModule:
    """Test vision module availability and basic functionality."""

    def test_import_vision_module(self):
        """Should be able to import vision module."""
        try:
            from backend.vision import ONNX_AVAILABLE
            # Should not raise ImportError
            assert isinstance(ONNX_AVAILABLE, bool)
        except ImportError:
            pytest.skip("Vision module not available")

    def test_table_structure_recognizer_import(self):
        """Should be able to import TableStructureRecognizer."""
        try:
            from backend.vision import TableStructureRecognizer
            assert TableStructureRecognizer is not None
        except ImportError:
            pytest.skip("TableStructureRecognizer not available")

    def test_recognizer_labels(self):
        """Should have correct labels for table structure."""
        try:
            from backend.vision import TableStructureRecognizer
            recognizer = TableStructureRecognizer.__new__(TableStructureRecognizer)
            expected_labels = [
                "table",
                "table column",
                "table row",
                "table column header",
                "table projected row header",
                "table spanning cell",
            ]
            assert recognizer.labels == expected_labels
        except ImportError:
            pytest.skip("TableStructureRecognizer not available")


class TestONNXRecognizer:
    """Test ONNX recognizer functionality (if available)."""

    @pytest.fixture
    def mock_onnx_session(self):
        """Create mock ONNX session."""
        session = MagicMock()
        session.get_inputs.return_value = [MagicMock(name="image")]
        session.get_outputs.return_value = [
            MagicMock(name="boxes"),
            MagicMock(name="scores"),
            MagicMock(name="labels"),
        ]
        return session

    def test_base_recognizer_sort_y_firstly(self):
        """Test sort_Y_firstly static method."""
        try:
            from backend.vision.recognizer import Recognizer

            boxes = [
                {"top": 100, "x0": 50},
                {"top": 10, "x0": 100},
                {"top": 10, "x0": 50},
                {"top": 100, "x0": 100},
            ]
            sorted_boxes = Recognizer.sort_Y_firstly(boxes, threshold=5)

            # First should be boxes with top=10
            assert sorted_boxes[0]["top"] == 10
            assert sorted_boxes[1]["top"] == 10
            # Sorted by x0 within same row
            assert sorted_boxes[0]["x0"] == 50
            assert sorted_boxes[1]["x0"] == 100
        except ImportError:
            pytest.skip("Recognizer not available")

    def test_base_recognizer_sort_x_firstly(self):
        """Test sort_X_firstly static method."""
        try:
            from backend.vision.recognizer import Recognizer

            boxes = [
                {"x0": 100, "top": 50},
                {"x0": 10, "top": 100},
                {"x0": 10, "top": 50},
                {"x0": 100, "top": 100},
            ]
            sorted_boxes = Recognizer.sort_X_firstly(boxes, threshold=5)

            # First should be boxes with x0=10
            assert sorted_boxes[0]["x0"] == 10
            assert sorted_boxes[1]["x0"] == 10
            # Sorted by top within same column
            assert sorted_boxes[0]["top"] == 50
            assert sorted_boxes[1]["top"] == 100
        except ImportError:
            pytest.skip("Recognizer not available")


class TestTableConstructor:
    """Test table construction from detected structure."""

    def test_construct_table_empty(self):
        """Should handle empty input."""
        try:
            from backend.vision import TableStructureRecognizer
            result = TableStructureRecognizer.construct_table([])
            assert result == ""
        except ImportError:
            pytest.skip("TableStructureRecognizer not available")

    def test_construct_table_html(self):
        """Should construct HTML table from boxes."""
        try:
            from backend.vision import TableStructureRecognizer

            boxes = [
                {"text": "Header 1", "top": 0, "bottom": 20, "x0": 0, "x1": 50},
                {"text": "Header 2", "top": 0, "bottom": 20, "x0": 50, "x1": 100},
                {"text": "Data 1", "top": 25, "bottom": 45, "x0": 0, "x1": 50},
                {"text": "Data 2", "top": 25, "bottom": 45, "x0": 50, "x1": 100},
            ]
            result = TableStructureRecognizer.construct_table(boxes, as_html=True)
            assert "<table>" in result
            assert "</table>" in result
            assert "Header 1" in result
        except ImportError:
            pytest.skip("TableStructureRecognizer not available")

    def test_construct_table_text(self):
        """Should construct text table from boxes."""
        try:
            from backend.vision import TableStructureRecognizer

            boxes = [
                {"text": "A", "top": 0, "bottom": 20, "x0": 0, "x1": 50},
                {"text": "B", "top": 0, "bottom": 20, "x0": 50, "x1": 100},
                {"text": "1", "top": 25, "bottom": 45, "x0": 0, "x1": 50},
                {"text": "2", "top": 25, "bottom": 45, "x0": 50, "x1": 100},
            ]
            result = TableStructureRecognizer.construct_table(
                boxes, as_html=False, is_english=True
            )
            assert " | " in result
        except ImportError:
            pytest.skip("TableStructureRecognizer not available")

    def test_is_caption_detection(self):
        """Should detect table captions."""
        try:
            from backend.vision import TableStructureRecognizer

            caption_box = {"text": "Table 1: Sales Data", "layout_type": ""}
            assert TableStructureRecognizer.is_caption(caption_box)

            regular_box = {"text": "Regular data here", "layout_type": ""}
            assert not TableStructureRecognizer.is_caption(regular_box)
        except ImportError:
            pytest.skip("TableStructureRecognizer not available")
