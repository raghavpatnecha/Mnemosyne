"""
Unit tests for ImageParser

Tests:
- MIME type validation (can_parse)
- Successful image analysis with Vision API
- Error handling (API failures, missing API key, file not found)
- Base64 encoding
- Image format detection
- Metadata extraction
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path
import base64

from backend.parsers.image_parser import ImageParser
from openai import OpenAIError


@pytest.mark.unit
class TestImageParser:
    """Test suite for ImageParser"""

    @patch('backend.parsers.image_parser.settings')
    @patch('backend.parsers.image_parser.OpenAI')
    async def test_init_with_api_key(self, mock_openai_class, mock_settings):
        """Test initialization with valid API key"""
        mock_settings.OPENAI_API_KEY = "test_key"

        parser = ImageParser()

        mock_openai_class.assert_called_once_with(api_key="test_key")
        assert parser.client is not None
        assert parser.model == "gpt-4o"

    @patch('backend.parsers.image_parser.settings')
    @patch('backend.parsers.image_parser.OpenAI')
    async def test_init_without_api_key(self, mock_openai_class, mock_settings):
        """Test initialization without API key logs warning"""
        mock_settings.OPENAI_API_KEY = None

        parser = ImageParser()

        mock_openai_class.assert_called_once_with(api_key=None)

    async def test_can_parse_png(self):
        """Test can_parse with PNG MIME type"""
        parser = ImageParser()
        assert parser.can_parse("image/png") is True

    async def test_can_parse_jpeg(self):
        """Test can_parse with JPEG MIME type"""
        parser = ImageParser()
        assert parser.can_parse("image/jpeg") is True

    async def test_can_parse_jpg(self):
        """Test can_parse with JPG MIME type"""
        parser = ImageParser()
        assert parser.can_parse("image/jpg") is True

    async def test_can_parse_webp(self):
        """Test can_parse with WEBP MIME type"""
        parser = ImageParser()
        assert parser.can_parse("image/webp") is True

    async def test_can_parse_case_insensitive(self):
        """Test can_parse is case insensitive"""
        parser = ImageParser()
        assert parser.can_parse("IMAGE/PNG") is True
        assert parser.can_parse("Image/Jpeg") is True

    async def test_can_parse_invalid_gif(self):
        """Test can_parse rejects GIF MIME type"""
        parser = ImageParser()
        assert parser.can_parse("image/gif") is False

    async def test_can_parse_invalid_svg(self):
        """Test can_parse rejects SVG MIME type"""
        parser = ImageParser()
        assert parser.can_parse("image/svg+xml") is False

    async def test_can_parse_invalid_text(self):
        """Test can_parse rejects text MIME type"""
        parser = ImageParser()
        assert parser.can_parse("text/plain") is False

    async def test_can_parse_invalid_pdf(self):
        """Test can_parse rejects PDF MIME type"""
        parser = ImageParser()
        assert parser.can_parse("application/pdf") is False

    @patch('backend.parsers.image_parser.Path')
    @patch('builtins.open', new_callable=mock_open, read_data=b'fake_image_data')
    async def test_encode_image_success(self, mock_file, mock_path_class):
        """Test successful image encoding to base64"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        parser = ImageParser()
        encoded = parser._encode_image("/fake/path/image.png")

        expected = base64.b64encode(b'fake_image_data').decode('utf-8')
        assert encoded == expected
        mock_file.assert_called_once_with("/fake/path/image.png", "rb")

    @patch('backend.parsers.image_parser.Path')
    async def test_encode_image_file_not_found(self, mock_path_class):
        """Test encoding raises FileNotFoundError for missing file"""
        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        parser = ImageParser()

        with pytest.raises(FileNotFoundError, match="Image file not found"):
            parser._encode_image("/fake/path/missing.png")

    @patch('backend.parsers.image_parser.Path')
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    async def test_encode_image_read_error(self, mock_file, mock_path_class):
        """Test encoding raises IOError when file cannot be read"""
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        parser = ImageParser()

        with pytest.raises(IOError, match="Failed to read image file"):
            parser._encode_image("/fake/path/protected.png")

    async def test_get_image_format_png(self):
        """Test format detection for PNG files"""
        parser = ImageParser()
        assert parser._get_image_format("/path/to/image.png") == "image/png"

    async def test_get_image_format_jpg(self):
        """Test format detection for JPG files"""
        parser = ImageParser()
        assert parser._get_image_format("/path/to/photo.jpg") == "image/jpeg"

    async def test_get_image_format_jpeg(self):
        """Test format detection for JPEG files"""
        parser = ImageParser()
        assert parser._get_image_format("/path/to/photo.jpeg") == "image/jpeg"

    async def test_get_image_format_webp(self):
        """Test format detection for WEBP files"""
        parser = ImageParser()
        assert parser._get_image_format("/path/to/image.webp") == "image/webp"

    async def test_get_image_format_unknown(self):
        """Test format detection defaults to JPEG for unknown"""
        parser = ImageParser()
        assert parser._get_image_format("/path/to/file.bmp") == "image/jpeg"

    async def test_get_image_format_case_insensitive(self):
        """Test format detection is case insensitive"""
        parser = ImageParser()
        assert parser._get_image_format("/path/to/IMAGE.PNG") == "image/png"
        assert parser._get_image_format("/path/to/PHOTO.JPG") == "image/jpeg"

    @patch('backend.parsers.image_parser.settings')
    @patch('backend.parsers.image_parser.Path')
    @patch('backend.parsers.image_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    @pytest.mark.asyncio
    async def test_parse_success(self, mock_file, mock_openai_class, mock_path_class, mock_settings):
        """Test successful image parsing with Vision API"""
        mock_settings.OPENAI_API_KEY = "test_key"

        # Setup path mock
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 1024000
        mock_path.name = "screenshot.png"
        mock_path.suffix = ".png"
        mock_path_class.return_value = mock_path

        # Setup OpenAI mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock Vision API response
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = (
            "Description: This image shows a dashboard with various metrics.\n\n"
            "Extracted Text:\n- Total Users: 1,234\n- Revenue: $56,789\n- Growth: +12%"
        )
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        parser = ImageParser()
        result = await parser.parse("/fake/path/screenshot.png")

        # Verify content
        assert "dashboard" in result["content"]
        assert "Total Users" in result["content"]
        assert result["page_count"] is None

        # Verify metadata
        metadata = result["metadata"]
        assert metadata["image_format"] == "image/png"
        assert metadata["model"] == "gpt-4o"
        assert metadata["file_size"] == 1024000
        assert metadata["file_name"] == "screenshot.png"

        # Verify API call
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["model"] == "gpt-4o"
        assert call_args.kwargs["max_completion_tokens"] == 1000
        assert call_args.kwargs["temperature"] == 0.1

    @patch('backend.parsers.image_parser.settings')
    @patch('backend.parsers.image_parser.Path')
    @patch('backend.parsers.image_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    @pytest.mark.asyncio
    async def test_parse_empty_response(self, mock_file, mock_openai_class, mock_path_class, mock_settings):
        """Test parsing with empty API response"""
        mock_settings.OPENAI_API_KEY = "test_key"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 512000
        mock_path.name = "blank.png"
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock empty response
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = None
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        parser = ImageParser()
        result = await parser.parse("/fake/path/blank.png")

        assert result["content"] == ""
        assert result["metadata"]["file_name"] == "blank.png"

    @patch('backend.parsers.image_parser.settings')
    @patch('backend.parsers.image_parser.OpenAI')
    @pytest.mark.asyncio
    async def test_parse_missing_api_key(self, mock_openai_class, mock_settings):
        """Test parse raises ValueError when API key is missing"""
        mock_settings.OPENAI_API_KEY = None

        parser = ImageParser()

        with pytest.raises(ValueError, match="OPENAI_API_KEY not configured"):
            await parser.parse("/fake/path/image.png")

    @patch('backend.parsers.image_parser.settings')
    @patch('backend.parsers.image_parser.Path')
    @pytest.mark.asyncio
    async def test_parse_file_not_found(self, mock_path_class, mock_settings):
        """Test parse raises FileNotFoundError for missing file"""
        mock_settings.OPENAI_API_KEY = "test_key"

        mock_path = MagicMock()
        mock_path.exists.return_value = False
        mock_path_class.return_value = mock_path

        parser = ImageParser()

        with pytest.raises(FileNotFoundError):
            await parser.parse("/fake/path/missing.png")

    @patch('backend.parsers.image_parser.settings')
    @patch('backend.parsers.image_parser.Path')
    @patch('backend.parsers.image_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'image_data')
    @pytest.mark.asyncio
    async def test_parse_openai_error(self, mock_file, mock_openai_class, mock_path_class, mock_settings):
        """Test parse raises OpenAIError on API failure"""
        mock_settings.OPENAI_API_KEY = "test_key"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 1024
        mock_path.name = "test.png"
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        # Mock API error
        mock_client.chat.completions.create.side_effect = OpenAIError("Rate limit exceeded")

        parser = ImageParser()

        with pytest.raises(OpenAIError, match="Failed to parse image with Vision API"):
            await parser.parse("/fake/path/test.png")

    @patch('backend.parsers.image_parser.settings')
    @patch('backend.parsers.image_parser.Path')
    @patch('backend.parsers.image_parser.OpenAI')
    @patch('builtins.open', side_effect=Exception("Unexpected error"))
    @pytest.mark.asyncio
    async def test_parse_unexpected_error(self, mock_file, mock_openai_class, mock_path_class, mock_settings):
        """Test parse raises RuntimeError on unexpected errors"""
        mock_settings.OPENAI_API_KEY = "test_key"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path_class.return_value = mock_path

        parser = ImageParser()

        with pytest.raises(RuntimeError, match="Failed to parse image"):
            await parser.parse("/fake/path/test.png")

    @patch('backend.parsers.image_parser.settings')
    @patch('backend.parsers.image_parser.Path')
    @patch('backend.parsers.image_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'large_image_data')
    @pytest.mark.asyncio
    async def test_parse_large_image(self, mock_file, mock_openai_class, mock_path_class, mock_settings):
        """Test parsing large image file"""
        mock_settings.OPENAI_API_KEY = "test_key"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 5242880  # 5 MB
        mock_path.name = "high_res.png"
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "High resolution image analysis"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        parser = ImageParser()
        result = await parser.parse("/fake/path/high_res.png")

        assert result["metadata"]["file_size"] == 5242880
        assert result["content"] == "High resolution image analysis"

    @patch('backend.parsers.image_parser.settings')
    @patch('backend.parsers.image_parser.Path')
    @patch('backend.parsers.image_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'jpeg_data')
    @pytest.mark.asyncio
    async def test_parse_jpeg_file(self, mock_file, mock_openai_class, mock_path_class, mock_settings):
        """Test parsing JPEG file with correct format detection"""
        mock_settings.OPENAI_API_KEY = "test_key"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 2048000
        mock_path.name = "photo.jpg"
        mock_path.suffix = ".jpg"
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "A beautiful landscape photo"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        parser = ImageParser()
        result = await parser.parse("/fake/path/photo.jpg")

        assert result["metadata"]["image_format"] == "image/jpeg"
        assert "landscape" in result["content"]

    @patch('backend.parsers.image_parser.settings')
    @patch('backend.parsers.image_parser.Path')
    @patch('backend.parsers.image_parser.OpenAI')
    @patch('builtins.open', new_callable=mock_open, read_data=b'webp_data')
    @pytest.mark.asyncio
    async def test_parse_webp_file(self, mock_file, mock_openai_class, mock_path_class, mock_settings):
        """Test parsing WEBP file"""
        mock_settings.OPENAI_API_KEY = "test_key"

        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.stat.return_value.st_size = 512000
        mock_path.name = "modern.webp"
        mock_path.suffix = ".webp"
        mock_path_class.return_value = mock_path

        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Modern format image"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_response

        parser = ImageParser()
        result = await parser.parse("/fake/path/modern.webp")

        assert result["metadata"]["image_format"] == "image/webp"
        assert result["content"] == "Modern format image"
