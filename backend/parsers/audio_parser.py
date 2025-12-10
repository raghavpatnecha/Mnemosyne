"""
Audio Parser for audio transcription
Uses LiteLLM for multi-provider speech-to-text conversion
Supports: OpenAI Whisper, Azure Whisper, Groq Whisper, and more
"""

import logging
from pathlib import Path
from typing import Dict, Any

try:
    from litellm import atranscription
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    atranscription = None

from backend.config import settings

logger = logging.getLogger(__name__)


class AudioParser:
    """
    Parser for audio files using LiteLLM for multi-provider STT

    Supports multiple providers through LiteLLM:
    - OpenAI Whisper: "whisper-1"
    - Azure Whisper: "azure/whisper"
    - Groq Whisper: "groq/whisper-large-v3"
    - Custom endpoints via STT_SERVICE_API_BASE
    """

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
        """Initialize AudioParser with LiteLLM configuration"""
        if not LITELLM_AVAILABLE:
            logger.error("LiteLLM is not installed. Install with: pip install litellm")
            raise ImportError("LiteLLM is required for AudioParser. Install with: pip install litellm")

        # Get API key (use STT-specific or fallback to OPENAI_API_KEY)
        self.api_key = settings.STT_SERVICE_API_KEY or settings.OPENAI_API_KEY

        if not self.api_key:
            logger.warning("No API key configured for STT service - AudioParser will fail at parse time")

        self.stt_service = settings.STT_SERVICE
        self.api_base = settings.STT_SERVICE_API_BASE or None

    def can_parse(self, content_type: str) -> bool:
        """
        Check if this parser can handle the content type

        Args:
            content_type: MIME type (e.g., "audio/mpeg")

        Returns:
            True if parser supports this content type
        """
        if not content_type:
            return False
        return content_type in self.SUPPORTED_FORMATS or content_type.startswith("audio/")

    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using LiteLLM (multi-provider STT)

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
            "stt_provider": self.stt_service,
        }

        try:
            # Build transcription kwargs
            transcription_kwargs = {
                "model": self.stt_service,
                "file": open(file_path, "rb"),
                "api_key": self.api_key,
            }

            # Add optional API base if configured
            if self.api_base:
                transcription_kwargs["api_base"] = self.api_base

            # Transcribe using LiteLLM (async)
            logger.info(
                f"Transcribing audio with LiteLLM: {path.name} "
                f"(provider: {self.stt_service})"
            )

            try:
                response = await atranscription(**transcription_kwargs)
            finally:
                # Ensure file is closed
                if "file" in transcription_kwargs and hasattr(transcription_kwargs["file"], "close"):
                    transcription_kwargs["file"].close()

            # Extract transcription text from response
            # LiteLLM returns a dict-like object
            content = response.get("text", "")

            if not content:
                logger.warning(f"Empty transcription returned for {path.name}")

            # Extract metadata from response
            # LiteLLM response may include: text, language, duration, segments
            metadata.update({
                "language": response.get("language"),
                "duration_seconds": response.get("duration"),
                "transcription_model": self.stt_service,
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
