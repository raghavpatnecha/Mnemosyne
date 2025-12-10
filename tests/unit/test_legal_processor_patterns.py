"""
Comprehensive tests for LegalProcessor pattern matching.

Tests the RAGFlow-ported patterns for:
- English legal documents (Part/Chapter/Section/Article)
- Multi-level numbering (1.1, 1.1.1, 1.1.1.1)
- Roman numerals (I, II, III, IV, V)
- Definitions extraction
"""

import pytest
from backend.processors.legal_processor import LegalProcessor
from backend.processors.ragflow_utils import (
    BULLET_PATTERNS,
    bullets_category,
    not_bullet,
    not_title,
)


class TestNotBulletFilter:
    """Test false positive filtering for bullet detection."""

    def test_rejects_lines_starting_with_zero(self):
        """Lines starting with 0 are not bullets."""
        assert not_bullet("0.1 is not a bullet")
        assert not_bullet("0123 test")

    def test_rejects_number_ranges(self):
        """Number ranges like '1 2-5' are not bullets."""
        assert not_bullet("1 2-5 items")
        assert not_bullet("3 4~6 pieces")

    def test_rejects_ellipsis_patterns(self):
        """Ellipsis patterns like '1.....' are not bullets."""
        assert not_bullet("1....")
        assert not_bullet("2...")

    def test_accepts_valid_bullets(self):
        """Valid bullets should pass the filter."""
        assert not not_bullet("1. Introduction")
        assert not not_bullet("Section 1")


class TestNotTitleFilter:
    """Test title validation filtering."""

    def test_rejects_long_lines(self):
        """Lines with >12 words are not titles."""
        long_line = "This is a very long line with more than twelve words in it that should not be a title"
        assert not_title(long_line)

    def test_rejects_long_no_space(self):
        """Lines >=32 chars without spaces are not titles."""
        long_no_space = "Thisisaveryverylongwordwithoutspaces"
        assert not_title(long_no_space)

    def test_rejects_punctuated_lines(self):
        """Lines with sentence-ending punctuation are not titles."""
        assert not_title("This is a sentence, with comma.")
        assert not_title("Question here?")
        assert not_title("Exclamation here!")

    def test_accepts_valid_titles(self):
        """Valid titles should pass the filter."""
        assert not not_title("DEFINITIONS")
        assert not not_title("Article 1")
        assert not not_title("Chapter One")


class TestBulletCategoryDetection:
    """Test automatic bullet pattern set detection."""

    def test_detects_numeric_patterns(self):
        """Should detect numeric pattern set (index 0)."""
        sections = [
            "1. Introduction",
            "1.1 Background",
            "1.1.1 Context",
            "1.1.1.1 Details",
            "2. Methods",
        ]
        category = bullets_category(sections)
        assert category == 0  # NUMERIC_PATTERNS

    def test_detects_english_legal_patterns(self):
        """Should detect English legal pattern set (index 1)."""
        sections = [
            "PART ONE GENERAL PROVISIONS",
            "CHAPTER I Definitions",
            "Section 1. Purpose",
            "Article 1. Scope",
            "Article 2. Definitions",
        ]
        category = bullets_category(sections)
        assert category == 1  # ENGLISH_LEGAL_PATTERNS

    def test_detects_markdown_patterns(self):
        """Should detect markdown pattern set (index 2)."""
        sections = [
            "# Main Title",
            "## Chapter 1",
            "### Section 1.1",
            "#### Subsection",
            "##### Detail",
        ]
        category = bullets_category(sections)
        assert category == 2  # MARKDOWN_PATTERNS


class TestEnglishLegalDocument:
    """Test processing of English legal documents."""

    @pytest.fixture
    def processor(self):
        return LegalProcessor()

    @pytest.fixture
    def english_contract(self):
        return """
PURCHASE AGREEMENT

PART ONE: GENERAL PROVISIONS

CHAPTER I: DEFINITIONS

Section 1. Purpose

WHEREAS, the Seller desires to sell and the Buyer desires to purchase the Property;

NOW, THEREFORE, in consideration of the mutual covenants herein, the parties agree:

Article 1. Definitions

"Agreement" means this Purchase Agreement and all attachments hereto.

"Buyer" means the party acquiring the Property.

"Seller" means the party conveying the Property.

Article 2. Purchase Price

The purchase price shall be as set forth in Schedule A.

CHAPTER II: OBLIGATIONS

Section 2. Seller's Obligations

2.1 The Seller shall deliver the Property free of liens.
2.2 The Seller warrants good title.
2.2.1 Title insurance shall be provided.
2.2.2 Survey shall be current.

Section 3. Buyer's Obligations

3.1 The Buyer shall pay the purchase price.
3.1.1 Payment shall be made at closing.
3.1.2 Funds shall be certified.

IN WITNESS WHEREOF, the parties have executed this Agreement.
"""

    def test_can_process_english_legal(self, processor, english_contract):
        """Should detect English legal document."""
        score = processor.can_process(english_contract, {})
        assert score > 0.4

    @pytest.mark.asyncio
    async def test_process_extracts_english_structure(self, processor, english_contract):
        """Should extract hierarchical structure from English legal document."""
        result = await processor.process(english_contract, {}, "contract.pdf")

        assert result.document_metadata["document_type"] == "legal"
        assert result.document_metadata["subtype"] == "contract"

        structure = result.document_metadata["structure"]
        assert len(structure) > 0

    @pytest.mark.asyncio
    async def test_process_extracts_definitions(self, processor, english_contract):
        """Should extract definitions from English legal document."""
        result = await processor.process(english_contract, {}, "contract.pdf")

        definitions = result.document_metadata["definitions"]
        assert result.document_metadata["has_definitions"]

        # Check if some definitions were extracted
        terms = [d["term"] for d in definitions]
        assert any("Agreement" in t or "Buyer" in t or "Seller" in t for t in terms)


