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


class ParserFactory:
    """Factory for selecting appropriate parser based on content type"""

    def __init__(self):
        self.parsers = [
            DoclingParser(),
            YouTubeParser(),    # YouTube URLs (must be before VideoParser)
            VideoParser(),      # Video files (MP4, AVI, MOV, WEBM)
            AudioParser(),
            ExcelParser(),
            ImageParser(),
            TextParser(),
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
]
