"""
Document Parsers
Factory pattern for selecting appropriate parser based on content type
"""

from backend.parsers.docling_parser import DoclingParser
from backend.parsers.text_parser import TextParser
from backend.parsers.audio_parser import AudioParser
from backend.parsers.excel_parser import ExcelParser
from backend.parsers.image_parser import ImageParser
from backend.parsers.youtube_parser import YouTubeParser
from backend.parsers.video_parser import VideoParser
from backend.parsers.ppt_parser import PPTParser
from backend.parsers.json_parser import JSONParser
from backend.parsers.email_parser import EmailParser
from backend.parsers.figure_parser import FigureParser, FigureResult


class ParserFactory:
    """Factory for selecting appropriate parser based on content type"""

    def __init__(self):
        self.parsers = [
            PPTParser(),        # PowerPoint files (PPTX, PPT) - before Docling
            ExcelParser(),      # Excel files - before Docling
            JSONParser(),       # JSON and JSONL files - before Docling
            EmailParser(),      # Email files (EML) - before Docling
            DoclingParser(),    # PDF, DOCX (universal fallback for documents)
            YouTubeParser(),    # YouTube URLs (must be before VideoParser)
            VideoParser(),      # Video files (MP4, AVI, MOV, WEBM)
            AudioParser(),      # Audio files
            ImageParser(),      # Image files
            TextParser(),       # Plain text files (fallback)
        ]

    def get_parser(self, content_type: str):
        """
        Get parser for content type

        Args:
            content_type: MIME type (e.g., "application/pdf")

        Returns:
            Parser instance

        Raises:
            ValueError: If no parser available for content type
        """
        for parser in self.parsers:
            if parser.can_parse(content_type):
                return parser

        raise ValueError(f"No parser available for content type: {content_type}")


__all__ = [
    "ParserFactory",
    "DoclingParser",
    "TextParser",
    "AudioParser",
    "ExcelParser",
    "ImageParser",
    "YouTubeParser",
    "VideoParser",
    "PPTParser",
    "JSONParser",
    "EmailParser",
    "FigureParser",
    "FigureResult",
]
