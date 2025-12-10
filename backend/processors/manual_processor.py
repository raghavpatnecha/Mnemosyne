"""
Manual/Technical Document Processor.

Extracts structure from technical documentation including:
- Installation guides
- How-to sections
- Troubleshooting sections
- Command/code examples
- Step-by-step procedures
- Warning/Note/Tip callouts

Adapted from RAGFlow's manual.py processor patterns.
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


class ManualProcessor(DomainProcessor):
    """Processor for technical manuals and documentation.

    Extracts structure from user guides, installation manuals,
    how-to documents, and technical documentation.
    """

    name = "manual"
    supported_content_types = [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/markdown",
    ]

    # Section type patterns
    SECTION_PATTERNS = {
        "installation": [
            r"^(?:##?\s*)?(?:INSTALLATION|Installation|INSTALL|Install)\b",
            r"^(?:##?\s*)?(?:GETTING\s+STARTED|Getting\s+Started)\b",
            r"^(?:##?\s*)?(?:SETUP|Setup|SET\s*UP|Set\s*Up)\b",
            r"^(?:##?\s*)?(?:QUICK\s+START|Quick\s+Start)\b",
        ],
        "configuration": [
            r"^(?:##?\s*)?(?:CONFIGURATION|Configuration|CONFIG|Config)\b",
            r"^(?:##?\s*)?(?:SETTINGS?|Settings?)\b",
            r"^(?:##?\s*)?(?:OPTIONS?|Options?)\b",
            r"^(?:##?\s*)?(?:PREFERENCES?|Preferences?)\b",
        ],
        "usage": [
            r"^(?:##?\s*)?(?:USAGE|Usage)\b",
            r"^(?:##?\s*)?(?:HOW\s+TO|How\s+To)\b",
            r"^(?:##?\s*)?(?:USING|Using)\b",
            r"^(?:##?\s*)?(?:BASIC\s+)?(?:OPERATIONS?|Operations?)\b",
        ],
        "troubleshooting": [
            r"^(?:##?\s*)?(?:TROUBLESHOOTING|Troubleshooting)\b",
            r"^(?:##?\s*)?(?:COMMON\s+)?(?:PROBLEMS?|Problems?)\b",
            r"^(?:##?\s*)?(?:COMMON\s+)?(?:ISSUES?|Issues?)\b",
            r"^(?:##?\s*)?(?:FAQ|F\.A\.Q\.?|Frequently\s+Asked)\b",
            r"^(?:##?\s*)?(?:ERROR|Error)\s*(?:MESSAGES?|Messages?)?\b",
        ],
        "reference": [
            r"^(?:##?\s*)?(?:REFERENCE|Reference)\b",
            r"^(?:##?\s*)?(?:API\s+)?(?:REFERENCE|Reference)\b",
            r"^(?:##?\s*)?(?:COMMAND\s+)?(?:REFERENCE|Reference)\b",
            r"^(?:##?\s*)?(?:APPENDIX|Appendix)\b",
        ],
        "examples": [
            r"^(?:##?\s*)?(?:EXAMPLES?|Examples?)\b",
            r"^(?:##?\s*)?(?:USE\s+CASES?|Use\s+Cases?)\b",
            r"^(?:##?\s*)?(?:TUTORIALS?|Tutorials?)\b",
            r"^(?:##?\s*)?(?:SAMPLE|Sample)\b",
        ],
    }

    # Callout patterns (Note, Warning, Tip, etc.)
    CALLOUT_PATTERNS = [
        r"^(?:NOTE|Note|Nota):\s*(.+)$",
        r"^(?:WARNING|Warning|CAUTION|Caution):\s*(.+)$",
        r"^(?:TIP|Tip|HINT|Hint):\s*(.+)$",
        r"^(?:IMPORTANT|Important):\s*(.+)$",
        r"^(?:DANGER|Danger):\s*(.+)$",
        r"^(?:INFO|Information):\s*(.+)$",
        r"^\[(?:NOTE|WARNING|TIP|IMPORTANT|DANGER|INFO)\]\s*(.+)$",
        r"^>\s*(?:\*\*)?(?:Note|Warning|Tip)(?:\*\*)?:\s*(.+)$",  # Markdown blockquote
    ]

    # Step patterns
    STEP_PATTERNS = [
        r"^(?:Step\s+)?(\d+)[.):]\s*(.+)$",
        r"^(\d+)\.\s+(.+)$",
        r"^[•\-\*]\s+(.+)$",
        r"^[a-z]\)\s+(.+)$",
    ]

    # Code block patterns
    CODE_PATTERNS = [
        r"^```[\w]*\n([\s\S]+?)^```",  # Markdown fenced code
        r"^\s{4,}(.+)$",  # Indented code
        r"^>\s*\$\s*(.+)$",  # Command prompt
        r"^>\s*C:\\.*>(.+)$",  # Windows prompt
    ]

    # Manual indicators for detection
    MANUAL_INDICATORS = [
        r"\b(?:install(?:ation)?|setup|configure|configuration)\b",
        r"\b(?:step\s+\d+|follow(?:ing)?\s+steps?)\b",
        r"\b(?:how\s+to|guide|tutorial|manual)\b",
        r"\b(?:troubleshoot(?:ing)?|problem|issue|error)\b",
        r"\b(?:command|terminal|console|shell)\b",
        r"\b(?:click|select|choose|enter|type)\b",
        r"\b(?:warning|caution|note|tip|important)\b",
        r"\b(?:requirements?|prerequisites?|dependencies?)\b",
        r"\b(?:user\s+guide|quick\s+start|getting\s+started)\b",
    ]

    async def process(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> ProcessorResult:
        """Process technical manual and extract structure.

        Args:
            content: Document text content
            metadata: User-provided metadata
            filename: Original filename

        Returns:
            ProcessorResult with extracted manual structure
        """
        logger.debug("Processing manual document: %s", filename)

        # Extract sections by type
        sections = self._extract_sections(content)

        # Extract callouts (Note, Warning, Tip, etc.)
        callouts = self._extract_callouts(content)

        # Extract step-by-step procedures
        procedures = self._extract_procedures(content)

        # Extract code examples
        code_blocks = self._extract_code_blocks(content)

        # Extract requirements/prerequisites
        requirements = self._extract_requirements(content)

        # Generate chunk annotations
        chunk_annotations = self._generate_chunk_annotations(
            content, sections, procedures
        )

        # Determine manual type
        manual_type = self._detect_manual_type(sections, content)

        # Use hierarchical_merge for section-based chunking (RAGFlow algorithm)
        hierarchy_merge_result = self._merge_hierarchically(content)

        document_metadata = {
            "document_type": "manual",
            "manual_type": manual_type,
            "sections": {k: len(v) for k, v in sections.items()},
            "section_names": self._get_section_names(sections),
            "callout_count": len(callouts),
            "callouts": callouts[:20],  # Limit for storage
            "procedure_count": len(procedures),
            "has_code_examples": len(code_blocks) > 0,
            "code_block_count": len(code_blocks),
            "requirements": requirements,
            "has_installation": "installation" in sections and len(sections["installation"]) > 0,
            "has_troubleshooting": "troubleshooting" in sections and len(sections["troubleshooting"]) > 0,
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

        sample = content[:10000].lower()
        score = 0.0

        # Check for manual indicators
        for pattern in self.MANUAL_INDICATORS:
            matches = len(re.findall(pattern, sample, re.IGNORECASE))
            score += min(matches * 0.03, 0.15)

        # Check for section patterns
        lines = content[:15000].split("\n")
        section_matches = 0
        for line in lines[:400]:
            line = line.strip()
            for section_type, patterns in self.SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        section_matches += 1
                        break

        score += min(section_matches * 0.1, 0.3)

        # Check for step patterns
        step_matches = 0
        for line in lines[:400]:
            for pattern in self.STEP_PATTERNS:
                if re.match(pattern, line.strip()):
                    step_matches += 1
                    break

        score += min(step_matches * 0.02, 0.2)

        # Check for callouts
        callout_matches = 0
        for line in lines[:400]:
            for pattern in self.CALLOUT_PATTERNS:
                if re.match(pattern, line.strip(), re.IGNORECASE):
                    callout_matches += 1
                    break

        score += min(callout_matches * 0.05, 0.15)

        # Check filename
        if filename := metadata.get("filename", ""):
            manual_filename_patterns = [
                r"manual", r"guide", r"howto", r"how-to",
                r"install", r"setup", r"readme", r"documentation",
            ]
            for pattern in manual_filename_patterns:
                if re.search(pattern, filename.lower()):
                    score += 0.15
                    break

        return min(score, 1.0)

    def _extract_sections(self, content: str) -> Dict[str, List[Dict]]:
        """Extract sections by type.

        Args:
            content: Document content

        Returns:
            Dictionary of section types to section lists
        """
        sections = {section_type: [] for section_type in self.SECTION_PATTERNS}
        lines = content.split("\n")
        current_position = 0

        for line_num, line in enumerate(lines):
            line_stripped = line.strip()

            for section_type, patterns in self.SECTION_PATTERNS.items():
                for pattern in patterns:
                    match = re.match(pattern, line_stripped, re.IGNORECASE)
                    if match:
                        sections[section_type].append({
                            "title": line_stripped,
                            "line_number": line_num,
                            "position": current_position,
                        })
                        break

            current_position += len(line) + 1

        return sections

    def _extract_callouts(self, content: str) -> List[Dict[str, Any]]:
        """Extract callouts (Note, Warning, Tip, etc.).

        Args:
            content: Document content

        Returns:
            List of callout dictionaries
        """
        callouts = []
        lines = content.split("\n")
        current_position = 0

        callout_type_map = {
            "NOTE": "note", "Note": "note", "Nota": "note",
            "WARNING": "warning", "Warning": "warning", "CAUTION": "warning", "Caution": "warning",
            "TIP": "tip", "Tip": "tip", "HINT": "tip", "Hint": "tip",
            "IMPORTANT": "important", "Important": "important",
            "DANGER": "danger", "Danger": "danger",
            "INFO": "info", "Information": "info",
        }

        for line_num, line in enumerate(lines):
            line_stripped = line.strip()

            for pattern in self.CALLOUT_PATTERNS:
                match = re.match(pattern, line_stripped, re.IGNORECASE)
                if match:
                    # Determine callout type
                    callout_type = "note"  # default
                    for key, value in callout_type_map.items():
                        if key.lower() in line_stripped.lower():
                            callout_type = value
                            break

                    callouts.append({
                        "type": callout_type,
                        "text": match.group(1) if match.groups() else line_stripped,
                        "line_number": line_num,
                        "position": current_position,
                    })
                    break

            current_position += len(line) + 1

        return callouts

    def _extract_procedures(self, content: str) -> List[Dict[str, Any]]:
        """Extract step-by-step procedures.

        Args:
            content: Document content

        Returns:
            List of procedure dictionaries
        """
        procedures = []
        lines = content.split("\n")
        current_procedure = None
        current_position = 0

        for line_num, line in enumerate(lines):
            line_stripped = line.strip()

            # Check for numbered step
            step_match = re.match(r"^(?:Step\s+)?(\d+)[.):]\s*(.+)$", line_stripped)
            if step_match:
                step_num = int(step_match.group(1))
                step_text = step_match.group(2)

                if step_num == 1:
                    # Start new procedure
                    if current_procedure:
                        procedures.append(current_procedure)
                    current_procedure = {
                        "start_line": line_num,
                        "start_position": current_position,
                        "steps": [],
                    }

                if current_procedure:
                    current_procedure["steps"].append({
                        "number": step_num,
                        "text": step_text,
                        "line_number": line_num,
                    })

            current_position += len(line) + 1

        # Add last procedure
        if current_procedure and current_procedure["steps"]:
            procedures.append(current_procedure)

        return procedures

    def _extract_code_blocks(self, content: str) -> List[Dict[str, Any]]:
        """Extract code examples.

        Args:
            content: Document content

        Returns:
            List of code block dictionaries
        """
        code_blocks = []

        # Find fenced code blocks
        fenced_pattern = r"```([\w]*)\n([\s\S]*?)```"
        for match in re.finditer(fenced_pattern, content, re.MULTILINE):
            code_blocks.append({
                "type": "fenced",
                "language": match.group(1) or "text",
                "code": match.group(2).strip(),
                "position": match.start(),
            })

        # Find command-line examples
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if re.match(r"^\s*\$\s+\S", line):  # Unix command
                code_blocks.append({
                    "type": "command",
                    "language": "bash",
                    "code": line.strip()[2:],  # Remove $ prefix
                    "line_number": i,
                })
            elif re.match(r"^\s*>\s+\S", line) and not re.match(r"^\s*>\s*(?:Note|Warning)", line):
                code_blocks.append({
                    "type": "command",
                    "language": "shell",
                    "code": line.strip()[2:],
                    "line_number": i,
                })

        return code_blocks[:50]  # Limit to 50 code blocks

    def _extract_requirements(self, content: str) -> List[str]:
        """Extract requirements/prerequisites.

        Args:
            content: Document content

        Returns:
            List of requirement strings
        """
        requirements = []
        lines = content.split("\n")
        in_requirements = False

        req_start_patterns = [
            r"^(?:##?\s*)?(?:REQUIREMENTS?|Requirements?)\b",
            r"^(?:##?\s*)?(?:PREREQUISITES?|Prerequisites?)\b",
            r"^(?:##?\s*)?(?:DEPENDENCIES|Dependencies)\b",
            r"^(?:##?\s*)?(?:BEFORE\s+YOU\s+BEGIN|Before\s+You\s+Begin)\b",
            r"^(?:##?\s*)?(?:SYSTEM\s+REQUIREMENTS?|System\s+Requirements?)\b",
        ]

        req_end_patterns = [
            r"^(?:##?\s*)?(?:INSTALLATION|Installation)\b",
            r"^(?:##?\s*)?(?:GETTING\s+STARTED|Getting\s+Started)\b",
            r"^(?:##?\s*)?(?:SETUP|Setup)\b",
            r"^#{1,2}\s+",  # Next markdown heading
        ]

        for line in lines:
            line_stripped = line.strip()

            # Check for requirements section start
            if not in_requirements:
                for pattern in req_start_patterns:
                    if re.match(pattern, line_stripped, re.IGNORECASE):
                        in_requirements = True
                        break
                continue

            # Check for end of requirements section
            for pattern in req_end_patterns:
                if re.match(pattern, line_stripped, re.IGNORECASE):
                    in_requirements = False
                    break

            if not in_requirements:
                break

            # Extract requirement items
            if re.match(r"^[•\-\*]\s+(.+)$", line_stripped):
                requirements.append(
                    re.match(r"^[•\-\*]\s+(.+)$", line_stripped).group(1)
                )
            elif re.match(r"^\d+[.)]\s+(.+)$", line_stripped):
                requirements.append(
                    re.match(r"^\d+[.)]\s+(.+)$", line_stripped).group(1)
                )

        return requirements[:20]  # Limit to 20 requirements

    def _detect_manual_type(
        self, sections: Dict[str, List], content: str
    ) -> str:
        """Detect the type of manual.

        Args:
            sections: Extracted sections
            content: Document content

        Returns:
            Manual type string
        """
        sample = content[:5000].lower()

        type_scores = {
            "installation_guide": 0,
            "user_guide": 0,
            "api_reference": 0,
            "troubleshooting_guide": 0,
            "quick_start": 0,
        }

        # Score based on sections
        if sections["installation"]:
            type_scores["installation_guide"] += 3
            type_scores["quick_start"] += 1
        if sections["configuration"]:
            type_scores["user_guide"] += 2
            type_scores["installation_guide"] += 1
        if sections["usage"]:
            type_scores["user_guide"] += 3
        if sections["troubleshooting"]:
            type_scores["troubleshooting_guide"] += 3
            type_scores["user_guide"] += 1
        if sections["reference"]:
            type_scores["api_reference"] += 3
        if sections["examples"]:
            type_scores["user_guide"] += 1
            type_scores["api_reference"] += 1

        # Score based on content keywords
        if "quick start" in sample:
            type_scores["quick_start"] += 2
        if "api" in sample and "endpoint" in sample:
            type_scores["api_reference"] += 2
        if "install" in sample and len(sections.get("installation", [])) > 0:
            type_scores["installation_guide"] += 1

        # Return highest scoring type
        return max(type_scores, key=type_scores.get)

    def _get_section_names(self, sections: Dict[str, List]) -> List[str]:
        """Get unique section names.

        Args:
            sections: Extracted sections

        Returns:
            List of section names
        """
        names = []
        for section_list in sections.values():
            for section in section_list:
                if section.get("title"):
                    names.append(section["title"])
        return names[:30]  # Limit to 30 names

    def _generate_chunk_annotations(
        self,
        content: str,
        sections: Dict[str, List],
        procedures: List[Dict],
    ) -> List[Dict[str, Any]]:
        """Generate chunk annotations.

        Args:
            content: Document content
            sections: Extracted sections
            procedures: Extracted procedures

        Returns:
            List of chunk annotations
        """
        annotations = []

        # Collect all section positions
        all_sections = []
        for section_type, section_list in sections.items():
            for section in section_list:
                all_sections.append({
                    **section,
                    "section_type": section_type,
                })

        # Sort by position
        all_sections.sort(key=lambda x: x["position"])

        # Create annotations for each section
        for i, section in enumerate(all_sections):
            end_position = (
                all_sections[i + 1]["position"]
                if i + 1 < len(all_sections)
                else len(content)
            )

            annotations.append({
                "start": section["position"],
                "end": end_position,
                "type": f"manual_{section['section_type']}",
                "section_title": section["title"],
                "preserve_boundary": True,
            })

        # Add procedure annotations
        for procedure in procedures:
            annotations.append({
                "start": procedure["start_position"],
                "end": procedure["start_position"] + 1000,  # Approximate
                "type": "manual_procedure",
                "step_count": len(procedure["steps"]),
                "preserve_boundary": True,
            })

        return annotations

    def _merge_hierarchically(self, content: str) -> Dict[str, Any]:
        """Merge content using RAGFlow's hierarchical_merge algorithm.

        Groups manual sections (installation, usage, troubleshooting) into
        coherent chunks that preserve section boundaries.

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
            # Detect if line is a section header
            for section_type, patterns in self.SECTION_PATTERNS.items():
                for pattern in patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        layout = "title"
                        break
                if layout:
                    break
            section_tuples.append((line, layout))

        # Get hierarchy levels
        most_level, levels = title_frequency(category, section_tuples)

        # Use hierarchical_merge for section-based grouping
        # depth=2 for Installation > Steps, Usage > Examples hierarchy
        merged_chunks = hierarchical_merge(category, section_tuples, depth=2)

        return {
            "category": category,
            "most_common_level": most_level,
            "merged_chunks": merged_chunks[:100],
            "chunk_count": len(merged_chunks),
        }
