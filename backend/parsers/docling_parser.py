"""
Docling Parser for documents (PDF, DOCX, PPTX)
Advanced document parsing with layout preservation
"""

from pathlib import Path
from typing import Dict, Any
from docling.document_converter import DocumentConverter


class DoclingParser:
    """Parser for documents using Docling (PDF, DOCX, PPTX, etc.)"""

    SUPPORTED_FORMATS = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.ms-powerpoint",
    }

    def __init__(self):
        self.converter = DocumentConverter()

    def can_parse(self, content_type: str) -> bool:
        """Check if this parser can handle the content type"""
        return content_type in self.SUPPORTED_FORMATS

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse document and extract text

        Args:
            file_path: Path to document file

        Returns:
            Dict with:
                - content: Extracted text
                - metadata: Document metadata
                - page_count: Number of pages (if applicable)
        """
        result = self.converter.convert(file_path)

        content = result.document.export_to_markdown()

        metadata = {
            "page_count": len(result.document.pages) if hasattr(result.document, "pages") else None,
            "title": result.document.title if hasattr(result.document, "title") else None,
            "language": result.document.language if hasattr(result.document, "language") else None,
        }

        return {
            "content": content,
            "metadata": metadata,
            "page_count": metadata["page_count"],
        }
