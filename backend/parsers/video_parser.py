"""
Video Parser for video files (MP4, AVI, MOV, WEBM)
Extracts audio and transcribes using LiteLLM multi-provider STT
"""

import logging
import tempfile
from pathlib import Path
from typing import Dict, Any

try:
    from litellm import atranscription
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False
    atranscription = None

from backend.config import settings
from backend.parsers.video_utils import (
    extract_audio_from_video,
    get_video_metadata,
)

logger = logging.getLogger(__name__)


class VideoParser:
    """
    Parser for video files using ffmpeg + LiteLLM STT

    Workflow:
    1. Extract audio from video using ffmpeg
    2. Transcribe audio using LiteLLM (supports multiple STT providers)
    3. Extract video metadata using ffprobe
    4. Clean up temporary files

    Supported formats: MP4, AVI, MOV, WEBM, MKV
    """

    SUPPORTED_FORMATS = {
        "video/mp4",
        "video/avi",
        "video/x-msvideo",  # AVI alternative
        "video/quicktime",  # MOV
        "video/webm",
        "video/x-matroska",  # MKV
    }

    def __init__(self):
        """Initialize VideoParser"""
        if not LITELLM_AVAILABLE:
            logger.error("LiteLLM is not installed")
            raise ImportError(
                "LiteLLM is required for VideoParser. "
                "Install with: pip install litellm"
            )

        # STT configuration
        self.api_key = settings.STT_SERVICE_API_KEY or settings.OPENAI_API_KEY
        self.stt_service = settings.STT_SERVICE
        self.api_base = settings.STT_SERVICE_API_BASE or None

        if not self.api_key:
            logger.warning("No API key configured for STT - VideoParser will fail at parse time")

    def can_parse(self, content_type: str) -> bool:
        """
        Check if this parser can handle the content type

        Args:
            content_type: MIME type (e.g., "video/mp4")

        Returns:
            True if parser supports this content type
        """
        if not content_type:
            return False
        return content_type in self.SUPPORTED_FORMATS or content_type.startswith("video/")

    async def transcribe_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Transcribe audio file using LiteLLM

        Args:
            audio_path: Path to audio file (WAV)

        Returns:
            Dictionary with transcription results
        """
        try:
            # Build transcription kwargs
            transcription_kwargs = {
                "model": self.stt_service,
                "file": open(audio_path, "rb"),
                "api_key": self.api_key,
            }

            # Add optional API base if configured
            if self.api_base:
                transcription_kwargs["api_base"] = self.api_base

            logger.info(f"Transcribing audio with LiteLLM (provider: {self.stt_service})")

            try:
                response = await atranscription(**transcription_kwargs)
            finally:
                # Ensure file is closed
                if "file" in transcription_kwargs and hasattr(transcription_kwargs["file"], "close"):
                    transcription_kwargs["file"].close()

            # Extract transcription text
            text = response.get("text", "")

            if not text:
                logger.warning("Empty transcription returned")

            return {
                "text": text,
                "language": response.get("language"),
                "duration": response.get("duration"),
                "success": True
            }

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {
                "text": "",
                "error": str(e),
                "success": False
            }

    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse video file: extract audio → transcribe → extract metadata

        Args:
            file_path: Path to video file

        Returns:
            Dict with:
                - content: Transcribed text from video
                - metadata: Video metadata (duration, resolution, etc.)
                - page_count: None
        """
        path = Path(file_path)

        if not path.exists():
            error_msg = f"Video file not found: {file_path}"
            logger.error(error_msg)
            return {
                "content": "",
                "metadata": {"error": error_msg},
                "page_count": None
            }

        # Get file info
        file_size = path.stat().st_size
        file_format = path.suffix.lstrip(".")

        logger.info(f"Processing video file: {path.name} ({file_size / 1024 / 1024:.1f} MB)")

        # Extract video metadata first
        video_metadata = get_video_metadata(str(path), settings.VIDEO_FFPROBE_PATH)

        # Check duration limit
        duration = video_metadata.get("duration_seconds", 0)
        if duration > settings.VIDEO_MAX_DURATION:
            error_msg = (
                f"Video duration ({duration}s) exceeds maximum "
                f"({settings.VIDEO_MAX_DURATION}s)"
            )
            logger.error(error_msg)
            return {
                "content": "",
                "metadata": {
                    "error": error_msg,
                    **video_metadata
                },
                "page_count": None
            }

        # Create temp audio file
        temp_audio = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".wav",
            dir=settings.VIDEO_TEMP_DIR if Path(settings.VIDEO_TEMP_DIR).exists() else None
        )
        temp_audio_path = temp_audio.name
        temp_audio.close()

        try:
            # Extract audio
            audio_extracted = extract_audio_from_video(
                str(path),
                temp_audio_path,
                settings.VIDEO_FFMPEG_PATH
            )

            if not audio_extracted:
                error_msg = "Failed to extract audio from video"
                logger.error(error_msg)
                return {
                    "content": "",
                    "metadata": {
                        "error": error_msg,
                        **video_metadata
                    },
                    "page_count": None
                }

            # Transcribe audio
            transcription_result = await self.transcribe_audio(temp_audio_path)

            if not transcription_result.get("success"):
                error_msg = transcription_result.get("error", "Transcription failed")
                logger.error(error_msg)
                return {
                    "content": "",
                    "metadata": {
                        "error": error_msg,
                        **video_metadata
                    },
                    "page_count": None
                }

            # Build result
            result_metadata = {
                **video_metadata,
                "file_name": path.name,
                "file_format": file_format,
                "transcription_language": transcription_result.get("language"),
                "transcription_model": self.stt_service,
                "transcription_success": True,
            }

            logger.info(
                f"Successfully processed video: {path.name} "
                f"({duration:.1f}s, {len(transcription_result['text'])} chars)"
            )

            return {
                "content": transcription_result["text"],
                "metadata": result_metadata,
                "page_count": None
            }

        except Exception as e:
            error_msg = f"Error processing video {path.name}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "content": "",
                "metadata": {
                    "error": error_msg,
                    **video_metadata
                },
                "page_count": None
            }

        finally:
            # Clean up temp audio file
            try:
                if Path(temp_audio_path).exists():
                    Path(temp_audio_path).unlink()
                    logger.debug(f"Cleaned up temp audio: {temp_audio_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_audio_path}: {e}")
