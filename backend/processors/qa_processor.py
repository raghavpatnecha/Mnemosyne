"""
Q&A Document Processor.

Extracts question-answer pairs from documents including:
- FAQ documents
- Exam papers and quizzes
- Interview question documents
- Help documentation with Q&A format

Ported from RAGFlow's qa.py processor with production-tested patterns.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.processors.base import DomainProcessor, ProcessorResult
from backend.processors.ragflow_utils import (
    QUESTION_PATTERNS,
    has_qbullet,
    index_int,
    not_bullet,
    qbullets_category,
)

logger = logging.getLogger(__name__)


class QAProcessor(DomainProcessor):
    """Processor for Q&A format documents.

    Extracts question-answer pairs and structures them for
    improved retrieval and display. Uses RAGFlow-ported patterns
    for robust question detection.
    """

    name = "qa"
    supported_content_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "text/plain",
        "text/markdown",
    ]

    # Q&A detection patterns (ordered by specificity)
    QA_PATTERNS = [
        # Q: / A: format
        (
            r"^(?:Q|Question)\s*[:.]\s*(.+?)(?=\n(?:A|Answer)\s*[:.]\s*)",
            r"^(?:A|Answer)\s*[:.]\s*(.+?)(?=\n(?:Q|Question)\s*[:.]|\Z)",
        ),
        # Question: / Answer: format
        (
            r"^Question\s*[:#]?\s*(.+?)(?=\nAnswer\s*[:#]?\s*)",
            r"^Answer\s*[:#]?\s*(.+?)(?=\nQuestion\s*[:#]?|\Z)",
        ),
        # Numbered Q&A: 1. Question? Answer
        (
            r"^(\d+)\.\s*(.+\?)\s*\n([^?\d][^\n]+)",
            None,  # Combined pattern
        ),
        # FAQ style with bold/header questions
        (
            r"^\*\*(.+\?)\*\*\s*\n(.+?)(?=\n\*\*|\Z)",
            None,  # Combined pattern
        ),
        # Markdown header questions
        (
            r"^#+\s*(.+\?)\s*\n(.+?)(?=\n#+|\Z)",
            None,  # Combined pattern
        ),
    ]

    # Q&A document indicators
    QA_INDICATORS = [
        r"\b(?:FAQ|F\.A\.Q\.|frequently\s+asked\s+questions)\b",
        r"\b(?:Q\s*[&:]\s*A|questions?\s+and\s+answers?)\b",
        r"^(?:Q|Question)\s*[:.#]\s*",
        r"^(?:A|Answer)\s*[:.#]\s*",
        r"\?$",  # Lines ending with question marks
        r"^\d+\.\s*.+\?",  # Numbered questions
        r"\b(?:exam|quiz|test|interview)\s+(?:questions?|paper)\b",
    ]

    async def process(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> ProcessorResult:
        """Process Q&A document and extract pairs.

        Args:
            content: Document text content
            metadata: User-provided metadata
            filename: Original filename

        Returns:
            ProcessorResult with extracted Q&A pairs
        """
        logger.debug("Processing Q&A document: %s", filename)

        # Extract Q&A pairs
        qa_pairs = self._extract_qa_pairs(content)

        # Format content to highlight Q&A structure
        structured_content = self._format_qa_content(qa_pairs, content)

        # Detect document subtype
        doc_subtype = self._detect_subtype(content, filename)

        # Generate chunk annotations
        chunk_annotations = self._generate_qa_annotations(qa_pairs)

        # Prepare pairs for metadata (limit size)
        pairs_preview = [
            {"question": p["question"][:200], "answer": p["answer"][:500]}
            for p in qa_pairs[:20]
        ]

        document_metadata = {
            "document_type": "qa",
            "subtype": doc_subtype,
            "qa_count": len(qa_pairs),
            "qa_pairs": pairs_preview,
            "has_numbered_questions": any(p.get("number") for p in qa_pairs),
            "average_answer_length": (
                sum(len(p["answer"]) for p in qa_pairs) // len(qa_pairs)
                if qa_pairs
                else 0
            ),
        }

        return ProcessorResult(
            content=structured_content,
            document_metadata=document_metadata,
            chunk_annotations=chunk_annotations,
            processor_name=self.name,
            confidence=0.9,
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

        sample = content[:10000]
        score = 0.0

        # Check for Q&A indicators
        for pattern in self.QA_INDICATORS:
            matches = len(re.findall(pattern, sample, re.IGNORECASE | re.MULTILINE))
            score += min(matches * 0.08, 0.3)

        # Count question marks (strong indicator)
        question_marks = sample.count("?")
        score += min(question_marks * 0.02, 0.2)

        # Check for Q:/A: or Question:/Answer: patterns
        qa_format_matches = len(
            re.findall(r"^(?:Q|A|Question|Answer)\s*[:.#]", sample, re.MULTILINE)
        )
        score += min(qa_format_matches * 0.1, 0.3)

        # Check filename
        if filename := metadata.get("filename", ""):
            qa_filename_patterns = [
                r"faq",
                r"q\s*[&_]\s*a",
                r"questions?",
                r"quiz",
                r"exam",
                r"interview",
            ]
            for pattern in qa_filename_patterns:
                if re.search(pattern, filename.lower()):
                    score += 0.2
                    break

        return min(score, 1.0)

    def _extract_qa_pairs(self, content: str) -> List[Dict[str, Any]]:
        """Extract question-answer pairs from content.

        Uses RAGFlow-ported pattern detection for robust extraction.

        Args:
            content: Document content

        Returns:
            List of Q&A pair dictionaries
        """
        qa_pairs = []

        # Try different extraction methods
        pairs = self._extract_explicit_qa(content)
        if pairs:
            qa_pairs.extend(pairs)

        # Try RAGFlow-style bullet detection
        if not qa_pairs:
            pairs = self._extract_bullet_qa(content)
            qa_pairs.extend(pairs)

        # Try numbered questions if no explicit Q&A found
        if not qa_pairs:
            pairs = self._extract_numbered_qa(content)
            qa_pairs.extend(pairs)

        # Try question-mark based detection
        if not qa_pairs:
            pairs = self._extract_question_mark_qa(content)
            qa_pairs.extend(pairs)

        # Deduplicate and clean
        qa_pairs = self._deduplicate_pairs(qa_pairs)

        return qa_pairs

    def _extract_bullet_qa(self, content: str) -> List[Dict[str, Any]]:
        """Extract Q&A pairs using RAGFlow bullet pattern detection.

        Uses RAGFlow's qbullets_category() for pattern detection and
        has_qbullet() for position-aware bullet detection.

        Args:
            content: Document content

        Returns:
            List of Q&A pairs
        """
        pairs = []
        lines = content.split("\n")
        sections = [line.strip() for line in lines if line.strip()]

        # Detect which pattern set matches best using RAGFlow's algorithm
        pattern_idx, pattern = qbullets_category(sections)
        if pattern_idx < 0 or not pattern:
            return pairs

        logger.debug("Detected Q&A bullet pattern: %s", pattern)

        # Build boxes with position info for position-aware detection
        boxes = []
        y_position = 0
        for line in lines:
            line_stripped = line.strip()
            if line_stripped:
                boxes.append({
                    "text": line_stripped,
                    "x0": 0,  # Assume left-aligned
                    "top": y_position,
                    "layout_type": "",
                })
            y_position += 20  # Approximate line height

        # Extract Q&A pairs using position-aware detection
        current_question = None
        current_answer_lines = []
        current_number = None
        last_box = {}
        last_index = 0
        last_bull = None
        bull_x0_list = []

        for i, box in enumerate(boxes):
            line_stripped = box.get("text", "")
            if not line_stripped:
                continue

            # Use RAGFlow's position-aware has_qbullet detection
            match, new_index = has_qbullet(
                pattern,
                box,
                last_box,
                last_index,
                last_bull,
                bull_x0_list,
            )

            if match and not not_bullet(line_stripped):
                # Save previous Q&A if exists
                if current_question and current_answer_lines:
                    pairs.append({
                        "question": current_question,
                        "answer": " ".join(current_answer_lines),
                        "number": current_number,
                        "format": "bullet",
                    })

                # Extract question number using index_int for conversion
                current_number = match.group(1) if match.groups() else None
                if current_number:
                    # Convert to int (supports Chinese, Roman, English words)
                    numeric_idx = index_int(current_number)
                    if numeric_idx > 0:
                        current_number = str(numeric_idx)

                # Get text after the bullet marker
                question_start = match.end()
                question_text = line_stripped[question_start:].strip()

                # If question ends with ?, the rest is the question
                if "?" in question_text or "？" in question_text:
                    q_end = max(
                        question_text.find("?") + 1 if "?" in question_text else 0,
                        question_text.find("？") + 1 if "？" in question_text else 0,
                    )
                    current_question = question_text[:q_end]
                    remainder = question_text[q_end:].strip()
                    current_answer_lines = [remainder] if remainder else []
                else:
                    current_question = question_text
                    current_answer_lines = []

                # Update tracking state
                last_bull = match
                last_index = new_index
            else:
                # Collect answer lines
                if current_question:
                    current_answer_lines.append(line_stripped)

            last_box = box

        # Don't forget the last Q&A
        if current_question and current_answer_lines:
            pairs.append({
                "question": current_question,
                "answer": " ".join(current_answer_lines),
                "number": current_number,
                "format": "bullet",
            })

        return pairs

    def _extract_explicit_qa(self, content: str) -> List[Dict[str, Any]]:
        """Extract Q:/A: or Question:/Answer: format pairs.

        Args:
            content: Document content

        Returns:
            List of Q&A pairs
        """
        pairs = []

        # Pattern for Q: ... A: ... format
        pattern = r"(?:^|\n)(?:Q|Question)\s*[:.#]?\s*(.+?)(?:\n(?:A|Answer)\s*[:.#]?\s*(.+?)(?=\n(?:Q|Question)\s*[:.#]?|\Z))"

        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)

        for question, answer in matches:
            question = question.strip()
            answer = answer.strip()

            if question and answer and len(question) > 5:
                pairs.append(
                    {
                        "question": question,
                        "answer": answer,
                        "format": "explicit",
                    }
                )

        return pairs

    def _extract_numbered_qa(self, content: str) -> List[Dict[str, Any]]:
        """Extract numbered question format (1. Question? Answer).

        Args:
            content: Document content

        Returns:
            List of Q&A pairs
        """
        pairs = []

        # Pattern for numbered questions with answers
        lines = content.split("\n")
        current_question = None
        current_number = None
        current_answer_lines = []

        for line in lines:
            line = line.strip()

            # Check for numbered question
            match = re.match(r"^(\d+)[.)]\s*(.+\?)\s*$", line)
            if match:
                # Save previous Q&A if exists
                if current_question and current_answer_lines:
                    pairs.append(
                        {
                            "question": current_question,
                            "answer": " ".join(current_answer_lines),
                            "number": current_number,
                            "format": "numbered",
                        }
                    )

                current_number = match.group(1)
                current_question = match.group(2)
                current_answer_lines = []
                continue

            # Check for answer on same line as question
            match = re.match(r"^(\d+)[.)]\s*(.+\?)\s+(.+)$", line)
            if match:
                if current_question and current_answer_lines:
                    pairs.append(
                        {
                            "question": current_question,
                            "answer": " ".join(current_answer_lines),
                            "number": current_number,
                            "format": "numbered",
                        }
                    )

                pairs.append(
                    {
                        "question": match.group(2),
                        "answer": match.group(3),
                        "number": match.group(1),
                        "format": "numbered_inline",
                    }
                )
                current_question = None
                current_answer_lines = []
                continue

            # Collect answer lines
            if current_question and line:
                # Stop if we hit another numbered item
                if re.match(r"^\d+[.)]", line):
                    if current_answer_lines:
                        pairs.append(
                            {
                                "question": current_question,
                                "answer": " ".join(current_answer_lines),
                                "number": current_number,
                                "format": "numbered",
                            }
                        )
                    current_question = None
                    current_answer_lines = []
                else:
                    current_answer_lines.append(line)

        # Don't forget the last Q&A
        if current_question and current_answer_lines:
            pairs.append(
                {
                    "question": current_question,
                    "answer": " ".join(current_answer_lines),
                    "number": current_number,
                    "format": "numbered",
                }
            )

        return pairs

    def _extract_question_mark_qa(self, content: str) -> List[Dict[str, Any]]:
        """Extract Q&A based on question marks and following content.

        Args:
            content: Document content

        Returns:
            List of Q&A pairs
        """
        pairs = []
        lines = content.split("\n")

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if line is a question (ends with ?)
            if line.endswith("?") and len(line) > 10:
                question = line
                answer_lines = []

                # Collect following lines as answer
                j = i + 1
                while j < len(lines):
                    next_line = lines[j].strip()

                    # Stop at next question or empty section
                    if next_line.endswith("?") and len(next_line) > 10:
                        break
                    if not next_line and answer_lines:
                        # Allow one empty line, but stop at two
                        if j + 1 < len(lines) and not lines[j + 1].strip():
                            break

                    if next_line:
                        answer_lines.append(next_line)
                    j += 1

                if answer_lines:
                    pairs.append(
                        {
                            "question": question,
                            "answer": " ".join(answer_lines),
                            "format": "question_mark",
                        }
                    )
                    i = j
                    continue

            i += 1

        return pairs

    def _deduplicate_pairs(
        self, pairs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Remove duplicate Q&A pairs.

        Args:
            pairs: List of Q&A pairs

        Returns:
            Deduplicated list
        """
        seen_questions = set()
        unique_pairs = []

        for pair in pairs:
            # Normalize question for comparison
            normalized = re.sub(r"\s+", " ", pair["question"].lower().strip())

            if normalized not in seen_questions:
                seen_questions.add(normalized)
                unique_pairs.append(pair)

        return unique_pairs

    def _format_qa_content(
        self, qa_pairs: List[Dict[str, Any]], original_content: str
    ) -> str:
        """Format content with clear Q&A structure.

        If we found Q&A pairs, restructure content for better retrieval.
        Otherwise, return original content.

        Args:
            qa_pairs: Extracted Q&A pairs
            original_content: Original document content

        Returns:
            Formatted content string
        """
        if not qa_pairs:
            return original_content

        # Format Q&A pairs with clear structure
        formatted_sections = []

        for i, pair in enumerate(qa_pairs, 1):
            number = pair.get("number", str(i))
            question = pair["question"]
            answer = pair["answer"]

            formatted_sections.append(
                f"Q{number}: {question}\n\nA{number}: {answer}"
            )

        return "\n\n---\n\n".join(formatted_sections)

    def _detect_subtype(self, content: str, filename: str) -> str:
        """Detect Q&A document subtype.

        Args:
            content: Document content
            filename: Original filename

        Returns:
            Subtype string
        """
        sample = (content[:5000] + " " + filename).lower()

        subtype_patterns = {
            "faq": [r"\bfaq\b", r"\bfrequently\s+asked\b"],
            "exam": [r"\bexam\b", r"\btest\b", r"\bquiz\b", r"\bassessment\b"],
            "interview": [r"\binterview\b", r"\bhiring\b", r"\bcandidate\b"],
            "help": [r"\bhelp\b", r"\bsupport\b", r"\btroubleshooting\b"],
            "tutorial": [r"\btutorial\b", r"\bhow\s+to\b", r"\bguide\b"],
        }

        best_subtype = "general"
        best_score = 0

        for subtype, patterns in subtype_patterns.items():
            score = sum(1 for p in patterns if re.search(p, sample))
            if score > best_score:
                best_score = score
                best_subtype = subtype

        return best_subtype

    def _generate_qa_annotations(
        self, qa_pairs: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate chunk annotations for Q&A pairs.

        Each Q&A pair should ideally be kept together as a chunk.

        Args:
            qa_pairs: Extracted Q&A pairs

        Returns:
            List of chunk annotations
        """
        annotations = []

        for i, pair in enumerate(qa_pairs):
            annotations.append(
                {
                    "index": i,
                    "type": "qa_pair",
                    "question": pair["question"][:200],
                    "format": pair.get("format", "unknown"),
                    "number": pair.get("number"),
                    "keep_together": True,  # Hint to chunker
                }
            )

        return annotations
