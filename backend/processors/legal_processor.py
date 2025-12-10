"""
Legal Document Processor.

Extracts hierarchical structure from legal documents including:
- Parts, Chapters, Sections, Articles, Clauses
- Definitions sections
- Multi-level numbered lists
- Roman numeral formatting

Ported from RAGFlow's laws.py processor with production-quality patterns.
"""

import logging
import re
from typing import Any, Dict, List, Tuple

from backend.processors.base import DomainProcessor, ProcessorResult
from backend.processors.ragflow_utils import (
    BULLET_PATTERNS,
    bullets_category,
    not_bullet,
    title_frequency,
    tree_merge,
)

logger = logging.getLogger(__name__)


class LegalProcessor(DomainProcessor):
    """Processor for legal documents.

    Extracts hierarchical structure from legislation, contracts,
    regulations, and other legal documents.

    Supports:
    - English legal documents (Part/Chapter/Section/Article)
    - Multi-level numbering (1.1, 1.1.1, 1.1.1.1)
    - Roman numerals (I, II, III, IV, V...)
    - Parenthetical numbering ((1), (a), (i))
    """

    name = "legal"
    supported_content_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/msword",
        "text/plain",
    ]

    # Hierarchy level mapping for each pattern set
    # Must match pattern order in BULLET_PATTERNS
    LEVEL_NAMES = {
        # Numeric: ordered by specificity (most specific first)
        0: ["clause_l4", "clause_l3", "clause_l2", "clause_l1", "clause_paren", "clause_alpha", "clause_roman"],
        # English: PART(word), Part(word), CHAPTER, Chapter, SECTION, Section, ARTICLE, Article, section
        1: ["part", "part", "chapter", "chapter", "section", "section", "article", "article", "section"],
        2: ["h1", "h2", "h3", "h4", "h5", "h6"],  # Markdown
    }

    # Patterns for legal document detection
    LEGAL_INDICATORS = [
        # English contract language
        r"\b(?:WHEREAS|WITNESSETH|NOW,?\s*THEREFORE)\b",
        r"\b(?:hereinafter|heretofore|hereby|herein|thereof|thereto)\b",
        r"\b(?:shall\s+be|shall\s+not|may\s+not|must\s+not)\b",
        r"\b(?:party|parties)\s+(?:of\s+the\s+)?(?:first|second|third)\s+part\b",
        r"\b(?:terms\s+and\s+conditions|governing\s+law|jurisdiction)\b",
        r"\b(?:indemnify|indemnification|liability|damages|breach)\b",
        r"\b(?:amendment|termination|severability|waiver|force\s+majeure)\b",
        r"\b(?:contract|agreement|covenant|obligation|warranty)\b",
        r"\b(?:plaintiff|defendant|court|tribunal|arbitration)\b",
        # Structural markers
        r"^(?:Section|SECTION|Article|ARTICLE|§)\s*[0-9]+",
    ]

    # Definitions section patterns
    DEFINITIONS_PATTERNS = [
        r"^(?:DEFINITIONS?|Definitions?)\s*$",
        r"^(?:\d+\.?\s*)?(?:DEFINITIONS?|Definitions?)\s*$",
        r"^(?:Article|Section|ARTICLE|SECTION)\s+\d+[.:]\s*(?:DEFINITIONS?|Definitions?)",
        r"^(?:CHAPTER|Chapter)\s+[IVXLCDM\d]+[.:\s-]+(?:DEFINITIONS?|Definitions?)",
    ]

    async def process(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> ProcessorResult:
        """Process legal document and extract structure.

        Args:
            content: Document text content
            metadata: User-provided metadata
            filename: Original filename

        Returns:
            ProcessorResult with extracted legal structure
        """
        logger.debug("Processing legal document: %s", filename)

        # Detect which bullet pattern set to use
        sections = [line.strip() for line in content.split("\n") if line.strip()]
        bullet_category = bullets_category(sections)

        # Extract hierarchical structure using detected patterns
        structure = self._extract_hierarchy(content, bullet_category)

        # Extract definitions section
        definitions = self._extract_definitions(content)

        # Calculate hierarchy depth
        hierarchy_depth = self._calculate_depth(structure)

        # Generate chunk annotations
        chunk_annotations = self._generate_chunk_annotations(structure, content)

        # Detect document subtype
        doc_subtype = self._detect_subtype(content, filename)

        # Use tree_merge for hierarchical chunking (RAGFlow algorithm)
        tree_merge_result = self._merge_with_tree(content, bullet_category)

        document_metadata = {
            "document_type": "legal",
            "subtype": doc_subtype,
            "bullet_category": bullet_category,
            "structure": structure[:50],  # Limit for storage
            "definitions": definitions[:20],  # Limit for storage
            "hierarchy_depth": hierarchy_depth,
            "section_count": len(structure),
            "has_definitions": len(definitions) > 0,
            # Tree merge results for hierarchical chunking
            "merged_chunks": tree_merge_result.get("merged_chunks", []),
            "merged_chunk_count": tree_merge_result.get("chunk_count", 0),
            "most_common_level": tree_merge_result.get("most_common_level", -1),
        }

        return ProcessorResult(
            content=content,
            document_metadata=document_metadata,
            chunk_annotations=chunk_annotations,
            processor_name=self.name,
            confidence=0.9 if bullet_category >= 0 else 0.7,
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

        sample = content[:8000]
        score = 0.0

        # Check for legal language patterns
        for pattern in self.LEGAL_INDICATORS:
            matches = len(re.findall(pattern, sample, re.IGNORECASE | re.MULTILINE))
            score += min(matches * 0.08, 0.25)

        # Check for hierarchical structure using all pattern sets
        sections = [line.strip() for line in sample.split("\n") if line.strip()]
        bullet_category = bullets_category(sections[:200])

        if bullet_category >= 0:
            # Count matches for the detected pattern set
            pattern_set = BULLET_PATTERNS[bullet_category]
            structure_matches = 0
            for section in sections[:200]:
                for pattern in pattern_set:
                    if re.match(pattern, section) and not not_bullet(section):
                        structure_matches += 1
                        break
            score += min(structure_matches * 0.04, 0.35)

        # Check filename for legal indicators
        if filename := metadata.get("filename", ""):
            legal_filename_patterns = [
                r"contract", r"agreement", r"terms", r"policy",
                r"nda", r"legal", r"law", r"statute", r"regulation",
            ]
            for pattern in legal_filename_patterns:
                if re.search(pattern, filename.lower()):
                    score += 0.15
                    break

        return min(score, 1.0)

    def _extract_hierarchy(
        self, content: str, bullet_category: int
    ) -> List[Dict[str, Any]]:
        """Extract hierarchical structure from legal document.

        Args:
            content: Document text content
            bullet_category: Detected bullet pattern set index

        Returns:
            List of structure elements with level, type, number, title, and position
        """
        structure = []
        lines = content.split("\n")

        if bullet_category < 0:
            # Fallback to English patterns
            bullet_category = 1

        pattern_set = BULLET_PATTERNS[bullet_category]
        level_names = self.LEVEL_NAMES.get(bullet_category, ["level_" + str(i) for i in range(10)])

        current_position = 0
        for line_num, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                current_position += len(line) + 1
                continue

            # Skip false positives
            if not_bullet(line_stripped):
                current_position += len(line) + 1
                continue

            # Check each pattern in the set
            for level_idx, pattern in enumerate(pattern_set):
                match = re.match(pattern, line_stripped)
                if match:
                    # Extract number/identifier from match
                    groups = match.groups() if match.groups() else (match.group(),)
                    number = groups[0] if groups else ""

                    # Get remaining text as title
                    title = line_stripped[match.end():].strip()
                    title = re.sub(r"^[\s.:\-]+", "", title)  # Clean leading punctuation

                    level_name = level_names[level_idx] if level_idx < len(level_names) else f"level_{level_idx}"

                    structure.append({
                        "level": level_name,
                        "level_idx": level_idx,
                        "number": number,
                        "title": title[:200],  # Limit title length
                        "line_number": line_num,
                        "position": current_position,
                        "text": line_stripped[:300],  # Limit text length
                    })
                    break

            current_position += len(line) + 1

        return structure

    def _extract_definitions(self, content: str) -> List[Dict[str, str]]:
        """Extract definitions from legal document.

        Args:
            content: Document text content

        Returns:
            List of definition dictionaries with term and definition
        """
        definitions = []
        lines = content.split("\n")
        in_definitions = False

        definitions_end_patterns = [
            r"^(?:ARTICLE|Article|SECTION|Section|CHAPTER|Chapter)\s+\d+",
            r"^(?:PART|Part)\s+[IVXLCDM\d]+",
        ]

        for line in lines:
            line_stripped = line.strip()

            # Check if entering definitions section
            just_entered = False
            for pattern in self.DEFINITIONS_PATTERNS:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    in_definitions = True
                    just_entered = True
                    break

            # Check if leaving definitions section (skip if we just entered)
            if in_definitions and not just_entered:
                for pattern in definitions_end_patterns:
                    if re.match(pattern, line_stripped):
                        in_definitions = False
                        break

            if not in_definitions:
                continue

            # Extract definition patterns
            definition_patterns = [
                # "Term" means/shall mean ...
                r'"([^"]+)"\s+(?:means?|shall\s+mean|refers?\s+to|is\s+defined\s+as)\s+(.+)',
                r"'([^']+)'\s+(?:means?|shall\s+mean|refers?\s+to|is\s+defined\s+as)\s+(.+)",
                # Term means ...
                r"([A-Z][a-zA-Z\s]{2,30})\s+(?:means?|shall\s+mean)\s+(.+)",
            ]

            for pattern in definition_patterns:
                match = re.search(pattern, line_stripped, re.IGNORECASE)
                if match:
                    term = match.group(1).strip()
                    definition = match.group(2).strip()
                    # Clean up definition
                    definition = re.sub(r"[;.]$", "", definition)
                    if len(term) > 2 and len(definition) > 5:
                        definitions.append({
                            "term": term,
                            "definition": definition[:500],  # Limit length
                        })
                    break

        return definitions

    def _calculate_depth(self, structure: List[Dict[str, Any]]) -> int:
        """Calculate maximum hierarchy depth.

        Args:
            structure: Extracted structure list

        Returns:
            Maximum depth
        """
        if not structure:
            return 0

        max_level_idx = max(item.get("level_idx", 0) for item in structure)
        return max_level_idx + 1

    def _generate_chunk_annotations(
        self, structure: List[Dict[str, Any]], content: str
    ) -> List[Dict[str, Any]]:
        """Generate annotations for chunking.

        Creates annotations that help preserve legal structure during chunking.

        Args:
            structure: Extracted structure list
            content: Original content

        Returns:
            List of chunk annotations with boundaries and metadata
        """
        annotations = []

        for i, item in enumerate(structure):
            # Determine end position (start of next item or end of content)
            end_position = (
                structure[i + 1]["position"] if i + 1 < len(structure) else len(content)
            )

            annotations.append({
                "start": item["position"],
                "end": end_position,
                "type": "legal_section",
                "level": item["level"],
                "level_idx": item.get("level_idx", 0),
                "number": item["number"],
                "title": item.get("title", ""),
                "preserve_boundary": True,
            })

        return annotations

    def _detect_subtype(self, content: str, filename: str) -> str:
        """Detect legal document subtype.

        Args:
            content: Document content
            filename: Original filename

        Returns:
            Subtype string
        """
        sample = (content[:5000] + " " + filename).lower()

        subtype_patterns = {
            "contract": [
                r"\bcontract\b", r"\bagreement\b", r"\bparties\b", r"\bwhereas\b",
            ],
            "legislation": [
                r"\bact\b", r"\bstatute\b", r"\blaw\b", r"\benacted\b",
            ],
            "regulation": [
                r"\bregulation\b", r"\brule\b", r"\bcompliance\b",
            ],
            "policy": [
                r"\bpolicy\b", r"\bprivacy\b", r"\bterms\s+of\s+(?:service|use)\b",
            ],
            "court": [
                r"\bplaintiff\b", r"\bdefendant\b", r"\bcourt\b", r"\bjudgment\b",
            ],
        }

        best_subtype = "other"
        best_score = 0

        for subtype, patterns in subtype_patterns.items():
            score = sum(1 for p in patterns if re.search(p, sample))
            if score > best_score:
                best_score = score
                best_subtype = subtype

        return best_subtype

    def _merge_with_tree(self, content: str, bullet_category: int) -> Dict[str, Any]:
        """Merge content using RAGFlow's tree_merge algorithm.

        Creates hierarchical chunks that preserve legal document structure
        with parent context included in each chunk.

        Args:
            content: Document content
            bullet_category: Detected bullet pattern category

        Returns:
            Dictionary with merge results and hierarchy info
        """
        lines = content.split("\n")
        sections = [line.strip() for line in lines if line.strip()]

        if bullet_category < 0:
            return {
                "category": -1,
                "merged_chunks": [],
                "most_common_level": -1,
            }

        # Build section tuples (text, layout_type)
        section_tuples: List[Tuple[str, str]] = []
        for line in sections:
            layout = ""
            # Detect if line is a title/header based on legal patterns
            if re.match(r"^(?:PART|Part|CHAPTER|Chapter|SECTION|Section|ARTICLE|Article)", line):
                layout = "title"
            section_tuples.append((line, layout))

        # Get hierarchy levels
        most_level, levels = title_frequency(bullet_category, section_tuples)

        # Use tree_merge for deep legal hierarchies (RAGFlow's algorithm)
        # depth=3 to capture Part > Chapter > Section > Article hierarchy
        merged_chunks = tree_merge(bullet_category, section_tuples, depth=3)

        return {
            "category": bullet_category,
            "most_common_level": most_level,
            "merged_chunks": merged_chunks[:100],
            "chunk_count": len(merged_chunks),
        }
