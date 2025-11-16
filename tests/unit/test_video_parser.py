"""
Unit tests for VideoParser

Tests:
- MIME type validation (can_parse)
- Video file parsing with ffmpeg audio extraction
- Audio transcription via LiteLLM
- Video metadata extraction via ffprobe
- Temporary file cleanup
- Error handling (ffmpeg failures, transcription errors, duration limits)
- Multi-format support (MP4, AVI, MOV, WEBM, MKV)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open, AsyncMock
from pathlib import Path
import tempfile

from backend.parsers.video_parser import VideoParser


@pytest.mark.unit
class TestVideoParser:
    """Test suite for VideoParser with ffmpeg + LiteLLM"""

    @patch('backend.parsers.video_parser.settings')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_init_with_api_key(self, mock_settings):
        """Test initialization with valid API key"""
        mock_settings.STT_SERVICE_API_KEY = ""
        mock_settings.OPENAI_API_KEY = "test_key"
        mock_settings.STT_SERVICE = "whisper-1"
        mock_settings.STT_SERVICE_API_BASE = ""

        parser = VideoParser()

        assert parser.api_key == "test_key"
        assert parser.stt_service == "whisper-1"

    @patch('backend.parsers.video_parser.settings')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_init_with_stt_specific_key(self, mock_settings):
        """Test initialization with STT-specific API key"""
        mock_settings.OPENAI_API_KEY = "openai_key"
        mock_settings.STT_SERVICE_API_KEY = "stt_key"
        mock_settings.STT_SERVICE = "groq/whisper-large-v3"
        mock_settings.STT_SERVICE_API_BASE = "https://api.groq.com"

        parser = VideoParser()

        assert parser.api_key == "stt_key"
        assert parser.stt_service == "groq/whisper-large-v3"
        assert parser.api_base == "https://api.groq.com"

    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', False)
    def test_init_without_litellm(self):
        """Test initialization fails without LiteLLM"""
        with pytest.raises(ImportError, match="LiteLLM is required"):
            VideoParser()

    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_mp4(self):
        """Test can_parse with video/mp4 MIME type"""
        parser = VideoParser()
        assert parser.can_parse("video/mp4") is True

    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_avi(self):
        """Test can_parse with video/avi MIME type"""
        parser = VideoParser()
        assert parser.can_parse("video/avi") is True

    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_avi_alternative(self):
        """Test can_parse with video/x-msvideo MIME type"""
        parser = VideoParser()
        assert parser.can_parse("video/x-msvideo") is True

    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_quicktime(self):
        """Test can_parse with video/quicktime (MOV) MIME type"""
        parser = VideoParser()
        assert parser.can_parse("video/quicktime") is True

    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_webm(self):
        """Test can_parse with video/webm MIME type"""
        parser = VideoParser()
        assert parser.can_parse("video/webm") is True

    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_mkv(self):
        """Test can_parse with video/x-matroska (MKV) MIME type"""
        parser = VideoParser()
        assert parser.can_parse("video/x-matroska") is True

    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_generic_video(self):
        """Test can_parse with generic video/* MIME type"""
        parser = VideoParser()
        assert parser.can_parse("video/unknown") is True

    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_invalid_audio(self):
        """Test can_parse rejects audio MIME type"""
        parser = VideoParser()
        assert parser.can_parse("audio/mp3") is False

    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_invalid_text(self):
        """Test can_parse rejects text MIME type"""
        parser = VideoParser()
        assert parser.can_parse("text/plain") is False

    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_invalid_image(self):
        """Test can_parse rejects image MIME type"""
        parser = VideoParser()
        assert parser.can_parse("image/jpeg") is False

    @pytest.mark.asyncio
    @patch('backend.parsers.video_parser.atranscription')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    async def test_transcribe_audio_success(self, mock_file, mock_atranscription):
        """Test successful audio transcription"""
        mock_atranscription.return_value = {
            "text": "This is a test transcription",
            "language": "en",
            "duration": 30.5
        }

        parser = VideoParser()
        result = await parser.transcribe_audio("/fake/audio.wav")

        assert result["success"] is True
        assert result["text"] == "This is a test transcription"
        assert result["language"] == "en"
        assert result["duration"] == 30.5

    @pytest.mark.asyncio
    @patch('backend.parsers.video_parser.atranscription')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    async def test_transcribe_audio_empty_text(self, mock_file, mock_atranscription):
        """Test transcription with empty text"""
        mock_atranscription.return_value = {
            "text": "",
            "language": "en",
            "duration": 5.0
        }

        parser = VideoParser()
        result = await parser.transcribe_audio("/fake/audio.wav")

        assert result["success"] is True
        assert result["text"] == ""

    @pytest.mark.asyncio
    @patch('backend.parsers.video_parser.atranscription')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    async def test_transcribe_audio_api_error(self, mock_file, mock_atranscription):
        """Test transcription with API error"""
        mock_atranscription.side_effect = Exception("API timeout")

        parser = VideoParser()
        result = await parser.transcribe_audio("/fake/audio.wav")

        assert result["success"] is False
        assert "API timeout" in result["error"]
        assert result["text"] == ""

    @pytest.mark.asyncio
    @patch('backend.parsers.video_parser.Path')
    @patch('backend.parsers.video_parser.get_video_metadata')
    @patch('backend.parsers.video_parser.extract_audio_from_video')
    @patch('backend.parsers.video_parser.atranscription')
    @patch('backend.parsers.video_parser.tempfile.NamedTemporaryFile')
    @patch('backend.parsers.video_parser.settings')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    async def test_parse_success(
        self, mock_file, mock_settings, mock_tempfile, mock_atranscription,
        mock_extract_audio, mock_get_metadata, mock_path_class
    ):
        """Test successful video parsing workflow"""
        # Configure settings
        mock_settings.VIDEO_FFMPEG_PATH = "ffmpeg"
        mock_settings.VIDEO_FFPROBE_PATH = "ffprobe"
        mock_settings.VIDEO_MAX_DURATION = 3600
        mock_settings.VIDEO_TEMP_DIR = "/tmp"
        mock_settings.STT_SERVICE = "whisper-1"

        # Setup path mock
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 10485760  # 10 MB
        mock_path.suffix = ".mp4"
        mock_path.name = "test_video.mp4"
        mock_path_class.return_value = mock_path

        # Mock temp file
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/temp_audio.wav"
        mock_temp.close = MagicMock()
        mock_tempfile.return_value = mock_temp

        # Mock video metadata
        mock_get_metadata.return_value = {
            "duration_seconds": 120.5,
            "file_size_bytes": 10485760,
            "format_name": "mp4",
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "codec": "h264"
        }

        # Mock audio extraction
        mock_extract_audio.return_value = True

        # Mock transcription
        mock_atranscription.return_value = {
            "text": "Video transcription content",
            "language": "en",
            "duration": 120.5
        }

        parser = VideoParser()
        result = await parser.parse("/fake/path/test_video.mp4")

        # Verify content
        assert result["content"] == "Video transcription content"
        assert result["page_count"] is None

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["duration_seconds"] == 120.5
        assert metadata["file_name"] == "test_video.mp4"
        assert metadata["file_format"] == "mp4"
        assert metadata["width"] == 1920
        assert metadata["height"] == 1080
        assert metadata["fps"] == 30.0
        assert metadata["transcription_language"] == "en"
        assert metadata["transcription_model"] == "whisper-1"
        assert metadata["transcription_success"] is True

        # Verify cleanup
        assert mock_path.unlink.called

    @pytest.mark.asyncio
    @patch('backend.parsers.video_parser.Path')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    async def test_parse_file_not_found(self, mock_path_class):
        """Test parse with non-existent file"""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        parser = VideoParser()
        result = await parser.parse("/fake/path/missing.mp4")

        assert result["content"] == ""
        assert "not found" in result["metadata"]["error"]
        assert result["page_count"] is None

    @pytest.mark.asyncio
    @patch('backend.parsers.video_parser.Path')
    @patch('backend.parsers.video_parser.get_video_metadata')
    @patch('backend.parsers.video_parser.settings')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    async def test_parse_duration_exceeded(self, mock_settings, mock_get_metadata, mock_path_class):
        """Test parse with video exceeding duration limit"""
        mock_settings.VIDEO_MAX_DURATION = 1800  # 30 minutes
        mock_settings.VIDEO_FFPROBE_PATH = "ffprobe"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 50000000
        mock_path.suffix = ".mp4"
        mock_path.name = "long_video.mp4"
        mock_path_class.return_value = mock_path

        # Mock metadata with long duration
        mock_get_metadata.return_value = {
            "duration_seconds": 3600,  # 1 hour (exceeds limit)
            "file_size_bytes": 50000000,
            "format_name": "mp4"
        }

        parser = VideoParser()
        result = await parser.parse("/fake/path/long_video.mp4")

        assert result["content"] == ""
        assert "exceeds maximum" in result["metadata"]["error"]
        assert result["metadata"]["duration_seconds"] == 3600

    @pytest.mark.asyncio
    @patch('backend.parsers.video_parser.Path')
    @patch('backend.parsers.video_parser.get_video_metadata')
    @patch('backend.parsers.video_parser.extract_audio_from_video')
    @patch('backend.parsers.video_parser.tempfile.NamedTemporaryFile')
    @patch('backend.parsers.video_parser.settings')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    async def test_parse_audio_extraction_failed(
        self, mock_settings, mock_tempfile, mock_extract_audio,
        mock_get_metadata, mock_path_class
    ):
        """Test parse when audio extraction fails"""
        mock_settings.VIDEO_FFMPEG_PATH = "ffmpeg"
        mock_settings.VIDEO_FFPROBE_PATH = "ffprobe"
        mock_settings.VIDEO_MAX_DURATION = 3600

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 1024000
        mock_path.suffix = ".avi"
        mock_path.name = "corrupted.avi"
        mock_path_class.return_value = mock_path

        mock_temp = MagicMock()
        mock_temp.name = "/tmp/temp_audio.wav"
        mock_temp.close = MagicMock()
        mock_tempfile.return_value = mock_temp

        mock_get_metadata.return_value = {
            "duration_seconds": 60.0,
            "file_size_bytes": 1024000
        }

        # Audio extraction fails
        mock_extract_audio.return_value = False

        parser = VideoParser()
        result = await parser.parse("/fake/path/corrupted.avi")

        assert result["content"] == ""
        assert "Failed to extract audio" in result["metadata"]["error"]

    @pytest.mark.asyncio
    @patch('backend.parsers.video_parser.Path')
    @patch('backend.parsers.video_parser.get_video_metadata')
    @patch('backend.parsers.video_parser.extract_audio_from_video')
    @patch('backend.parsers.video_parser.atranscription')
    @patch('backend.parsers.video_parser.tempfile.NamedTemporaryFile')
    @patch('backend.parsers.video_parser.settings')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    async def test_parse_transcription_failed(
        self, mock_file, mock_settings, mock_tempfile, mock_atranscription,
        mock_extract_audio, mock_get_metadata, mock_path_class
    ):
        """Test parse when transcription fails"""
        mock_settings.VIDEO_FFMPEG_PATH = "ffmpeg"
        mock_settings.VIDEO_FFPROBE_PATH = "ffprobe"
        mock_settings.VIDEO_MAX_DURATION = 3600
        mock_settings.VIDEO_TEMP_DIR = "/tmp"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 2048000
        mock_path.suffix = ".webm"
        mock_path.name = "test.webm"
        mock_path_class.return_value = mock_path

        mock_temp = MagicMock()
        mock_temp.name = "/tmp/temp_audio.wav"
        mock_temp.close = MagicMock()
        mock_tempfile.return_value = mock_temp

        mock_get_metadata.return_value = {
            "duration_seconds": 45.0,
            "file_size_bytes": 2048000
        }

        mock_extract_audio.return_value = True

        # Transcription fails
        mock_atranscription.side_effect = Exception("Transcription timeout")

        parser = VideoParser()
        result = await parser.parse("/fake/path/test.webm")

        assert result["content"] == ""
        assert "Transcription timeout" in result["metadata"]["error"]

    @pytest.mark.asyncio
    @patch('backend.parsers.video_parser.Path')
    @patch('backend.parsers.video_parser.get_video_metadata')
    @patch('backend.parsers.video_parser.extract_audio_from_video')
    @patch('backend.parsers.video_parser.atranscription')
    @patch('backend.parsers.video_parser.tempfile.NamedTemporaryFile')
    @patch('backend.parsers.video_parser.settings')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    async def test_parse_cleanup_on_error(
        self, mock_file, mock_settings, mock_tempfile, mock_atranscription,
        mock_extract_audio, mock_get_metadata, mock_path_class
    ):
        """Test that errors during transcription are handled gracefully"""
        mock_settings.VIDEO_FFMPEG_PATH = "ffmpeg"
        mock_settings.VIDEO_FFPROBE_PATH = "ffprobe"
        mock_settings.VIDEO_MAX_DURATION = 3600
        mock_settings.VIDEO_TEMP_DIR = "/tmp"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 1024000
        mock_path.suffix = ".mp4"
        mock_path.name = "test.mp4"
        mock_path_class.return_value = mock_path

        mock_temp = MagicMock()
        mock_temp.name = "/tmp/temp_audio.wav"
        mock_temp.close = MagicMock()
        mock_tempfile.return_value = mock_temp

        mock_get_metadata.return_value = {
            "duration_seconds": 30.0,
            "file_size_bytes": 1024000
        }

        mock_extract_audio.return_value = True
        mock_atranscription.side_effect = Exception("Transcription error")

        parser = VideoParser()
        result = await parser.parse("/fake/path/test.mp4")

        # Verify error is returned
        assert result["content"] == ""
        assert "Transcription error" in result["metadata"]["error"]

        # Verify temp file close was called
        assert mock_temp.close.called

    @pytest.mark.asyncio
    @patch('backend.parsers.video_parser.Path')
    @patch('backend.parsers.video_parser.get_video_metadata')
    @patch('backend.parsers.video_parser.extract_audio_from_video')
    @patch('backend.parsers.video_parser.atranscription')
    @patch('backend.parsers.video_parser.tempfile.NamedTemporaryFile')
    @patch('backend.parsers.video_parser.settings')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    async def test_parse_mov_format(
        self, mock_file, mock_settings, mock_tempfile, mock_atranscription,
        mock_extract_audio, mock_get_metadata, mock_path_class
    ):
        """Test parsing MOV (QuickTime) format"""
        mock_settings.VIDEO_FFMPEG_PATH = "ffmpeg"
        mock_settings.VIDEO_FFPROBE_PATH = "ffprobe"
        mock_settings.VIDEO_MAX_DURATION = 3600
        mock_settings.VIDEO_TEMP_DIR = "/tmp"
        mock_settings.STT_SERVICE = "whisper-1"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 5242880
        mock_path.suffix = ".mov"
        mock_path.name = "recording.mov"
        mock_path_class.return_value = mock_path

        mock_temp = MagicMock()
        mock_temp.name = "/tmp/temp_audio.wav"
        mock_temp.close = MagicMock()
        mock_tempfile.return_value = mock_temp

        mock_get_metadata.return_value = {
            "duration_seconds": 90.0,
            "file_size_bytes": 5242880,
            "format_name": "mov,mp4,m4a",
            "codec": "h264"
        }

        mock_extract_audio.return_value = True
        mock_atranscription.return_value = {
            "text": "MOV video transcription",
            "language": "en",
            "duration": 90.0
        }

        parser = VideoParser()
        result = await parser.parse("/fake/path/recording.mov")

        assert result["content"] == "MOV video transcription"
        assert result["metadata"]["file_format"] == "mov"
        assert result["metadata"]["transcription_success"] is True

    @pytest.mark.asyncio
    @patch('backend.parsers.video_parser.Path')
    @patch('backend.parsers.video_parser.get_video_metadata')
    @patch('backend.parsers.video_parser.extract_audio_from_video')
    @patch('backend.parsers.video_parser.atranscription')
    @patch('backend.parsers.video_parser.tempfile.NamedTemporaryFile')
    @patch('backend.parsers.video_parser.settings')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.video_parser.LITELLM_AVAILABLE', True)
    async def test_parse_with_groq_provider(
        self, mock_file, mock_settings, mock_tempfile, mock_atranscription,
        mock_extract_audio, mock_get_metadata, mock_path_class
    ):
        """Test video parsing with Groq STT provider"""
        mock_settings.VIDEO_FFMPEG_PATH = "ffmpeg"
        mock_settings.VIDEO_FFPROBE_PATH = "ffprobe"
        mock_settings.VIDEO_MAX_DURATION = 3600
        mock_settings.VIDEO_TEMP_DIR = "/tmp"
        mock_settings.STT_SERVICE = "groq/whisper-large-v3"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 2048000
        mock_path.suffix = ".mp4"
        mock_path.name = "video.mp4"
        mock_path_class.return_value = mock_path

        mock_temp = MagicMock()
        mock_temp.name = "/tmp/temp_audio.wav"
        mock_temp.close = MagicMock()
        mock_tempfile.return_value = mock_temp

        mock_get_metadata.return_value = {
            "duration_seconds": 60.0,
            "file_size_bytes": 2048000
        }

        mock_extract_audio.return_value = True
        mock_atranscription.return_value = {
            "text": "Groq transcription",
            "language": "en",
            "duration": 60.0
        }

        parser = VideoParser()
        result = await parser.parse("/fake/path/video.mp4")

        assert result["content"] == "Groq transcription"
        assert result["metadata"]["transcription_model"] == "groq/whisper-large-v3"
