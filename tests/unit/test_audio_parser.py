"""
Unit tests for AudioParser

Tests:
- MIME type validation (can_parse)
- Successful transcription with Whisper API
- Error handling (API failures, missing API key)
- Metadata extraction (duration, language, format)
- File size and format detection
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path

from backend.parsers.audio_parser import AudioParser


@pytest.mark.unit
class TestAudioParser:
    """Test suite for AudioParser"""

    @patch('backend.parsers.audio_parser.settings')
    @patch('backend.parsers.audio_parser.OpenAI')
    def test_init_with_api_key(self, mock_openai_class, mock_settings):
        """Test initialization with valid API key"""
        mock_settings.OPENAI_API_KEY = "test_key"

        parser = AudioParser()

        mock_openai_class.assert_called_once_with(api_key="test_key")
        assert parser.client is not None

    @patch('backend.parsers.audio_parser.settings')
    @patch('backend.parsers.audio_parser.OpenAI')
    def test_init_without_api_key(self, mock_openai_class, mock_settings):
        """Test initialization without API key logs warning"""
        mock_settings.OPENAI_API_KEY = None

        parser = AudioParser()

        mock_openai_class.assert_called_once_with(api_key=None)

    def test_can_parse_valid_mpeg(self):
        """Test can_parse with audio/mpeg MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/mpeg") is True

    def test_can_parse_valid_mp3(self):
        """Test can_parse with audio/mp3 MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/mp3") is True

    def test_can_parse_valid_wav(self):
        """Test can_parse with audio/wav MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/wav") is True

    def test_can_parse_valid_m4a(self):
        """Test can_parse with audio/m4a MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/m4a") is True

    def test_can_parse_valid_flac(self):
        """Test can_parse with audio/flac MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/flac") is True

    def test_can_parse_valid_webm(self):
        """Test can_parse with audio/webm MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/webm") is True

    def test_can_parse_valid_ogg(self):
        """Test can_parse with audio/ogg MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/ogg") is True

    def test_can_parse_generic_audio(self):
        """Test can_parse with generic audio/* MIME type"""
        parser = AudioParser()
        assert parser.can_parse("audio/unknown") is True

    def test_can_parse_invalid_video(self):
        """Test can_parse rejects video MIME type"""
        parser = AudioParser()
        assert parser.can_parse("video/mp4") is False

    def test_can_parse_invalid_text(self):
        """Test can_parse rejects text MIME type"""
        parser = AudioParser()
        assert parser.can_parse("text/plain") is False

    def test_can_parse_invalid_image(self):
        """Test can_parse rejects image MIME type"""
        parser = AudioParser()
        assert parser.can_parse("image/png") is False

    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    def test_parse_success(self, mock_file, mock_openai_class, mock_path_class):
        """Test successful audio transcription"""
        # Setup path mock
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 1024000
        mock_path.suffix = '.mp3'
        mock_path.name = 'test_audio.mp3'
        mock_path_class.return_value = mock_path

        # Setup OpenAI mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock transcription response
        mock_transcript = MagicMock()
        mock_transcript.text = "This is a test transcription."
        mock_transcript.language = "en"
        mock_transcript.duration = 45.7
        mock_client.audio.transcriptions.create.return_value = mock_transcript

        parser = AudioParser()
        result = parser.parse("/fake/path/test_audio.mp3")

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

        # Verify API call
        mock_client.audio.transcriptions.create.assert_called_once_with(
            model="whisper-1",
            file=mock_file.return_value,
            response_format="verbose_json"
        )

    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    def test_parse_success_without_metadata(self, mock_file, mock_openai_class, mock_path_class):
        """Test transcription when API doesn't return duration/language"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 512000
        mock_path.suffix = '.wav'
        mock_path.name = 'recording.wav'
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock transcript without duration/language attributes
        mock_transcript = MagicMock()
        mock_transcript.text = "Transcription text"
        del mock_transcript.language
        del mock_transcript.duration
        mock_client.audio.transcriptions.create.return_value = mock_transcript

        parser = AudioParser()
        result = parser.parse("/fake/path/recording.wav")

        assert result["content"] == "Transcription text"
        metadata = result["metadata"]
        assert metadata["language"] is None
        assert metadata["duration_seconds"] is None
        assert metadata["transcription_success"] is True

    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.OpenAI')
    @patch('builtins.open', side_effect=IOError("File not found"))
    def test_parse_file_read_error(self, mock_file, mock_openai_class, mock_path_class):
        """Test parse with file read error"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 1024
        mock_path.suffix = '.mp3'
        mock_path.name = 'test.mp3'
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        parser = AudioParser()
        result = parser.parse("/fake/path/test.mp3")

        # Should return empty content with error in metadata
        assert result["content"] == ""
        assert result["page_count"] is None

        metadata = result["metadata"]
        assert metadata["transcription_success"] is False
        assert "File not found" in metadata["transcription_error"]
        assert metadata["error_type"] == "OSError"

    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    def test_parse_api_error(self, mock_file, mock_openai_class, mock_path_class):
        """Test parse with OpenAI API error"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 2048
        mock_path.suffix = '.m4a'
        mock_path.name = 'audio.m4a'
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock API failure
        mock_client.audio.transcriptions.create.side_effect = Exception("API rate limit exceeded")

        parser = AudioParser()
        result = parser.parse("/fake/path/audio.m4a")

        # Should return empty content with error
        assert result["content"] == ""
        assert result["page_count"] is None

        metadata = result["metadata"]
        assert metadata["transcription_success"] is False
        assert "API rate limit exceeded" in metadata["transcription_error"]
        assert metadata["error_type"] == "Exception"
        assert metadata["format"] == "m4a"

    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    def test_parse_empty_transcription(self, mock_file, mock_openai_class, mock_path_class):
        """Test parse with empty transcription result"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 1024
        mock_path.suffix = '.wav'
        mock_path.name = 'silence.wav'
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock empty transcription
        mock_transcript = MagicMock()
        mock_transcript.text = ""
        mock_transcript.language = "en"
        mock_transcript.duration = 10.0
        mock_client.audio.transcriptions.create.return_value = mock_transcript

        parser = AudioParser()
        result = parser.parse("/fake/path/silence.wav")

        assert result["content"] == ""
        assert result["metadata"]["transcription_success"] is True
        assert result["metadata"]["duration_seconds"] == 10.0

    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    def test_parse_different_languages(self, mock_file, mock_openai_class, mock_path_class):
        """Test parse with non-English language detection"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 2048000
        mock_path.suffix = '.mp3'
        mock_path.name = 'spanish.mp3'
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock Spanish transcription
        mock_transcript = MagicMock()
        mock_transcript.text = "Hola, esto es una prueba."
        mock_transcript.language = "es"
        mock_transcript.duration = 5.2
        mock_client.audio.transcriptions.create.return_value = mock_transcript

        parser = AudioParser()
        result = parser.parse("/fake/path/spanish.mp3")

        assert result["content"] == "Hola, esto es una prueba."
        assert result["metadata"]["language"] == "es"
        assert result["metadata"]["transcription_success"] is True

    @patch('backend.parsers.audio_parser.Path')
    @patch('backend.parsers.audio_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'audio_data')
    def test_parse_large_audio_file(self, mock_file, mock_openai_class, mock_path_class):
        """Test parse with large audio file"""
        mock_path = MagicMock()
        mock_path.stat.return_value.st_size = 25000000  # 25 MB
        mock_path.suffix = '.wav'
        mock_path.name = 'podcast.wav'
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_transcript = MagicMock()
        mock_transcript.text = "Long podcast transcription..."
        mock_transcript.language = "en"
        mock_transcript.duration = 1800.5  # 30 minutes
        mock_client.audio.transcriptions.create.return_value = mock_transcript

        parser = AudioParser()
        result = parser.parse("/fake/path/podcast.wav")

        assert result["metadata"]["file_size_bytes"] == 25000000
        assert result["metadata"]["duration_seconds"] == 1800.5
        assert result["metadata"]["transcription_success"] is True
