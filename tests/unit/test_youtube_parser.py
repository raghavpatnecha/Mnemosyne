"""
Unit tests for YouTubeParser

Tests:
- MIME type validation (can_parse)
- Video ID extraction from 4 URL formats
- Transcript fetching with timestamps
- Metadata fetching via oEmbed API
- Error handling (invalid URLs, missing captions, API failures)
- Multi-language transcript support
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from pathlib import Path
import aiohttp

from backend.parsers.youtube_parser import YouTubeParser


@pytest.mark.unit
class TestYouTubeParser:
    """Test suite for YouTubeParser with YouTube Transcript API"""

    def test_init(self):
        """Test initialization"""
        parser = YouTubeParser()
        assert parser is not None

    def test_can_parse_html(self):
        """Test can_parse with text/html MIME type"""
        parser = YouTubeParser()
        assert parser.can_parse("text/html") is True

    def test_can_parse_youtube(self):
        """Test can_parse with video/youtube MIME type"""
        parser = YouTubeParser()
        assert parser.can_parse("video/youtube") is True

    def test_can_parse_x_youtube(self):
        """Test can_parse with application/x-youtube MIME type"""
        parser = YouTubeParser()
        assert parser.can_parse("application/x-youtube") is True

    def test_can_parse_invalid_video(self):
        """Test can_parse rejects video/mp4 MIME type"""
        parser = YouTubeParser()
        assert parser.can_parse("video/mp4") is False

    def test_can_parse_invalid_audio(self):
        """Test can_parse rejects audio MIME type"""
        parser = YouTubeParser()
        assert parser.can_parse("audio/mpeg") is False

    def test_can_parse_invalid_application(self):
        """Test can_parse rejects application/pdf MIME type"""
        parser = YouTubeParser()
        assert parser.can_parse("application/pdf") is False

    def test_extract_video_id_youtu_be(self):
        """Test video ID extraction from youtu.be short URL"""
        parser = YouTubeParser()
        video_id = parser.extract_video_id("https://youtu.be/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_watch(self):
        """Test video ID extraction from youtube.com/watch URL"""
        parser = YouTubeParser()
        video_id = parser.extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_watch_with_params(self):
        """Test video ID extraction with additional query parameters"""
        parser = YouTubeParser()
        video_id = parser.extract_video_id(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PLtest"
        )
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_embed(self):
        """Test video ID extraction from youtube.com/embed URL"""
        parser = YouTubeParser()
        video_id = parser.extract_video_id("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_v_format(self):
        """Test video ID extraction from youtube.com/v URL"""
        parser = YouTubeParser()
        video_id = parser.extract_video_id("https://www.youtube.com/v/dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_mobile(self):
        """Test video ID extraction from m.youtube.com URL"""
        parser = YouTubeParser()
        video_id = parser.extract_video_id("https://m.youtube.com/watch?v=dQw4w9WgXcQ")
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid_url(self):
        """Test video ID extraction from invalid URL returns None"""
        parser = YouTubeParser()
        video_id = parser.extract_video_id("https://example.com/video")
        assert video_id is None

    def test_extract_video_id_missing_v_param(self):
        """Test video ID extraction from watch URL without v parameter"""
        parser = YouTubeParser()
        video_id = parser.extract_video_id("https://www.youtube.com/watch?list=PLtest")
        assert video_id is None

    def test_extract_video_id_malformed(self):
        """Test video ID extraction from malformed URL"""
        parser = YouTubeParser()
        video_id = parser.extract_video_id("not-a-url")
        assert video_id is None

    def test_format_timestamp_zero(self):
        """Test timestamp formatting at 0 seconds"""
        parser = YouTubeParser()
        timestamp = parser.format_timestamp(0)
        assert timestamp == "00:00"

    def test_format_timestamp_seconds(self):
        """Test timestamp formatting for seconds only"""
        parser = YouTubeParser()
        timestamp = parser.format_timestamp(45)
        assert timestamp == "00:45"

    def test_format_timestamp_minutes(self):
        """Test timestamp formatting for minutes and seconds"""
        parser = YouTubeParser()
        timestamp = parser.format_timestamp(125)  # 2:05
        assert timestamp == "02:05"

    def test_format_timestamp_hours(self):
        """Test timestamp formatting for hours (outputs MM:SS)"""
        parser = YouTubeParser()
        timestamp = parser.format_timestamp(3665)  # 61:05
        assert timestamp == "61:05"

    def test_format_timestamp_long_video(self):
        """Test timestamp formatting for multi-hour video (outputs MM:SS)"""
        parser = YouTubeParser()
        timestamp = parser.format_timestamp(7384)  # 123:04
        assert timestamp == "123:04"

    def test_is_youtube_url_valid_youtu_be(self):
        """Test YouTube URL detection with youtu.be"""
        parser = YouTubeParser()
        assert parser.is_youtube_url("https://youtu.be/test") is True

    def test_is_youtube_url_valid_youtube_com(self):
        """Test YouTube URL detection with youtube.com"""
        parser = YouTubeParser()
        assert parser.is_youtube_url("https://www.youtube.com/watch?v=test") is True

    def test_is_youtube_url_valid_mobile(self):
        """Test YouTube URL detection with m.youtube.com"""
        parser = YouTubeParser()
        assert parser.is_youtube_url("https://m.youtube.com/watch?v=test") is True

    def test_is_youtube_url_invalid(self):
        """Test YouTube URL detection with non-YouTube URL"""
        parser = YouTubeParser()
        assert parser.is_youtube_url("https://vimeo.com/test") is False
        assert parser.is_youtube_url("https://example.com") is False
        assert parser.is_youtube_url("not-a-url") is False

    @pytest.mark.asyncio
    async def test_fetch_video_metadata_success(self):
        """Test successful metadata fetching via oEmbed API"""
        parser = YouTubeParser()

        # Create proper async context manager mocks
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "title": "Test Video Title",
            "author_name": "Test Channel",
            "thumbnail_url": "https://i.ytimg.com/vi/test/maxresdefault.jpg"
        })
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('backend.parsers.youtube_parser.aiohttp.ClientSession', return_value=mock_session):
            metadata = await parser.fetch_video_metadata("test_video_id")

        assert metadata["title"] == "Test Video Title"
        assert metadata["author"] == "Test Channel"
        assert metadata["thumbnail"] == "https://i.ytimg.com/vi/test/maxresdefault.jpg"

    @pytest.mark.asyncio
    @patch('backend.parsers.youtube_parser.Path')
    @patch('backend.parsers.youtube_parser.YouTubeTranscriptApi.get_transcript')
    async def test_parse_success(self, mock_get_transcript, mock_path_class):
        """Test successful full parse workflow"""
        # Setup path mock
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.read_text.return_value = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        mock_path_class.return_value = mock_path

        # Mock transcript with duration
        mock_get_transcript.return_value = [
            {"start": 0.0, "text": "Never gonna give you up", "duration": 3.0},
            {"start": 3.5, "text": "Never gonna let you down", "duration": 2.5}
        ]

        # Mock metadata using proper async context managers
        mock_metadata_response = MagicMock()
        mock_metadata_response.status = 200
        mock_metadata_response.json = AsyncMock(return_value={
            "title": "Rick Astley - Never Gonna Give You Up",
            "author_name": "Rick Astley",
            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
        })
        mock_metadata_response.__aenter__ = AsyncMock(return_value=mock_metadata_response)
        mock_metadata_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_metadata_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch('backend.parsers.youtube_parser.aiohttp.ClientSession', return_value=mock_session):
            parser = YouTubeParser()
            result = await parser.parse("/fake/path/youtube_url.txt")

        # Verify content
        assert "[00:00] Never gonna give you up" in result["content"]
        assert "[00:03] Never gonna let you down" in result["content"]
        assert result["page_count"] is None

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["video_id"] == "dQw4w9WgXcQ"
        assert metadata["title"] == "Rick Astley - Never Gonna Give You Up"
        assert metadata["author"] == "Rick Astley"
        assert metadata["url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        assert metadata["transcript_segments"] == 2

    @pytest.mark.asyncio
    @patch('backend.parsers.youtube_parser.Path')
    async def test_parse_file_not_found(self, mock_path_class):
        """Test parse with non-existent file (treated as direct URL)"""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        parser = YouTubeParser()
        result = await parser.parse("/fake/path/missing.txt")

        assert result["content"] == ""
        assert "Could not extract YouTube video ID" in result["metadata"]["error"]

    @pytest.mark.asyncio
    @patch('backend.parsers.youtube_parser.Path')
    async def test_parse_invalid_url(self, mock_path_class):
        """Test parse with non-YouTube URL"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.read_text.return_value = "https://example.com/video"
        mock_path_class.return_value = mock_path

        parser = YouTubeParser()
        result = await parser.parse("/fake/path/url.txt")

        assert result["content"] == ""
        assert "Could not extract YouTube video ID" in result["metadata"]["error"]

    @pytest.mark.asyncio
    @patch('backend.parsers.youtube_parser.Path')
    @patch('backend.parsers.youtube_parser.YouTubeTranscriptApi.get_transcript')
    async def test_parse_transcript_unavailable(self, mock_get_transcript, mock_path_class):
        """Test parse when transcript is unavailable"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.is_file.return_value = True
        mock_path.read_text.return_value = "https://youtu.be/test123"
        mock_path_class.return_value = mock_path

        # Mock the specific exception that would be raised
        mock_get_transcript.side_effect = Exception(
            "\nCould not retrieve a transcript for the video https://www.youtube.com/watch?v=test123! "
            "This is most likely caused by:\n\nSubtitles are disabled for this video"
        )

        parser = YouTubeParser()
        result = await parser.parse("/fake/path/url.txt")

        assert result["content"] == ""
        assert "Failed to extract transcript" in result["metadata"]["error"]
        assert result["metadata"]["video_id"] == "test123"
