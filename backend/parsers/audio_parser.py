"""
Audio Parser for audio transcription
Uses OpenAI Whisper API for speech-to-text conversion
"""

import logging
from pathlib import Path
from typing import Dict, Any
from openai import OpenAI

from backend.config import settings

logger = logging.getLogger(__name__)


class AudioParser:
    """Parser for audio files using OpenAI Whisper API"""

    SUPPORTED_FORMATS = {
        "audio/mpeg",      # MP3
        "audio/mp3",       # MP3 alternative
        "audio/wav",       # WAV
        "audio/x-wav",     # WAV alternative
        "audio/wave",      # WAV alternative
        "audio/x-m4a",     # M4A
        "audio/m4a",       # M4A alternative
        "audio/mp4",       # M4A/MP4 audio
        "audio/webm",      # WEBM
        "audio/ogg",       # OGG
        "audio/flac",      # FLAC
        "audio/x-flac",    # FLAC alternative
    }

    def __init__(self):
        """Initialize AudioParser with OpenAI client"""
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set - AudioParser will fail")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def can_parse(self, content_type: str) -> bool:
        """
        Check if this parser can handle the content type

        Args:
            content_type: MIME type (e.g., "audio/mpeg")

        Returns:
            True if parser supports this content type
        """
        return content_type in self.SUPPORTED_FORMATS or content_type.startswith("audio/")

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using OpenAI Whisper API

        Args:
            file_path: Path to audio file

        Returns:
            Dict with:
                - content: Transcribed text from audio
                - metadata: Audio metadata (duration, format, language, etc.)
                - page_count: None (not applicable for audio)
        """
        path = Path(file_path)

        # Get basic file info
        file_size = path.stat().st_size
        file_format = path.suffix.lstrip('.')

        metadata = {
            "file_size_bytes": file_size,
            "format": file_format,
            "original_filename": path.name,
        }

        try:
            # Open and transcribe audio file with Whisper
            with open(file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json"  # Get detailed metadata including duration
                )

            # Extract transcription text
            content = transcript.text

            # Add Whisper-provided metadata
            metadata.update({
                "language": getattr(transcript, "language", None),
                "duration_seconds": getattr(transcript, "duration", None),
                "transcription_model": "whisper-1",
                "transcription_success": True,
            })

            logger.info(
                f"Successfully transcribed audio: {path.name} "
                f"(duration: {metadata.get('duration_seconds', 'unknown')}s, "
                f"language: {metadata.get('language', 'unknown')})"
            )

        except Exception as e:
            logger.error(f"Failed to transcribe audio {path.name}: {str(e)}")

            # Return error in metadata, empty content
            content = ""
            metadata.update({
                "transcription_error": str(e),
                "transcription_success": False,
                "error_type": type(e).__name__,
            })

        return {
            "content": content,
            "metadata": metadata,
            "page_count": None,  # Not applicable for audio files
        }
