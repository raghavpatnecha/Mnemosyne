"""
Docling Parser for documents (PDF, DOCX, PPTX)
Advanced document parsing with layout preservation and image extraction
Uses Docling 2.x API with pypdfium2 fallback for malformed PDFs

References:
- Pipeline Options: https://docling-project.github.io/docling/reference/pipeline_options/
- Advanced Options: https://docling-project.github.io/docling/usage/advanced_options/
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
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
        """Initialize Docling parser with optimized settings for layout analysis"""
        self.converter = None
        self._initialized = False

    def _initialize_converter(self):
        """Lazy initialization of DocumentConverter with optimized settings"""
        if self._initialized:
            return

        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.pipeline_options import PdfPipelineOptions
            from docling.datamodel.base_models import InputFormat

            # Configure PDF pipeline for better layout analysis
            # Note: Multi-column reading order is a known limitation
            # See: https://github.com/docling-project/docling/issues/1203
            pipeline_options = PdfPipelineOptions(
                do_table_structure=True,
                do_ocr=True,  # Enable OCR for scanned documents
            )

            # Use accurate table structure for better results
            try:
                from docling.datamodel.pipeline_options import TableFormerMode
                pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
                pipeline_options.table_structure_options.do_cell_matching = True
            except (ImportError, AttributeError):
                # Older Docling versions may not have TableFormerMode
                pass

            self.converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )
            logger.info("Docling DocumentConverter initialized with optimized settings")

        except ImportError as e:
            logger.warning(f"Docling 2.x import failed, using basic converter: {e}")
            from docling.document_converter import DocumentConverter
            self.converter = DocumentConverter()

        self._initialized = True

    def can_parse(self, content_type: str) -> bool:
        """Check if this parser can handle the content type"""
        if not content_type:
            return False
        return content_type in self.SUPPORTED_FORMATS

    def _fallback_pdf_extraction(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Fallback PDF text extraction using pypdfium2 directly.
        Used when Docling fails on malformed PDFs (missing MediaBox, etc.)
        """
        try:
            import pypdfium2 as pdfium

            pdf = pdfium.PdfDocument(str(file_path))
            page_count = len(pdf)

            text_parts = []
            for i, page in enumerate(pdf):
                textpage = page.get_textpage()
                text = textpage.get_text_bounded()
                if text:
                    text_parts.append(f"## Page {i + 1}\n\n{text}")

            content = "\n\n".join(text_parts)

            if not content or not content.strip():
                return None

            logger.info(f"Fallback extraction succeeded: {len(content)} chars, {page_count} pages")

            return {
                "content": content,
                "metadata": {
                    "page_count": page_count,
                    "title": None,
                    "language": None,
                    "image_count": 0,
                    "extraction_method": "pypdfium2_fallback",
                },
                "page_count": page_count,
                "images": [],
            }
        except Exception as e:
            logger.warning(f"Fallback PDF extraction also failed: {e}")
            return None

    async def parse(self, file_path: str) -> Dict[str, Any]:
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

        Raises:
            ValueError: If document parsing fails or returns empty content
        """
        # Initialize converter on first use (lazy loading)
        self._initialize_converter()

        file_path_obj = Path(file_path)
        content = None
        result = None
        docling_error = None

        # Try Docling 2.x API first
        try:
            # Use convert for single file conversion (returns ConversionResult)
            result = self.converter.convert(str(file_path_obj))
            # Check conversion status
            from docling.datamodel.base_models import ConversionStatus
            if result.status != ConversionStatus.SUCCESS:
                docling_error = f"Conversion failed for: {file_path_obj.name} with status: {result.status}"
                if result.errors:
                    docling_error += f". Errors: {'; '.join(str(e) for e in result.errors)}"
                logger.warning(docling_error)
            else:
                content = result.document.export_to_markdown()
        except Exception as e:
            docling_error = str(e)
            logger.warning(f"Docling conversion failed: {e}")

        # Fallback for PDFs if Docling failed or returned empty content
        if (not content or not content.strip()) and file_path_obj.suffix.lower() == ".pdf":
            logger.info(f"Attempting fallback PDF extraction for {file_path_obj.name}")
            fallback_result = self._fallback_pdf_extraction(file_path_obj)
            if fallback_result:
                return fallback_result

        # Fail-fast: raise error if content is empty after all attempts
        if not content or not content.strip():
            error_msg = f"Failed to extract content from {file_path_obj.name}."
            if docling_error:
                error_msg = docling_error
            raise ValueError(error_msg)

        # Extract images from document (Docling 2.x API)
        images = []
        doc = result.document
        try:
            # Docling 2.x: iterate over document pictures
            if hasattr(doc, "pictures") and doc.pictures:
                for img_idx, picture in enumerate(doc.pictures):
                    try:
                        # Get image data if available
                        if hasattr(picture, "image") and picture.image:
                            img_data = picture.image.pil_image

                            import io
                            img_bytes = io.BytesIO()
                            img_data.save(img_bytes, format='PNG')
                            img_bytes.seek(0)

                            # Get page number if available
                            page_num = getattr(picture, "page_no", img_idx + 1)

                            images.append({
                                "data": img_bytes.read(),
                                "page": page_num,
                                "index": img_idx,
                                "format": "png",
                                "filename": f"page_{page_num}_image_{img_idx}.png"
                            })
                            logger.info(f"Extracted image {img_idx} from document")
                    except Exception as e:
                        logger.warning(f"Failed to extract image {img_idx}: {e}")
                        continue
        except Exception as e:
            logger.warning(f"Image extraction failed (non-critical): {e}")

        # Extract metadata (Docling 2.x API)
        page_count = None
        title = None
        try:
            if hasattr(doc, "pages"):
                page_count = len(doc.pages) if doc.pages else None
            if hasattr(doc, "name"):
                title = doc.name
        except Exception as e:
            logger.warning(f"Metadata extraction failed (non-critical): {e}")

        metadata = {
            "page_count": page_count,
            "title": title,
            "language": None,
            "image_count": len(images),
        }

        logger.info(f"Parsed document: {len(content)} chars, {page_count} pages, {len(images)} images")

        return {
            "content": content,
            "metadata": metadata,
            "page_count": page_count,
            "images": images,
        }
