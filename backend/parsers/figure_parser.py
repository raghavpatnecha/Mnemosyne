"""
Figure Parser for extracting and describing figures from documents.

Extracts figures/images from PDFs and DOCX files and generates descriptions
using OpenAI Vision API. Supports concurrent processing for efficiency.

Ported from RAGFlow's deepdoc/parser/figure_parser.py
"""

import asyncio
import base64
import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI, OpenAI

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class FigureResult:
    """Result of figure extraction and description."""

    index: int
    page: Optional[int]
    description: str
    image_data: bytes
    format: str
    position: Optional[Dict[str, float]] = None
    filename: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "index": self.index,
            "page": self.page,
            "description": self.description,
            "format": self.format,
            "position": self.position,
            "filename": self.filename,
            "confidence": self.confidence,
        }


class FigureParser:
    """
    Parser for extracting and describing figures from documents.

    Uses OpenAI Vision API (GPT-4o) to generate detailed descriptions
    of figures, charts, diagrams, and images in documents.

    Features:
    - Concurrent processing for multiple figures
    - Position tracking for figure placement
    - Support for various image formats (PNG, JPEG, WEBP)
    - Confidence scoring for description quality
    """

    SUPPORTED_FORMATS = {"png", "jpeg", "jpg", "webp", "gif"}
    MAX_CONCURRENT_REQUESTS = 5

    def __init__(
        self,
        model: str = None,  # Uses settings.VISION_MODEL if not provided
        max_concurrent: int = MAX_CONCURRENT_REQUESTS,
    ):
        """
        Initialize FigureParser.

        Args:
            model: OpenAI model to use for vision analysis
            max_concurrent: Maximum concurrent API requests
        """
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set - FigureParser will fail")

        self.async_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.sync_client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = model or settings.VISION_MODEL  # Use centralized config
        self.max_concurrent = max_concurrent
        self._semaphore: Optional[asyncio.Semaphore] = None

    def _get_semaphore(self) -> asyncio.Semaphore:
        """Get or create semaphore for concurrency control."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    def _encode_image(self, image_data: bytes) -> str:
        """Encode image bytes to base64 string."""
        return base64.b64encode(image_data).decode("utf-8")

    def _get_mime_type(self, format_str: str) -> str:
        """Get MIME type from format string."""
        format_lower = format_str.lower()
        if format_lower in ("jpg", "jpeg"):
            return "image/jpeg"
        elif format_lower == "png":
            return "image/png"
        elif format_lower == "webp":
            return "image/webp"
        elif format_lower == "gif":
            return "image/gif"
        return "image/png"  # Default

    async def describe_figure(
        self,
        image_data: bytes,
        image_format: str = "png",
        context: Optional[str] = None,
    ) -> str:
        """
        Generate description for a single figure using Vision API.

        Args:
            image_data: Raw image bytes
            image_format: Image format (png, jpeg, etc.)
            context: Optional document context for better descriptions

        Returns:
            Generated description string

        Raises:
            ValueError: If image data is invalid
        """
        if not image_data:
            raise ValueError("Image data is empty")

        base64_image = self._encode_image(image_data)
        mime_type = self._get_mime_type(image_format)

        # Build prompt with optional context
        prompt_text = (
            "Analyze this figure/image and provide:\n"
            "1. A detailed description of what is shown\n"
            "2. Key information, data, or text visible in the image\n"
            "3. Type of visualization (chart, diagram, photo, etc.)\n"
            "4. Any labels, legends, or annotations present\n\n"
            "Be concise but comprehensive. Focus on information that would "
            "be useful for understanding the document content."
        )

        if context:
            prompt_text = (
                f"Document context: {context[:500]}\n\n"
                f"{prompt_text}"
            )

        async with self._get_semaphore():
            try:
                response = await self.async_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_text},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{base64_image}",
                                        "detail": "high",
                                    },
                                },
                            ],
                        }
                    ],
                    max_completion_tokens=500,
                    temperature=0.1,
                )

                description = response.choices[0].message.content
                return description.strip() if description else ""

            except Exception as e:
                logger.error(f"Vision API error: {e}")
                raise

    async def process_figures(
        self,
        figures: List[Dict[str, Any]],
        context: Optional[str] = None,
    ) -> List[FigureResult]:
        """
        Process multiple figures concurrently.

        Args:
            figures: List of figure dictionaries with keys:
                - data: Raw image bytes
                - page: Page number (optional)
                - index: Figure index
                - format: Image format (optional, default: png)
                - position: Position info dict (optional)
                - filename: Original filename (optional)
            context: Optional document context for descriptions

        Returns:
            List of FigureResult objects with descriptions
        """
        if not figures:
            return []

        logger.info(f"Processing {len(figures)} figures with Vision API")

        async def process_single(figure: Dict[str, Any]) -> FigureResult:
            """Process a single figure."""
            index = figure.get("index", 0)
            page = figure.get("page")
            image_data = figure.get("data", b"")
            image_format = figure.get("format", "png")
            position = figure.get("position")
            filename = figure.get("filename")

            try:
                description = await self.describe_figure(
                    image_data=image_data,
                    image_format=image_format,
                    context=context,
                )
                confidence = 0.9 if len(description) > 50 else 0.5

            except Exception as e:
                logger.warning(f"Failed to describe figure {index}: {e}")
                description = f"[Figure {index + 1}]"
                confidence = 0.0

            return FigureResult(
                index=index,
                page=page,
                description=description,
                image_data=image_data,
                format=image_format,
                position=position,
                filename=filename,
                confidence=confidence,
            )

        # Process all figures concurrently
        tasks = [process_single(fig) for fig in figures]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and log them
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Figure {i} processing failed: {result}")
            else:
                valid_results.append(result)

        # Sort by page and index
        valid_results.sort(key=lambda r: (r.page or 0, r.index))

        logger.info(
            f"Successfully processed {len(valid_results)}/{len(figures)} figures"
        )

        return valid_results

    def process_figures_sync(
        self,
        figures: List[Dict[str, Any]],
        context: Optional[str] = None,
        max_workers: int = 3,
    ) -> List[FigureResult]:
        """
        Process multiple figures using ThreadPoolExecutor (sync version).

        For use in non-async contexts like Celery workers.

        Args:
            figures: List of figure dictionaries
            context: Optional document context
            max_workers: Max parallel threads

        Returns:
            List of FigureResult objects
        """
        if not figures:
            return []

        logger.info(f"Processing {len(figures)} figures (sync mode)")

        def process_single_sync(figure: Dict[str, Any]) -> Optional[FigureResult]:
            """Process a single figure synchronously."""
            index = figure.get("index", 0)
            page = figure.get("page")
            image_data = figure.get("data", b"")
            image_format = figure.get("format", "png")
            position = figure.get("position")
            filename = figure.get("filename")

            if not image_data:
                return None

            base64_image = self._encode_image(image_data)
            mime_type = self._get_mime_type(image_format)

            prompt_text = (
                "Analyze this figure and provide a concise description "
                "including what is shown, key data/text visible, and type "
                "of visualization."
            )

            if context:
                prompt_text = f"Context: {context[:300]}\n\n{prompt_text}"

            try:
                response = self.sync_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt_text},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:{mime_type};base64,{base64_image}",
                                        "detail": "high",
                                    },
                                },
                            ],
                        }
                    ],
                    max_completion_tokens=400,
                    temperature=0.1,
                )

                description = response.choices[0].message.content or ""
                confidence = 0.9 if len(description) > 50 else 0.5

            except Exception as e:
                logger.warning(f"Sync figure processing failed: {e}")
                description = f"[Figure {index + 1}]"
                confidence = 0.0

            return FigureResult(
                index=index,
                page=page,
                description=description.strip(),
                image_data=image_data,
                format=image_format,
                position=position,
                filename=filename,
                confidence=confidence,
            )

        results = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(process_single_sync, fig) for fig in figures
            ]
            for future in futures:
                try:
                    result = future.result(timeout=60)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Figure processing thread failed: {e}")

        results.sort(key=lambda r: (r.page or 0, r.index))
        return results

    @staticmethod
    def format_figures_as_markdown(results: List[FigureResult]) -> str:
        """
        Format figure descriptions as markdown text.

        Args:
            results: List of FigureResult objects

        Returns:
            Markdown formatted string with figure descriptions
        """
        if not results:
            return ""

        parts = []
        for result in results:
            page_info = f" (Page {result.page})" if result.page else ""
            parts.append(
                f"### Figure {result.index + 1}{page_info}\n\n"
                f"{result.description}\n"
            )

        return "\n".join(parts)
