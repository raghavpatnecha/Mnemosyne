"""
Book Document Processor.

Extracts hierarchical structure from books and long-form documents including:
- Parts, Chapters, Sections, Subsections
- Table of Contents detection
- Chapter hierarchy preservation
- Front/back matter identification

Adapted from RAGFlow's book.py processor patterns.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.processors.base import DomainProcessor, ProcessorResult
from backend.processors.ragflow_utils import (
    BULLET_PATTERNS,
    bullets_category,
    hierarchical_merge,
    title_frequency,
)

logger = logging.getLogger(__name__)


class BookProcessor(DomainProcessor):
    """Processor for book documents.

    Extracts hierarchical structure from books, manuals, and long-form
    documents with chapter-based organization.
    """

    name = "book"
    supported_content_types = [
        "application/pdf",
        "application/epub+zip",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]

    # Part patterns (highest level)
    PART_PATTERNS = [
        r"^(?:PART|Part)\s+([IVXLCDM]+|[0-9]+)[\s:.]*(.*)$",
        r"^(?:BOOK|Book)\s+([IVXLCDM]+|[0-9]+)[\s:.]*(.*)$",
        r"^(?:VOLUME|Volume)\s+([IVXLCDM]+|[0-9]+)[\s:.]*(.*)$",
    ]

    # Chapter patterns
    CHAPTER_PATTERNS = [
        r"^(?:CHAPTER|Chapter)\s+([IVXLCDM]+|[0-9]+)[\s:.]*(.*)$",
        r"^(?:Ch\.|CH\.)\s*([0-9]+)[\s:.]*(.*)$",
        r"^([0-9]+)\s*[.:\-]\s*([A-Z][^.]+)$",  # 1. Introduction
    ]

    # Section patterns
    SECTION_PATTERNS = [
        r"^(?:Section|SECTION)\s+([0-9]+(?:\.[0-9]+)*)[\s:.]*(.*)$",
        r"^([0-9]+\.[0-9]+)[\s:.]+(.+)$",  # 1.1 Subsection
        r"^([0-9]+\.[0-9]+\.[0-9]+)[\s:.]+(.+)$",  # 1.1.1 Sub-subsection
    ]

    # Front/back matter patterns
    FRONT_MATTER_PATTERNS = [
        r"^(?:PREFACE|Preface)\s*$",
        r"^(?:FOREWORD|Foreword)\s*$",
        r"^(?:INTRODUCTION|Introduction)\s*$",
        r"^(?:PROLOGUE|Prologue)\s*$",
        r"^(?:ACKNOWLEDGM?ENTS?|Acknowledgm?ents?)\s*$",
        r"^(?:DEDICATION|Dedication)\s*$",
        r"^(?:CONTENTS?|Contents?|TABLE\s+OF\s+CONTENTS?)\s*$",
    ]

    BACK_MATTER_PATTERNS = [
        r"^(?:EPILOGUE|Epilogue)\s*$",
        r"^(?:AFTERWORD|Afterword)\s*$",
        r"^(?:APPENDIX|Appendix|APPENDICES|Appendices)\s*([A-Z0-9]*)[\s:.]*(.*)$",
        r"^(?:GLOSSARY|Glossary)\s*$",
        r"^(?:BIBLIOGRAPHY|Bibliography)\s*$",
        r"^(?:REFERENCES?|References?)\s*$",
        r"^(?:INDEX|Index)\s*$",
        r"^(?:NOTES?|Notes?)\s*$",
        r"^(?:ABOUT\s+THE\s+AUTHOR|About\s+the\s+Author)\s*$",
    ]

    # Book indicators for detection
    BOOK_INDICATORS = [
        r"\b(?:chapter|chapters)\s+[0-9ivxlcdm]+\b",
        r"\b(?:part|parts)\s+[0-9ivxlcdm]+\b",
        r"\btable\s+of\s+contents?\b",
        r"\b(?:preface|foreword|introduction|prologue)\b",
        r"\b(?:epilogue|afterword|appendix|glossary)\b",
        r"\b(?:bibliography|index)\b",
        r"\babout\s+the\s+author\b",
        r"\b(?:volume|book)\s+[0-9ivxlcdm]+\b",
    ]

    async def process(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> ProcessorResult:
        """Process book document and extract chapter structure.

        Args:
            content: Document text content
            metadata: User-provided metadata
            filename: Original filename

        Returns:
            ProcessorResult with extracted book structure
        """
        logger.debug("Processing book document: %s", filename)

        # Extract title (usually first substantial line or metadata)
        title = self._extract_title(content, metadata)

        # Detect table of contents
        toc = self._extract_toc(content)

        # Extract parts
        parts = self._extract_parts(content)

        # Extract chapters
        chapters = self._extract_chapters(content)

        # Extract sections within chapters
        sections = self._extract_sections(content)

        # Identify front and back matter
        front_matter = self._identify_front_matter(content)
        back_matter = self._identify_back_matter(content)

        # Calculate hierarchy depth
        hierarchy_depth = self._calculate_depth(parts, chapters, sections)

        # Generate chunk annotations for chapter-aware chunking
        chunk_annotations = self._generate_chunk_annotations(
            content, parts, chapters, sections
        )

        # Use hierarchical_merge for grouped chapter chunking (RAGFlow algorithm)
        hierarchy_merge_result = self._merge_hierarchically(content)

        document_metadata = {
            "document_type": "book",
            "title": title,
            "has_toc": bool(toc),
            "toc_entries": len(toc),
            "part_count": len(parts),
            "chapter_count": len(chapters),
            "section_count": len(sections),
            "hierarchy_depth": hierarchy_depth,
            "front_matter": front_matter,
            "back_matter": back_matter,
            "chapters": [c["title"] for c in chapters[:20]],  # First 20 chapters
            # Hierarchical merge results for intelligent chunking
            "hierarchy_category": hierarchy_merge_result.get("category", -1),
            "merged_chunks": hierarchy_merge_result.get("merged_chunks", []),
            "merged_chunk_count": hierarchy_merge_result.get("chunk_count", 0),
        }

        return ProcessorResult(
            content=content,
            document_metadata=document_metadata,
            chunk_annotations=chunk_annotations,
            processor_name=self.name,
            confidence=0.85,
        )

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

        sample = content[:15000].lower()
        score = 0.0

        # Check for book indicators
        for pattern in self.BOOK_INDICATORS:
            matches = len(re.findall(pattern, sample, re.IGNORECASE))
            score += min(matches * 0.08, 0.25)

        # Check for chapter patterns
        lines = content[:20000].split("\n")
        chapter_matches = 0
        for line in lines[:500]:
            line = line.strip()
            for pattern in self.CHAPTER_PATTERNS:
                if re.match(pattern, line, re.IGNORECASE):
                    chapter_matches += 1
                    break

        score += min(chapter_matches * 0.12, 0.35)

        # Check for part patterns
        part_matches = 0
        for line in lines[:500]:
            line = line.strip()
            for pattern in self.PART_PATTERNS:
                if re.match(pattern, line, re.IGNORECASE):
                    part_matches += 1
                    break

        score += min(part_matches * 0.15, 0.2)

        # Check for TOC
        if re.search(r"table\s+of\s+contents?", sample):
            score += 0.15

        # Check filename
        if filename := metadata.get("filename", ""):
            book_filename_patterns = [
                r"book", r"novel", r"volume", r"manual",
                r"guide", r"handbook", r"edition",
            ]
            for pattern in book_filename_patterns:
                if re.search(pattern, filename.lower()):
                    score += 0.1
                    break

        return min(score, 1.0)

    def _extract_title(
        self, content: str, metadata: Dict[str, Any]
    ) -> Optional[str]:
        """Extract book title.

        Args:
            content: Document content
            metadata: User-provided metadata

        Returns:
            Extracted title or None
        """
        # Check metadata first
        if title := metadata.get("title"):
            return title

        lines = content.split("\n")
        for line in lines[:30]:
            line = line.strip()
            if not line:
                continue

            # Skip TOC, copyright, etc.
            skip_patterns = [
                r"^(?:table\s+of\s+contents?|copyright|isbn)",
                r"^\d+$",
                r"^(?:page|chapter|part)\s+\d+",
            ]
            if any(re.match(p, line, re.IGNORECASE) for p in skip_patterns):
                continue

            # Title should be substantial
            if len(line) > 10 and len(line) < 150:
                return line

        return None

    def _extract_toc(self, content: str) -> List[Dict[str, Any]]:
        """Extract table of contents entries.

        Args:
            content: Document content

        Returns:
            List of TOC entries
        """
        toc_entries = []
        lines = content.split("\n")
        in_toc = False
        toc_end_line = 0

        for i, line in enumerate(lines[:300]):
            line_stripped = line.strip()

            # Detect TOC start
            if re.match(
                r"^(?:TABLE\s+OF\s+)?CONTENTS?$", line_stripped, re.IGNORECASE
            ):
                in_toc = True
                continue

            if not in_toc:
                continue

            # Detect TOC end (chapter 1, introduction, etc.)
            if (
                re.match(r"^(?:CHAPTER|Chapter|PART|Part)\s+1", line_stripped)
                or re.match(r"^(?:INTRODUCTION|Introduction)$", line_stripped)
                or (i - toc_end_line > 5 and not line_stripped)
            ):
                break

            if not line_stripped:
                toc_end_line = i
                continue

            # Parse TOC entry (title ... page)
            toc_pattern = r"^(.+?)[\s.]{3,}(\d+)$"
            match = re.match(toc_pattern, line_stripped)
            if match:
                toc_entries.append({
                    "title": match.group(1).strip(),
                    "page": int(match.group(2)),
                })
            elif len(line_stripped) > 3:
                # Entry without page number
                toc_entries.append({
                    "title": line_stripped,
                    "page": None,
                })

        return toc_entries[:100]  # Limit entries

    def _extract_parts(self, content: str) -> List[Dict[str, Any]]:
        """Extract part divisions.

        Args:
            content: Document content

        Returns:
            List of part dictionaries
        """
        parts = []
        lines = content.split("\n")
        current_position = 0

        for line_num, line in enumerate(lines):
            line_stripped = line.strip()

            for pattern in self.PART_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    parts.append({
                        "number": match.group(1),
                        "title": match.group(2).strip() if match.group(2) else "",
                        "line_number": line_num,
                        "position": current_position,
                    })
                    break

            current_position += len(line) + 1

        return parts

    def _extract_chapters(self, content: str) -> List[Dict[str, Any]]:
        """Extract chapter structure.

        Args:
            content: Document content

        Returns:
            List of chapter dictionaries
        """
        chapters = []
        lines = content.split("\n")
        current_position = 0

        for line_num, line in enumerate(lines):
            line_stripped = line.strip()

            for pattern in self.CHAPTER_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    chapters.append({
                        "number": match.group(1),
                        "title": match.group(2).strip() if match.group(2) else "",
                        "line_number": line_num,
                        "position": current_position,
                    })
                    break

            current_position += len(line) + 1

        return chapters

    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract section structure within chapters.

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
                    sections.append({
                        "number": match.group(1),
                        "title": match.group(2).strip() if match.group(2) else "",
                        "line_number": line_num,
                        "position": current_position,
                        "level": line_stripped.count("."),  # Depth indicator
                    })
                    break

            current_position += len(line) + 1

        return sections

    def _identify_front_matter(self, content: str) -> List[str]:
        """Identify front matter sections.

        Args:
            content: Document content

        Returns:
            List of front matter section names
        """
        front_matter = []
        lines = content.split("\n")

        for line in lines[:200]:  # Front matter in first 200 lines
            line_stripped = line.strip()
            for pattern in self.FRONT_MATTER_PATTERNS:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    front_matter.append(line_stripped)
                    break

        return front_matter

    def _identify_back_matter(self, content: str) -> List[str]:
        """Identify back matter sections.

        Args:
            content: Document content

        Returns:
            List of back matter section names
        """
        back_matter = []
        lines = content.split("\n")

        # Check last portion of document
        for line in lines[-500:]:
            line_stripped = line.strip()
            for pattern in self.BACK_MATTER_PATTERNS:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    back_matter.append(line_stripped)
                    break

        return back_matter

    def _calculate_depth(
        self,
        parts: List[Dict],
        chapters: List[Dict],
        sections: List[Dict],
    ) -> int:
        """Calculate hierarchy depth.

        Args:
            parts: Extracted parts
            chapters: Extracted chapters
            sections: Extracted sections

        Returns:
            Maximum hierarchy depth
        """
        depth = 0
        if parts:
            depth = 1
        if chapters:
            depth = max(depth, 2)
        if sections:
            max_section_depth = max(
                (s.get("level", 0) for s in sections), default=0
            )
            depth = max(depth, 2 + max_section_depth)
        return depth

    def _generate_chunk_annotations(
        self,
        content: str,
        parts: List[Dict],
        chapters: List[Dict],
        sections: List[Dict],
    ) -> List[Dict[str, Any]]:
        """Generate chunk annotations for chapter-aware chunking.

        Args:
            content: Document content
            parts: Extracted parts
            chapters: Extracted chapters
            sections: Extracted sections

        Returns:
            List of chunk annotations
        """
        annotations = []

        # Add chapter boundaries (primary chunking boundaries)
        for i, chapter in enumerate(chapters):
            end_position = (
                chapters[i + 1]["position"]
                if i + 1 < len(chapters)
                else len(content)
            )

            annotations.append({
                "start": chapter["position"],
                "end": end_position,
                "type": "book_chapter",
                "chapter_number": chapter["number"],
                "chapter_title": chapter.get("title", ""),
                "preserve_boundary": True,
            })

        # Add section boundaries (secondary)
        for i, section in enumerate(sections):
            end_position = (
                sections[i + 1]["position"]
                if i + 1 < len(sections)
                else len(content)
            )

            annotations.append({
                "start": section["position"],
                "end": end_position,
                "type": "book_section",
                "section_number": section["number"],
                "section_title": section.get("title", ""),
                "preserve_boundary": False,  # Can be split if needed
            })

        return annotations

    def _merge_hierarchically(self, content: str) -> Dict[str, Any]:
        """Merge content using RAGFlow's hierarchical_merge algorithm.

        Groups content by chapter/section hierarchy for better chunking.
        Returns grouped sections that preserve chapter boundaries.

        Args:
            content: Document content

        Returns:
            Dictionary with merge results and hierarchy info
        """
        lines = content.split("\n")
        sections = [line.strip() for line in lines if line.strip()]

        # Detect bullet pattern category
        category = bullets_category(sections)

        if category < 0:
            return {
                "category": -1,
                "merged_chunks": [],
                "hierarchy_info": None,
            }

        # Build section tuples (text, layout_type)
        section_tuples: List[Tuple[str, str]] = []
        for line in sections:
            layout = ""
            # Detect if line is a title/header
            for pattern in self.PART_PATTERNS + self.CHAPTER_PATTERNS:
                if re.match(pattern, line, re.IGNORECASE):
                    layout = "title"
                    break
            section_tuples.append((line, layout))

        # Get hierarchy levels
        most_level, levels = title_frequency(category, section_tuples)

        # Use hierarchical_merge for chapter-based grouping
        # depth=3 to capture Part > Chapter > Section hierarchy
        merged_chunks = hierarchical_merge(category, section_tuples, depth=3)

        return {
            "category": category,
            "most_common_level": most_level,
            "merged_chunks": merged_chunks[:100],
            "chunk_count": len(merged_chunks),
        }