class TestMultiLevelNumbering:
    """Test multi-level decimal numbering patterns."""

    @pytest.fixture
    def processor(self):
        return LegalProcessor()

    @pytest.fixture
    def numbered_document(self):
        return """
TECHNICAL SPECIFICATIONS

1. GENERAL REQUIREMENTS

1.1 Scope of Work
1.1.1 This specification covers...
1.1.1.1 Including all subsystems
1.1.1.2 And all interfaces

1.2 Standards and Codes
1.2.1 All work shall comply with:
1.2.1.1 Local building codes
1.2.1.2 Industry standards

2. TECHNICAL REQUIREMENTS

2.1 Performance Standards
2.1.1 System Availability
2.1.1.1 Target: 99.9%
2.1.2 Response Time
2.1.2.1 Maximum: 500ms

3. TESTING REQUIREMENTS

3.1 Unit Testing
3.2 Integration Testing
3.3 System Testing
"""

    def test_can_process_numbered_document(self, processor, numbered_document):
        """Should detect numbered document."""
        score = processor.can_process(numbered_document, {})
        # Score may be lower but should still process
        assert score >= 0.1

    @pytest.mark.asyncio
    async def test_process_extracts_numbering_hierarchy(
        self, processor, numbered_document
    ):
        """Should extract multi-level numbering hierarchy."""
        result = await processor.process(numbered_document, {}, "spec.pdf")

        structure = result.document_metadata["structure"]
        assert len(structure) > 0

        # Check for different levels
        level_indices = {item["level_idx"] for item in structure}
        assert len(level_indices) > 1  # Multiple levels detected


class TestRomanNumerals:
    """Test Roman numeral pattern detection."""

    @pytest.fixture
    def processor(self):
        return LegalProcessor()

    @pytest.fixture
    def roman_document(self):
        return """
BYLAWS OF XYZ CORPORATION

CHAPTER I - NAME AND OFFICES

Section 1.1 The name of this corporation shall be XYZ Corporation.

CHAPTER II - MEMBERS

Section 2.1 Classes of Members
Section 2.2 Voting Rights

CHAPTER III - BOARD OF DIRECTORS

Section 3.1 Powers
Section 3.2 Number and Qualification

CHAPTER IV - OFFICERS

Section 4.1 Number
Section 4.2 Election and Term

CHAPTER V - AMENDMENTS

Section 5.1 These Bylaws may be amended by the Board.
"""

    def test_can_process_roman_numerals(self, processor, roman_document):
        """Should detect document with Roman numerals."""
        score = processor.can_process(roman_document, {})
        assert score > 0.2

    @pytest.mark.asyncio
    async def test_process_extracts_roman_structure(self, processor, roman_document):
        """Should extract Roman numeral chapters."""
        result = await processor.process(roman_document, {}, "bylaws.pdf")

        structure = result.document_metadata["structure"]
        assert len(structure) > 0

        # Check for chapter detection
        chapters = [s for s in structure if "chapter" in s.get("level", "").lower()]
        assert len(chapters) > 0


class TestDefinitionsExtraction:
    """Test definitions section extraction."""

    @pytest.fixture
    def processor(self):
        return LegalProcessor()

    def test_extracts_quoted_definitions(self, processor):
        """Should extract definitions with quoted terms."""
        content = '''
DEFINITIONS

"Agreement" means this Master Service Agreement.
"Confidential Information" means any information marked as confidential.
"Services" means the services described in Schedule A.

ARTICLE 1. SERVICES
'''
        # Manually test definition extraction
        definitions = processor._extract_definitions(content)
        assert len(definitions) > 0

        terms = [d["term"] for d in definitions]
        assert "Agreement" in terms or "Confidential Information" in terms


class TestDocumentSubtypeDetection:
    """Test document subtype detection."""

    @pytest.fixture
    def processor(self):
        return LegalProcessor()

    def test_detects_contract(self, processor):
        """Should detect contract subtype."""
        content = "WHEREAS the parties agree... NOW THEREFORE in consideration..."
        subtype = processor._detect_subtype(content, "agreement.pdf")
        assert subtype == "contract"

    def test_detects_legislation(self, processor):
        """Should detect legislation subtype."""
        content = "This Act may be cited as the Data Protection Act enacted by Parliament..."
        subtype = processor._detect_subtype(content, "law.pdf")
        assert subtype == "legislation"

    def test_detects_policy(self, processor):
        """Should detect policy subtype."""
        content = "Privacy Policy: This privacy policy describes how we collect and use your information..."
        subtype = processor._detect_subtype(content, "privacy.pdf")
        assert subtype == "policy"

    def test_detects_court_document(self, processor):
        """Should detect court document subtype."""
        content = "The plaintiff alleges that the defendant... The court hereby orders judgment..."
        subtype = processor._detect_subtype(content, "case.pdf")
        assert subtype == "court"


class TestChunkAnnotations:
    """Test chunk annotation generation."""

    @pytest.fixture
    def processor(self):
        return LegalProcessor()

    @pytest.mark.asyncio
    async def test_generates_annotations(self, processor):
        """Should generate chunk annotations for legal sections."""
        content = """
Section 1. Introduction

This section provides an overview.

Section 2. Scope

This section defines the scope.

Section 3. Definitions

Key terms are defined here.
"""
        result = await processor.process(content, {}, "doc.pdf")

        annotations = result.chunk_annotations
        assert len(annotations) > 0

        # Check annotation structure
        for ann in annotations:
            assert "start" in ann
            assert "end" in ann
            assert "type" in ann
            assert ann["type"] == "legal_section"
            assert "preserve_boundary" in ann
