"""
Citation Formatter - Academic [1], [2] style citations
"""

from typing import List, Tuple, Any, Optional


class CitationFormatter:
    """
    Format sources with academic [1], [2] style citations.

    Supports multiple citation styles:
    - inline: Simple [1] inline citations
    - academic: [1], [2] with numbered references
    - academic_full: [1] with full bibliography (author, date)
    - narrative: Natural language citations
    """

    def format_context_with_citations(
        self,
        chunks: List[Any],  # ChunkResult objects
        style: str = "academic"
    ) -> Tuple[str, str]:
        """
        Format chunks with citation markers.

        Args:
            chunks: List of ChunkResult objects with content and document info
            style: Citation style (inline, academic, academic_full, narrative)

        Returns:
            Tuple of (context_text, references_text)
        """
        if not chunks:
            return "", ""

        if style == "narrative":
            return self._format_narrative(chunks)
        elif style == "academic_full":
            return self._format_academic_full(chunks)
        else:
            return self._format_academic(chunks)

    def _format_academic(self, chunks: List[Any]) -> Tuple[str, str]:
        """Standard academic [1], [2] format."""
        context_parts = []
        references = []

        for i, chunk in enumerate(chunks, 1):
            # Get content
            content = getattr(chunk, 'content', str(chunk))

            # Add citation marker to content
            context_parts.append(f"[{i}] {content}")

            # Build reference entry
            doc = getattr(chunk, 'document', None)
            if doc:
                title = getattr(doc, 'title', None) or getattr(doc, 'filename', f'Document {i}')
                ref = f"[{i}] {title}"
            else:
                ref = f"[{i}] Source {i}"

            references.append(ref)

        return "\n\n".join(context_parts), "\n".join(references)

    def _format_academic_full(self, chunks: List[Any]) -> Tuple[str, str]:
        """Academic with full bibliography (author, date, etc.)."""
        context_parts = []
        references = []

        for i, chunk in enumerate(chunks, 1):
            # Get content
            content = getattr(chunk, 'content', str(chunk))
            context_parts.append(f"[{i}] {content}")

            # Build full reference entry
            doc = getattr(chunk, 'document', None)
            ref_parts = [f"[{i}]"]

            if doc:
                title = getattr(doc, 'title', None) or getattr(doc, 'filename', f'Document {i}')
                ref_parts.append(title)

                # Add metadata if available
                metadata = getattr(chunk, 'metadata', None) or {}
                if isinstance(metadata, dict):
                    if 'author' in metadata:
                        ref_parts.append(f"- {metadata['author']}")
                    if 'date' in metadata:
                        ref_parts.append(f"({metadata['date']})")
                    if 'source' in metadata:
                        ref_parts.append(f"[{metadata['source']}]")
            else:
                ref_parts.append(f"Source {i}")

            references.append(" ".join(ref_parts))

        return "\n\n".join(context_parts), "\n".join(references)

    def _format_narrative(self, chunks: List[Any]) -> Tuple[str, str]:
        """Narrative style citations."""
        context_parts = []
        references = []

        for i, chunk in enumerate(chunks, 1):
            content = getattr(chunk, 'content', str(chunk))

            # Get document title for narrative citation
            doc = getattr(chunk, 'document', None)
            if doc:
                title = getattr(doc, 'title', None) or getattr(doc, 'filename', f'Document {i}')
                # Narrative format: "According to [Document Title], ..."
                context_parts.append(f"From {title}:\n{content}")
            else:
                context_parts.append(content)

            references.append(f"- {title if doc else f'Source {i}'}")

        return "\n\n---\n\n".join(context_parts), "\n".join(references)

    def format_inline_citations(self, text: str, source_indices: List[int]) -> str:
        """
        Add inline citations to generated text.

        Args:
            text: Generated response text
            source_indices: List of source indices used

        Returns:
            Text with [1], [2] citations appended
        """
        if not source_indices:
            return text

        citations = ", ".join(f"[{i}]" for i in source_indices)
        return f"{text} {citations}"
