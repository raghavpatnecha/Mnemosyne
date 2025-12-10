"""
Academic Paper Processor.

Extracts structure from academic/research papers including:
- Title, authors, abstract
- Standard sections (Introduction, Methods, Results, Discussion, References)
- Citations and references
- Hierarchical structure detection

Ported from RAGFlow's paper.py processor with production-tested patterns.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.processors.base import DomainProcessor, ProcessorResult
from backend.processors.ragflow_utils import (
    BULLET_PATTERNS as BASE_BULLET_PATTERNS,
    bullets_category,
    not_bullet,
    not_title,
    title_frequency,
    tree_merge,
    Node,
)

logger = logging.getLogger(__name__)


# Combined bullet patterns: Base + Academic-specific
# Extends RAGFlow's BULLET_PATTERNS with academic patterns
BULLET_PATTERNS = BASE_BULLET_PATTERNS + [
    # Pattern Set: Academic section patterns
    [
        r"^\d+\.?\s*(ABSTRACT|INTRODUCTION|METHODS?|RESULTS?|DISCUSSION|CONCLUSIONS?)",
        r"^(ABSTRACT|INTRODUCTION|METHODS?|RESULTS?|DISCUSSION|CONCLUSIONS?)\s*$",
        r"^\d+\.\d+\.?\s+[A-Z]",  # 1.1 Subsection
    ],
]


class AcademicProcessor(DomainProcessor):
    """Processor for academic papers and research documents.

    Extracts structure from scientific papers, journal articles,
    conference papers, and other academic publications.
    """

    name = "academic"
    supported_content_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]

    # Standard academic section patterns
    SECTION_PATTERNS = [
        # Numbered sections
        r"^(\d+\.?\s*)(ABSTRACT|Abstract)\s*$",
        r"^(\d+\.?\s*)(INTRODUCTION|Introduction)\s*$",
        r"^(\d+\.?\s*)(BACKGROUND|Background)\s*$",
        r"^(\d+\.?\s*)(RELATED\s+WORK|Related\s+Work)\s*$",
        r"^(\d+\.?\s*)(LITERATURE\s+REVIEW|Literature\s+Review)\s*$",
        r"^(\d+\.?\s*)(METHODS?|Methods?|METHODOLOGY|Methodology)\s*$",
        r"^(\d+\.?\s*)(MATERIALS?\s+AND\s+METHODS?|Materials?\s+and\s+Methods?)\s*$",
        r"^(\d+\.?\s*)(EXPERIMENTAL?\s+SETUP?|Experimental?\s+Setup?)\s*$",
        r"^(\d+\.?\s*)(RESULTS?|Results?)\s*$",
        r"^(\d+\.?\s*)(RESULTS?\s+AND\s+DISCUSSION|Results?\s+and\s+Discussion)\s*$",
        r"^(\d+\.?\s*)(DISCUSSION|Discussion)\s*$",
        r"^(\d+\.?\s*)(ANALYSIS|Analysis)\s*$",
        r"^(\d+\.?\s*)(CONCLUSIONS?|Conclusions?)\s*$",
        r"^(\d+\.?\s*)(SUMMARY|Summary)\s*$",
        r"^(\d+\.?\s*)(FUTURE\s+WORK|Future\s+Work)\s*$",
        r"^(\d+\.?\s*)(ACKNOWLEDGM?ENTS?|Acknowledgm?ents?)\s*$",
        r"^(\d+\.?\s*)(REFERENCES?|References?|BIBLIOGRAPHY|Bibliography)\s*$",
        r"^(\d+\.?\s*)(APPENDIX|Appendix|APPENDICES|Appendices)\s*$",
        # Unnumbered sections
        r"^(ABSTRACT|Abstract)\s*$",
        r"^(INTRODUCTION|Introduction)\s*$",
        r"^(METHODS?|Methods?|METHODOLOGY|Methodology)\s*$",
        r"^(RESULTS?|Results?)\s*$",
        r"^(DISCUSSION|Discussion)\s*$",
        r"^(CONCLUSIONS?|Conclusions?)\s*$",
        r"^(REFERENCES?|References?)\s*$",
    ]

    # Academic paper indicators
    ACADEMIC_INDICATORS = [
        r"\b(?:abstract|introduction|methodology|results|conclusion|references)\b",
        r"\b(?:hypothesis|experiment|analysis|findings|study|research)\b",
        r"\b(?:et\s+al\.?|ibid\.?|op\.?\s*cit\.?)\b",
        r"\b(?:fig(?:ure)?\.?\s*\d|table\s*\d)\b",
        r"\[\d+\]",  # Citation markers [1], [2], etc.
        r"\(\w+(?:\s+et\s+al\.?)?,?\s*\d{4}\)",  # Author-year citations
        r"\b(?:peer[- ]review|journal|conference|proceedings)\b",
        r"\b(?:doi|issn|isbn)\s*:?\s*[\d\-./]+",
        r"\b(?:university|institute|department|faculty)\b",
    ]

    # Keywords section patterns
    KEYWORDS_PATTERNS = [
        r"^(?:Keywords?|KEY\s*WORDS?|Index\s+Terms?)\s*[:\-]?\s*(.+)$",
    ]

    async def process(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> ProcessorResult:
        """Process academic paper and extract structure.

        Uses RAGFlow-ported bullet detection for hierarchical structure.

        Args:
            content: Document text content
            metadata: User-provided metadata
            filename: Original filename

        Returns:
            ProcessorResult with extracted academic structure
        """
        logger.debug("Processing academic paper: %s", filename)

        # Extract title (usually first substantial line)
        title = self._extract_title(content)

        # Extract authors
        authors = self._extract_authors(content)

        # Extract abstract
        abstract = self._extract_abstract(content)

        # Extract keywords
        keywords = self._extract_keywords(content)

        # Extract sections using pattern detection
        sections = self._extract_sections(content)

        # Detect hierarchical structure using RAGFlow patterns
        hierarchy = self._detect_hierarchy(content)

        # Extract references
        references = self._extract_references(content)

        # Count citations in text
        citation_count = self._count_citations(content)

        # Generate chunk annotations
        chunk_annotations = self._generate_chunk_annotations(sections, content)

        document_metadata = {
            "document_type": "academic",
            "title": title,
            "authors": authors,
            "abstract": abstract[:1000] if abstract else None,  # Truncate for storage
            "keywords": keywords,
            "sections": [s["name"] for s in sections],
            "section_count": len(sections),
            "reference_count": len(references),
            "citation_count": citation_count,
            "has_abstract": bool(abstract),
            "hierarchy": hierarchy,
            "bullet_category": hierarchy.get("category", -1) if hierarchy else -1,
        }

        return ProcessorResult(
            content=content,
            document_metadata=document_metadata,
            chunk_annotations=chunk_annotations,
            processor_name=self.name,
            confidence=0.85,
        )

    def _detect_hierarchy(self, content: str) -> Dict[str, Any]:
        """Detect hierarchical document structure using RAGFlow patterns.

        Uses RAGFlow's bullets_category() and title_frequency() for detection,
        and tree_merge() for hierarchical chunking.

        Args:
            content: Document content

        Returns:
            Dictionary with hierarchy information
        """
        lines = content.split("\n")
        sections = [line.strip() for line in lines if line.strip()]

        # Detect bullet category using RAGFlow's algorithm
        category = bullets_category(sections)

        if category < 0:
            return {"category": -1, "levels": [], "structure": [], "chunks": []}

        # Get hierarchy levels using RAGFlow's title_frequency
        section_tuples = [(s, "") for s in sections]
        most_level, levels = title_frequency(category, section_tuples)

        # Build structure with level information
        structure = []
        for i, (section, level) in enumerate(zip(sections, levels)):
            if category < len(BULLET_PATTERNS) and level < len(BULLET_PATTERNS[category]):
                structure.append({
                    "text": section[:200],  # Truncate for storage
                    "level": level,
                    "index": i,
                })

        # Use tree_merge for hierarchical chunking (RAGFlow's core algorithm)
        # depth=2 means merge up to 2 levels of hierarchy
        merged_chunks = tree_merge(category, section_tuples, depth=2)

        return {
            "category": category,
            "category_name": self._get_category_name(category),
            "most_common_level": most_level,
            "structure": structure[:50],  # Limit to first 50 structural elements
            "chunks": merged_chunks[:100],  # Hierarchical chunks for better retrieval
        }

    def _get_category_name(self, category: int) -> str:
        """Get human-readable name for bullet category.

        Args:
            category: Category index

        Returns:
            Category name string
        """
        names = ["numeric", "legal_formal", "markdown", "academic"]
        return names[category] if 0 <= category < len(names) else "unknown"

    def can_process(self, content: str, metadata: Dict[str, Any]) -> float:
        """Determine if this processor can handle the document.

        Args:
            content: Document text content
            metadata: User-provided metadata

        Returns:
            Confidence score (0-1)
        """
        if not content:
            return 0.0

        sample = content[:8000].lower()
        score = 0.0

        # Check for academic indicators
        for pattern in self.ACADEMIC_INDICATORS:
            matches = len(re.findall(pattern, sample, re.IGNORECASE))
            score += min(matches * 0.05, 0.2)

        # Check for standard sections
        lines = content[:15000].split("\n")
        section_matches = 0
        for line in lines:
            line = line.strip()
            for pattern in self.SECTION_PATTERNS:
                if re.match(pattern, line, re.IGNORECASE):
                    section_matches += 1
                    break

        score += min(section_matches * 0.1, 0.4)

        # Check for citations
        citation_patterns = [r"\[\d+\]", r"\(\w+,?\s*\d{4}\)"]
        for pattern in citation_patterns:
            matches = len(re.findall(pattern, sample))
            score += min(matches * 0.02, 0.15)

        # Check filename for academic indicators
        if filename := metadata.get("filename", ""):
            academic_filename_patterns = [
                r"paper",
                r"article",
                r"research",
                r"thesis",
                r"dissertation",
                r"journal",
                r"arxiv",
            ]
            for pattern in academic_filename_patterns:
                if re.search(pattern, filename.lower()):
                    score += 0.15
                    break

        return min(score, 1.0)

    def _extract_title(self, content: str) -> Optional[str]:
        """Extract paper title.

        Heuristic: First substantial line that's not all caps and metadata.

        Args:
            content: Document content

        Returns:
            Extracted title or None
        """
        lines = content.split("\n")

        for line in lines[:20]:  # Check first 20 lines
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            # Skip likely metadata lines
            skip_patterns = [
                r"^\d+$",  # Page numbers
                r"^(?:arxiv|doi|issn|isbn)",
                r"^(?:submitted|accepted|published|received)",
                r"^(?:volume|issue|pages?)",
                r"^[A-Z]{2,}\s*\d+",  # Conference IDs
            ]
            if any(re.match(p, line, re.IGNORECASE) for p in skip_patterns):
                continue

            # Title should be substantial (at least 3 words)
            words = line.split()
            if len(words) >= 3 and len(line) > 20:
                # Clean up title
                title = line.strip()
                # Remove trailing punctuation except question marks
                title = re.sub(r"[.;,]+$", "", title)
                return title

        return None

    def _extract_authors(self, content: str) -> List[str]:
        """Extract author names.

        Args:
            content: Document content

        Returns:
            List of author names
        """
        authors = []
        lines = content.split("\n")

        # Look for author line(s) after title, before abstract
        in_author_region = False
        author_region_end = False

        for i, line in enumerate(lines[:50]):
            line = line.strip()

            # Start looking after finding title (substantial line)
            if not in_author_region:
                if len(line.split()) >= 3 and len(line) > 20:
                    in_author_region = True
                continue

            # Stop at abstract or section headers
            if re.match(r"^(?:abstract|introduction|keywords)", line, re.IGNORECASE):
                break

            # Skip empty lines and email/affiliation lines
            if not line or "@" in line or re.match(r"^\d", line):
                continue

            # Look for author patterns
            # Pattern 1: Names separated by commas or "and"
            if re.search(r"(?:,\s*|\s+and\s+)", line) and len(line) < 200:
                # Check if line contains names (capitalized words)
                potential_names = re.findall(r"[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", line)
                if potential_names:
                    authors.extend(potential_names)
                    continue

            # Pattern 2: Single author per line
            if re.match(r"^[A-Z][a-z]+(?:\s+[A-Z]\.?\s*)*[A-Z][a-z]+$", line):
                authors.append(line)

        # Deduplicate while preserving order
        seen = set()
        unique_authors = []
        for author in authors:
            if author not in seen:
                seen.add(author)
                unique_authors.append(author)

        return unique_authors[:10]  # Limit to 10 authors

    def _extract_abstract(self, content: str) -> Optional[str]:
        """Extract abstract section.

        Args:
            content: Document content

        Returns:
            Abstract text or None
        """
        # Find abstract section
        abstract_start_patterns = [
            r"^(?:\d+\.?\s*)?(?:ABSTRACT|Abstract)\s*$",
            r"^(?:ABSTRACT|Abstract)\s*[:\-]\s*",
        ]

        abstract_end_patterns = [
            r"^(?:\d+\.?\s*)?(?:INTRODUCTION|Introduction|KEYWORDS?|Keywords?|INDEX\s+TERMS?)",
            r"^(?:1\.?\s*(?:INTRODUCTION|Introduction))",
        ]

        lines = content.split("\n")
        abstract_lines = []
        in_abstract = False

        for line in lines[:100]:  # Abstract should be in first 100 lines
            line_stripped = line.strip()

            # Check for abstract start
            if not in_abstract:
                for pattern in abstract_start_patterns:
                    if re.match(pattern, line_stripped, re.IGNORECASE):
                        in_abstract = True
                        # Check if abstract text is on same line
                        remainder = re.sub(pattern, "", line_stripped, flags=re.IGNORECASE).strip()
                        if remainder:
                            abstract_lines.append(remainder)
                        break
                continue

            # Check for abstract end
            for pattern in abstract_end_patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    in_abstract = False
                    break

            if not in_abstract:
                break

            # Collect abstract lines
            if line_stripped:
                abstract_lines.append(line_stripped)

        if abstract_lines:
            return " ".join(abstract_lines)

        return None

    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords.

        Args:
            content: Document content

        Returns:
            List of keywords
        """
        lines = content.split("\n")

        for line in lines[:100]:
            line = line.strip()
            for pattern in self.KEYWORDS_PATTERNS:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    keywords_text = match.group(1)
                    # Split by common delimiters
                    keywords = re.split(r"[;,·•]", keywords_text)
                    keywords = [k.strip() for k in keywords if k.strip()]
                    return keywords[:15]  # Limit to 15 keywords

        return []

    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract paper sections.

        Args:
            content: Document content

        Returns:
            List of section dictionaries
        """
        sections = []
        lines = content.split("\n")
        current_position = 0

        for line_num, line in enumerate(lines):
            line_stripped = line.strip()

            for pattern in self.SECTION_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    # Handle numbered vs unnumbered sections
                    if len(groups) >= 2:
                        number = groups[0].strip()
                        name = groups[1].strip()
                    else:
                        number = ""
                        name = groups[0].strip() if groups else line_stripped

                    sections.append(
                        {
                            "number": number,
                            "name": name,
                            "line_number": line_num,
                            "position": current_position,
                        }
                    )
                    break

            current_position += len(line) + 1

        return sections

    def _extract_references(self, content: str) -> List[str]:
        """Extract references section entries.

        Args:
            content: Document content

        Returns:
            List of reference strings
        """
        references = []

        # Find references section
        ref_start_patterns = [
            r"^(?:\d+\.?\s*)?(?:REFERENCES?|References?|BIBLIOGRAPHY|Bibliography)\s*$",
        ]

        lines = content.split("\n")
        in_references = False

        for line in lines:
            line_stripped = line.strip()

            if not in_references:
                for pattern in ref_start_patterns:
                    if re.match(pattern, line_stripped, re.IGNORECASE):
                        in_references = True
                        break
                continue

            # Skip empty lines
            if not line_stripped:
                continue

            # Stop at appendix or end of document markers
            if re.match(r"^(?:APPENDIX|Appendix)", line_stripped):
                break

            # Reference patterns
            ref_patterns = [
                r"^\[\d+\]",  # [1] Author...
                r"^\d+\.",  # 1. Author...
                r"^[A-Z][a-z]+,?\s+[A-Z]\.",  # Author, A. ...
            ]

            for pattern in ref_patterns:
                if re.match(pattern, line_stripped):
                    references.append(line_stripped)
                    break

        return references[:100]  # Limit to 100 references

    def _count_citations(self, content: str) -> int:
        """Count in-text citations.

        Args:
            content: Document content

        Returns:
            Number of citations found
        """
        citation_patterns = [
            r"\[\d+(?:,\s*\d+)*\]",  # [1], [1, 2]
            r"\(\w+(?:\s+et\s+al\.?)?,?\s*\d{4}(?:;\s*\w+(?:\s+et\s+al\.?)?,?\s*\d{4})*\)",
        ]

        count = 0
        for pattern in citation_patterns:
            matches = re.findall(pattern, content)
            count += len(matches)

        return count

    def _generate_chunk_annotations(
        self, sections: List[Dict[str, Any]], content: str
    ) -> List[Dict[str, Any]]:
        """Generate chunk annotations from sections.

        Args:
            sections: Extracted sections
            content: Original content

        Returns:
            List of chunk annotations
        """
        annotations = []

        for i, section in enumerate(sections):
            end_position = (
                sections[i + 1]["position"] if i + 1 < len(sections) else len(content)
            )

            annotations.append(
                {
                    "start": section["position"],
                    "end": end_position,
                    "type": "academic_section",
                    "section_name": section["name"],
                    "section_number": section.get("number", ""),
                    "preserve_boundary": True,
                }
            )

        return annotations
