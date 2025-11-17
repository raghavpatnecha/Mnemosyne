"""
Docling Parser for documents (PDF, DOCX, PPTX)
Advanced document parsing with layout preservation and image extraction
"""

from pathlib import Path
from typing import Dict, Any, List
from docling.document_converter import DocumentConverter
import logging

logger = logging.getLogger(__name__)


class DoclingParser:
    """Parser for documents using Docling (PDF, DOCX, PPTX, etc.)"""

    SUPPORTED_FORMATS = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.ms-powerpoint",
    }

    def __init__(self):
        self.converter = DocumentConverter()

    def can_parse(self, content_type: str) -> bool:
        """Check if this parser can handle the content type"""
        return content_type in self.SUPPORTED_FORMATS

    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse document and extract text + images

        Args:
            file_path: Path to document file

        Returns:
            Dict with:
                - content: Extracted text
                - metadata: Document metadata
                - page_count: Number of pages (if applicable)
                - images: List of extracted images (bytes + metadata)
        """
        result = self.converter.convert(file_path)

        content = result.document.export_to_markdown()

        # Extract images from document
        images = []
        try:
            if hasattr(result.document, "pages"):
                for page_num, page in enumerate(result.document.pages, start=1):
                    # Check if page has images/pictures
                    if hasattr(page, "pictures") and page.pictures:
                        for img_idx, picture in enumerate(page.pictures):
                            try:
                                # Extract image data
                                if hasattr(picture, "image") and picture.image:
                                    img_data = picture.image.pil_image  # PIL Image object

                                    # Convert PIL image to bytes
                                    import io
                                    img_bytes = io.BytesIO()
                                    img_data.save(img_bytes, format='PNG')
                                    img_bytes.seek(0)

                                    images.append({
                                        "data": img_bytes.read(),
                                        "page": page_num,
                                        "index": img_idx,
                                        "format": "png",
                                        "filename": f"page_{page_num}_image_{img_idx}.png"
                                    })
                                    logger.info(f"Extracted image from page {page_num}")
                            except Exception as e:
                                logger.warning(f"Failed to extract image from page {page_num}: {e}")
                                continue
        except Exception as e:
            logger.warning(f"Image extraction failed (non-critical): {e}")

        metadata = {
            "page_count": len(result.document.pages) if hasattr(result.document, "pages") else None,
            "title": result.document.title if hasattr(result.document, "title") else None,
            "language": result.document.language if hasattr(result.document, "language") else None,
            "image_count": len(images),
        }

        return {
            "content": content,
            "metadata": metadata,
            "page_count": metadata["page_count"],
            "images": images,  # NEW: List of extracted images
        }
