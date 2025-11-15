"""
Plain Text Parser
Fallback parser for text files
"""

from typing import Dict, Any


class TextParser:
    """Parser for plain text files"""

    SUPPORTED_FORMATS = {
        "text/plain",
        "text/markdown",
        "text/html",
        "text/csv",
    }

    def can_parse(self, content_type: str) -> bool:
        """Check if this parser can handle the content type"""
        return content_type in self.SUPPORTED_FORMATS or content_type.startswith("text/")

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse text file and extract content

        Args:
            file_path: Path to text file

        Returns:
            Dict with content and metadata
        """
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        return {
            "content": content,
            "metadata": {},
            "page_count": None,
        }
