"""
Presentation Document Processor.

Extracts structure from presentation documents including:
- Slide-by-slide organization
- Title and bullet point extraction
- Speaker notes detection
- Slide transitions and hierarchy

Adapted from RAGFlow's presentation.py processor patterns.
"""

import logging
import re
from typing import Any, Dict, List, Optional

from backend.processors.base import DomainProcessor, ProcessorResult

logger = logging.getLogger(__name__)


class PresentationProcessor(DomainProcessor):
    """Processor for presentation documents.

    Extracts slide structure from PowerPoint, Keynote,
    and other presentation formats.
    """

    name = "presentation"
    supported_content_types = [
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/vnd.ms-powerpoint",
        "application/pdf",
        "text/plain",
    ]

    # Slide delimiter patterns
    SLIDE_PATTERNS = [
        r"^---+\s*$",  # Markdown slide separator
        r"^={3,}\s*$",
        r"^(?:Slide|SLIDE)\s+(\d+)\b",
        r"^##\s+Slide\s+(\d+)",
        r"^Page\s+(\d+)\s*$",
        r"^\[Slide\s+(\d+)\]",
    ]

    # Title patterns within slides
    TITLE_PATTERNS = [
        r"^#\s+(.+)$",  # Markdown H1
        r"^##\s+(.+)$",  # Markdown H2
        r"^(?:Title|TITLE):\s*(.+)$",
        r"^([A-Z][A-Za-z\s]{5,50})$",  # All-caps or title-case short line
    ]

    # Bullet point patterns
    BULLET_PATTERNS = [
        r"^[•\-\*]\s+(.+)$",
        r"^\d+[.)]\s+(.+)$",
        r"^[a-z][.)]\s+(.+)$",
        r"^\s{2,}[•\-\*]\s+(.+)$",  # Nested bullets
    ]

    # Speaker notes patterns
    NOTES_PATTERNS = [
        r"^(?:Notes?|NOTES?):\s*(.+)$",
        r"^(?:Speaker\s+Notes?):\s*(.+)$",
        r"^\[Notes?\]\s*(.+)$",
        r"^>\s*Notes?:\s*(.+)$",
    ]

    # Presentation indicators for detection
    PRESENTATION_INDICATORS = [
        r"\bslide\s*\d+\b",
        r"\b(?:presentation|deck|slides?)\b",
        r"\b(?:title\s+slide|agenda|overview)\b",
        r"\b(?:bullet\s+points?|key\s+points?)\b",
        r"\b(?:speaker\s+notes?|presenter\s+notes?)\b",
        r"\b(?:thank\s+you|questions\??)\s*$",
        r"\b(?:q\s*&\s*a|q&a)\b",
    ]

    async def process(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> ProcessorResult:
        """Process presentation and extract slide structure.

        Args:
            content: Document text content
            metadata: User-provided metadata
            filename: Original filename

        Returns:
            ProcessorResult with extracted presentation structure
        """
        logger.debug("Processing presentation document: %s", filename)

        # Extract slides
        slides = self._extract_slides(content)

        # Extract presentation title (usually first slide title)
        presentation_title = self._extract_presentation_title(slides, content)

        # Detect agenda/outline slide
        agenda = self._detect_agenda(slides)

        # Count total bullet points
        total_bullets = sum(len(s.get("bullets", [])) for s in slides)

        # Detect speaker notes
        notes_count = sum(1 for s in slides if s.get("has_notes"))

        # Generate chunk annotations (one per slide)
        chunk_annotations = self._generate_chunk_annotations(slides, content)

        document_metadata = {
            "document_type": "presentation",
            "title": presentation_title,
            "slide_count": len(slides),
            "total_bullet_points": total_bullets,
            "has_speaker_notes": notes_count > 0,
            "speaker_notes_count": notes_count,
            "has_agenda": agenda is not None,
            "agenda_items": agenda,
            "slides": [
                {
                    "number": s["number"],
                    "title": s.get("title", ""),
                    "bullet_count": len(s.get("bullets", [])),
                }
                for s in slides[:30]  # First 30 slides
            ],
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

        sample = content[:10000].lower()
        score = 0.0

        # Check for presentation indicators
        for pattern in self.PRESENTATION_INDICATORS:
            matches = len(re.findall(pattern, sample, re.IGNORECASE))
            score += min(matches * 0.08, 0.25)

        # Check for slide patterns
        lines = content[:15000].split("\n")
        slide_matches = 0
        for line in lines:
            line = line.strip()
            for pattern in self.SLIDE_PATTERNS:
                if re.match(pattern, line, re.IGNORECASE):
                    slide_matches += 1
                    break

        score += min(slide_matches * 0.1, 0.35)

        # Check for bullet patterns (presentations are bullet-heavy)
        bullet_matches = 0
        for line in lines:
            for pattern in self.BULLET_PATTERNS:
                if re.match(pattern, line.strip()):
                    bullet_matches += 1
                    break

        # High bullet density suggests presentation
        bullet_ratio = bullet_matches / max(len(lines), 1)
        if bullet_ratio > 0.3:
            score += 0.2
        elif bullet_ratio > 0.15:
            score += 0.1

        # Check filename
        if filename := metadata.get("filename", ""):
            pres_filename_patterns = [
                r"\.pptx?$", r"presentation", r"deck", r"slides",
                r"keynote", r"pitch",
            ]
            for pattern in pres_filename_patterns:
                if re.search(pattern, filename.lower()):
                    score += 0.25
                    break

        return min(score, 1.0)

    def _extract_slides(self, content: str) -> List[Dict[str, Any]]:
        """Extract individual slides from content.

        Args:
            content: Document content

        Returns:
            List of slide dictionaries
        """
        slides = []
        lines = content.split("\n")

        current_slide = None
        slide_number = 0
        current_position = 0
        slide_start_position = 0

        for line_num, line in enumerate(lines):
            line_stripped = line.strip()

            # Check for slide boundary
            is_slide_boundary = False
            detected_number = None

            for pattern in self.SLIDE_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    is_slide_boundary = True
                    if match.groups():
                        try:
                            detected_number = int(match.group(1))
                        except (ValueError, IndexError):
                            pass
                    break

            if is_slide_boundary:
                # Save previous slide
                if current_slide:
                    current_slide["end_position"] = current_position
                    current_slide["end_line"] = line_num
                    slides.append(current_slide)

                # Start new slide
                slide_number = detected_number or (slide_number + 1)
                slide_start_position = current_position
                current_slide = {
                    "number": slide_number,
                    "title": None,
                    "bullets": [],
                    "notes": [],
                    "has_notes": False,
                    "start_position": slide_start_position,
                    "start_line": line_num,
                }
                current_position += len(line) + 1
                continue

            if current_slide is None:
                # Create implicit first slide
                slide_number = 1
                current_slide = {
                    "number": slide_number,
                    "title": None,
                    "bullets": [],
                    "notes": [],
                    "has_notes": False,
                    "start_position": 0,
                    "start_line": 0,
                }

            # Check for title
            if current_slide["title"] is None:
                for pattern in self.TITLE_PATTERNS:
                    match = re.match(pattern, line_stripped)
                    if match:
                        current_slide["title"] = match.group(1).strip()
                        break

            # Check for bullets
            for pattern in self.BULLET_PATTERNS:
                match = re.match(pattern, line_stripped)
                if match:
                    current_slide["bullets"].append(match.group(1))
                    break

            # Check for speaker notes
            for pattern in self.NOTES_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    current_slide["notes"].append(match.group(1))
                    current_slide["has_notes"] = True
                    break

            current_position += len(line) + 1

        # Add final slide
        if current_slide:
            current_slide["end_position"] = len(content)
            current_slide["end_line"] = len(lines)
            slides.append(current_slide)

        # If no slides detected, treat entire content as one slide
        if not slides:
            slides = [{
                "number": 1,
                "title": self._extract_first_title(content),
                "bullets": self._extract_all_bullets(content),
                "notes": [],
                "has_notes": False,
                "start_position": 0,
                "end_position": len(content),
                "start_line": 0,
                "end_line": len(lines),
            }]

        return slides

    def _extract_first_title(self, content: str) -> Optional[str]:
        """Extract first title from content.

        Args:
            content: Document content

        Returns:
            Title string or None
        """
        lines = content.split("\n")
        for line in lines[:20]:
            line = line.strip()
            for pattern in self.TITLE_PATTERNS:
                match = re.match(pattern, line)
                if match:
                    return match.group(1).strip()
        return None

    def _extract_all_bullets(self, content: str) -> List[str]:
        """Extract all bullets from content.

        Args:
            content: Document content

        Returns:
            List of bullet strings
        """
        bullets = []
        lines = content.split("\n")
        for line in lines:
            for pattern in self.BULLET_PATTERNS:
                match = re.match(pattern, line.strip())
                if match:
                    bullets.append(match.group(1))
                    break
        return bullets[:50]  # Limit

    def _extract_presentation_title(
        self, slides: List[Dict], content: str
    ) -> Optional[str]:
        """Extract presentation title (from first slide or content).

        Args:
            slides: Extracted slides
            content: Document content

        Returns:
            Presentation title or None
        """
        # Try first slide title
        if slides and slides[0].get("title"):
            return slides[0]["title"]

        # Try to find title in first few lines
        lines = content.split("\n")
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 5 and len(line) < 100:
                # Skip common non-title lines
                if not re.match(r"^(Slide|Page|\d+|---|===)", line, re.IGNORECASE):
                    return line

        return None

    def _detect_agenda(self, slides: List[Dict]) -> Optional[List[str]]:
        """Detect agenda/outline slide and extract items.

        Args:
            slides: Extracted slides

        Returns:
            List of agenda items or None
        """
        agenda_patterns = [
            r"agenda", r"outline", r"overview",
            r"topics?", r"contents?", r"today",
        ]

        for slide in slides[:5]:  # Agenda usually in first 5 slides
            title = slide.get("title", "").lower()
            for pattern in agenda_patterns:
                if re.search(pattern, title):
                    return slide.get("bullets", [])

        return None

    def _generate_chunk_annotations(
        self, slides: List[Dict], content: str
    ) -> List[Dict[str, Any]]:
        """Generate chunk annotations for slide-based chunking.

        Each slide becomes a separate chunk.

        Args:
            slides: Extracted slides
            content: Document content

        Returns:
            List of chunk annotations
        """
        annotations = []

        for slide in slides:
            annotations.append({
                "start": slide.get("start_position", 0),
                "end": slide.get("end_position", len(content)),
                "type": "presentation_slide",
                "slide_number": slide["number"],
                "slide_title": slide.get("title", ""),
                "bullet_count": len(slide.get("bullets", [])),
                "has_notes": slide.get("has_notes", False),
                "preserve_boundary": True,  # Each slide is a complete chunk
            })

        return annotations
