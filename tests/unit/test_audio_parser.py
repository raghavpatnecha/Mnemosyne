"""
Unit tests for AudioParser

Tests:
- MIME type validation (can_parse)
- Successful transcription with LiteLLM
- Error handling (API failures, missing API key)
- Metadata extraction (duration, language, format)
- File size and format detection
- Multi-provider support via LiteLLM
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open, AsyncMock
from pathlib import Path

from backend.parsers.audio_parser import AudioParser


@pytest.mark.unit
class TestAudioParser:
    """Test suite for AudioParser with LiteLLM"""

    @patch('backend.parsers.audio_parser.settings')
    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_init_with_api_key(self, mock_settings):
        """Test initialization with valid API key"""
        mock_settings.OPENAI_API_KEY = "test_key"
        mock_settings.STT_SERVICE_API_KEY = ""
        mock_settings.STT_SERVICE = "whisper-1"
        mock_settings.STT_SERVICE_API_BASE = ""

        parser = AudioParser()

        assert parser.api_key == "test_key"
        assert parser.stt_service == "whisper-1"

    @patch('backend.parsers.audio_parser.settings')
    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_init_with_stt_specific_key(self, mock_settings):
        """Test initialization with STT-specific API key"""
        mock_settings.OPENAI_API_KEY = "openai_key"
        mock_settings.STT_SERVICE_API_KEY = "stt_specific_key"
        mock_settings.STT_SERVICE = "groq/whisper-large-v3"
        mock_settings.STT_SERVICE_API_BASE = "https://api.groq.com"

        parser = AudioParser()

        assert parser.api_key == "stt_specific_key"
        assert parser.stt_service == "groq/whisper-large-v3"
        assert parser.api_base == "https://api.groq.com"

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', False)
    def test_init_without_litellm(self):
        """Test initialization fails without LiteLLM"""
        with pytest.raises(ImportError, match="LiteLLM is required"):
            AudioParser()

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_valid_mpeg(self):
        """Test can_parse with audio/mpeg MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/mpeg") is True

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_valid_mp3(self):
        """Test can_parse with audio/mp3 MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/mp3") is True

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_valid_wav(self):
        """Test can_parse with audio/wav MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/wav") is True

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_valid_m4a(self):
        """Test can_parse with audio/m4a MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/m4a") is True

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_valid_flac(self):
        """Test can_parse with audio/flac MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/flac") is True

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_valid_webm(self):
        """Test can_parse with audio/webm MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/webm") is True

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_valid_ogg(self):
        """Test can_parse with audio/ogg MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/ogg") is True

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_generic_audio(self):
        """Test can_parse with generic audio/* MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/unknown") is True

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_invalid_video(self):
        """Test can_parse rejects video MIME type"""
        parser = AudioParser()
        assert parser.can_parse("video/mp4") is False

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_invalid_text(self):
        """Test can_parse rejects text MIME type"""
        parser = AudioParser()
        assert parser.can_parse("text/plain") is False

    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    def test_can_parse_invalid_image(self):
        """Test can_parse rejects image MIME type"""
        parser = AudioParser()
        assert parser.can_parse("image/png") is False

    @pytest.mark.asyncio
    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.atranscription')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    async def test_parse_success(self, mock_file, mock_atranscription, mock_path_class):
        """Test successful audio transcription with LiteLLM"""
        # Setup path mock
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 1024000
        mock_path.suffix = '.mp3'
        mock_path.name = 'test_audio.mp3'
        mock_path_class.return_value = mock_path

        # Mock LiteLLM transcription response (dict format)
        mock_atranscription.return_value = {
            "text": "This is a test transcription.",
            "language": "en",
            "duration": 45.7
        }

        parser = AudioParser()
        result = await parser.parse("/fake/path/test_audio.mp3")

        # Verify content
        assert result["content"] == "This is a test transcription."
        assert result["page_count"] is None

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["file_size_bytes"] == 1024000
        assert metadata["format"] == "mp3"
        assert metadata["original_filename"] == "test_audio.mp3"
        assert metadata["language"] == "en"
        assert metadata["duration_seconds"] == 45.7
        assert metadata["transcription_model"] == "whisper-1"
        assert metadata["transcription_success"] is True
        assert metadata["stt_provider"] == "whisper-1"

        # Verify LiteLLM was called
        assert mock_atranscription.called

    @pytest.mark.asyncio
    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.atranscription')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    async def test_parse_success_without_metadata(self, mock_file, mock_atranscription, mock_path_class):
        """Test transcription when API doesn't return duration/language"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 512000
        mock_path.suffix = '.wav'
        mock_path.name = 'recording.wav'
        mock_path_class.return_value = mock_path

        # Mock response without optional metadata
        mock_atranscription.return_value = {
            "text": "Transcription text"
        }

        parser = AudioParser()
        result = await parser.parse("/fake/path/recording.wav")

        assert result["content"] == "Transcription text"
        metadata = result["metadata"]
        assert metadata["language"] is None
        assert metadata["duration_seconds"] is None
        assert metadata["transcription_success"] is True

    @pytest.mark.asyncio
    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.atranscription')
    @patch('builtins.open', side_effect=IOError("File not found"))
    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    async def test_parse_file_read_error(self, mock_file, mock_atranscription, mock_path_class):
        """Test parse with file read error"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 1024
        mock_path.suffix = '.mp3'
        mock_path.name = 'test.mp3'
        mock_path_class.return_value = mock_path

        parser = AudioParser()
        result = await parser.parse("/fake/path/test.mp3")

        # Should return empty content with error in metadata
        assert result["content"] == ""
        assert result["page_count"] is None

        metadata = result["metadata"]
        assert metadata["transcription_success"] is False
        assert "File not found" in metadata["transcription_error"]
        assert metadata["error_type"] == "OSError"

    @pytest.mark.asyncio
    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.atranscription')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    async def test_parse_api_error(self, mock_file, mock_atranscription, mock_path_class):
        """Test parse with LiteLLM API error"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 2048
        mock_path.suffix = '.m4a'
        mock_path.name = 'audio.m4a'
        mock_path_class.return_value = mock_path

        # Mock API failure
        mock_atranscription.side_effect = Exception("API rate limit exceeded")

        parser = AudioParser()
        result = await parser.parse("/fake/path/audio.m4a")

        # Should return empty content with error
        assert result["content"] == ""
        assert result["page_count"] is None

        metadata = result["metadata"]
        assert metadata["transcription_success"] is False
        assert "API rate limit exceeded" in metadata["transcription_error"]
        assert metadata["error_type"] == "Exception"
        assert metadata["format"] == "m4a"

    @pytest.mark.asyncio
    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.atranscription')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    async def test_parse_empty_transcription(self, mock_file, mock_atranscription, mock_path_class):
        """Test parse with empty transcription result"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 1024
        mock_path.suffix = '.wav'
        mock_path.name = 'silence.wav'
        mock_path_class.return_value = mock_path

        # Mock empty transcription
        mock_atranscription.return_value = {
            "text": "",
            "language": "en",
            "duration": 10.0
        }

        parser = AudioParser()
        result = await parser.parse("/fake/path/silence.wav")

        assert result["content"] == ""
        assert result["metadata"]["transcription_success"] is True
        assert result["metadata"]["duration_seconds"] == 10.0

    @pytest.mark.asyncio
    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.atranscription')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    async def test_parse_different_languages(self, mock_file, mock_atranscription, mock_path_class):
        """Test parse with non-English language detection"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 2048000
        mock_path.suffix = '.mp3'
        mock_path.name = 'spanish.mp3'
        mock_path_class.return_value = mock_path

        # Mock Spanish transcription
        mock_atranscription.return_value = {
            "text": "Hola, esto es una prueba.",
            "language": "es",
            "duration": 5.2
        }

        parser = AudioParser()
        result = await parser.parse("/fake/path/spanish.mp3")

        assert result["content"] == "Hola, esto es una prueba."
        assert result["metadata"]["language"] == "es"
        assert result["metadata"]["transcription_success"] is True

    @pytest.mark.asyncio
    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.atranscription')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    async def test_parse_large_audio_file(self, mock_file, mock_atranscription, mock_path_class):
        """Test parse with large audio file"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 25000000  # 25 MB
        mock_path.suffix = '.wav'
        mock_path.name = 'podcast.wav'
        mock_path_class.return_value = mock_path

        mock_atranscription.return_value = {
            "text": "Long podcast transcription...",
            "language": "en",
            "duration": 1800.5  # 30 minutes
        }

        parser = AudioParser()
        result = await parser.parse("/fake/path/podcast.wav")

        assert result["metadata"]["file_size_bytes"] == 25000000
        assert result["metadata"]["duration_seconds"] == 1800.5
        assert result["metadata"]["transcription_success"] is True

    @pytest.mark.asyncio
    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.atranscription')
    @patch('backend.parsers.audio_parser.settings')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    async def test_parse_with_groq_provider(self, mock_file, mock_settings, mock_atranscription, mock_path_class):
        """Test transcription with Groq provider via LiteLLM"""
        mock_settings.STT_SERVICE = "groq/whisper-large-v3"
        mock_settings.STT_SERVICE_API_KEY = "groq_api_key"
        mock_settings.STT_SERVICE_API_BASE = ""
        mock_settings.OPENAI_API_KEY = ""

        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 512000
        mock_path.suffix = '.mp3'
        mock_path.name = 'test.mp3'
        mock_path_class.return_value = mock_path

        mock_atranscription.return_value = {
            "text": "Groq transcription",
            "language": "en",
            "duration": 12.3
        }

        parser = AudioParser()
        result = await parser.parse("/fake/path/test.mp3")

        assert result["content"] == "Groq transcription"
        assert result["metadata"]["stt_provider"] == "groq/whisper-large-v3"
        assert result["metadata"]["transcription_success"] is True

    @pytest.mark.asyncio
    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.atranscription')
    @patch('backend.parsers.audio_parser.settings')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    @patch('backend.parsers.audio_parser.LITELLM_AVAILABLE', True)
    async def test_parse_with_azure_provider(self, mock_file, mock_settings, mock_atranscription, mock_path_class):
        """Test transcription with Azure Whisper via LiteLLM"""
        mock_settings.STT_SERVICE = "azure/whisper"
        mock_settings.STT_SERVICE_API_KEY = "azure_key"
        mock_settings.STT_SERVICE_API_BASE = "https://my-azure.openai.azure.com"
        mock_settings.OPENAI_API_KEY = ""

        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 1024
        mock_path.suffix = '.wav'
        mock_path.name = 'azure_test.wav'
        mock_path_class.return_value = mock_path

        mock_atranscription.return_value = {
            "text": "Azure transcription",
            "language": "en",
            "duration": 8.5
        }

        parser = AudioParser()
        result = await parser.parse("/fake/path/azure_test.wav")

        assert result["content"] == "Azure transcription"
        assert result["metadata"]["stt_provider"] == "azure/whisper"
        assert result["metadata"]["transcription_model"] == "azure/whisper"
        assert result["metadata"]["transcription_success"] is True
