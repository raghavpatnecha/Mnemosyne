"""
Image Parser using OpenAI Vision API
Extracts visual descriptions and text from images (PNG, JPG, JPEG, WEBP)
"""

import base64
import logging
from pathlib import Path
from typing import Dict, Any

from openai import OpenAI, OpenAIError
from backend.config import settings

logger = logging.getLogger(__name__)


class ImageParser:
    """Parser for images using OpenAI Vision API (GPT-4 Vision)"""

    SUPPORTED_FORMATS = {
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
    }

    def __init__(self):
        """Initialize ImageParser with OpenAI client"""
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set - ImageParser will fail at parse time")
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.VISION_MODEL  # Use centralized config

    def can_parse(self, content_type: str) -> bool:
        """
        Check if this parser can handle the content type

        Args:
            content_type: MIME type (e.g., "image/png")

        Returns:
            True if content type is supported, False otherwise
        """
        if not content_type:
            return False
        if not content_type:
            return False
        return content_type.lower() in self.SUPPORTED_FORMATS

    def _encode_image(self, file_path: str) -> str:
        """
        Encode image file to base64 string

        Args:
            file_path: Path to image file

        Returns:
            Base64 encoded image string

        Raises:
            FileNotFoundError: If image file doesn't exist
            IOError: If image cannot be read
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        try:
            with open(file_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to encode image {file_path}: {e}")
            raise IOError(f"Failed to read image file: {e}") from e

    def _get_image_format(self, file_path: str) -> str:
        """
        Determine image format from file extension

        Args:
            file_path: Path to image file

        Returns:
            MIME type string (e.g., "image/png")
        """
        extension = Path(file_path).suffix.lower()
        format_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }
        return format_map.get(extension, "image/jpeg")

    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse image and extract visual description and text using OpenAI Vision API

        Args:
            file_path: Path to image file

        Returns:
            Dict with:
                - content: Extracted description and text from image
                - metadata: Image metadata (format, model used)
                - page_count: Always None for images

        Raises:
            OpenAIError: If API call fails
            FileNotFoundError: If image file doesn't exist
            ValueError: If OpenAI API key is not configured
        """
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY not configured. Please set it in environment variables."
            )

        try:
            base64_image = self._encode_image(file_path)
            image_format = self._get_image_format(file_path)

            logger.info(f"Parsing image: {file_path} with OpenAI Vision API")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Analyze this image and provide:\n"
                                    "1. A detailed description of what you see in the image\n"
                                    "2. Extract ALL visible text (if any) from the image\n"
                                    "3. Identify any charts, diagrams, or data visualizations\n\n"
                                    "Format your response clearly with sections for description and extracted text."
                                ),
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{image_format};base64,{base64_image}",
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_completion_tokens=1000,
                temperature=0.1,
            )

            content = response.choices[0].message.content

            if not content:
                logger.warning(f"Empty response from Vision API for {file_path}")
                content = ""

            metadata = {
                "image_format": image_format,
                "model": self.model,
                "file_size": Path(file_path).stat().st_size,
                "file_name": Path(file_path).name,
            }

            logger.info(f"Successfully parsed image: {file_path}")

            return {
                "content": content,
                "metadata": metadata,
                "page_count": None,
            }

        except OpenAIError as e:
            logger.error(f"OpenAI API error while parsing {file_path}: {e}")
            raise OpenAIError(
                f"Failed to parse image with Vision API: {e}"
            ) from e
        except FileNotFoundError as e:
            logger.error(f"Image file not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing image {file_path}: {e}")
            raise RuntimeError(f"Failed to parse image: {e}") from e
