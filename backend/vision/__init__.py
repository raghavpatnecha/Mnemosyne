"""
Vision module for document analysis.

Provides ONNX-based recognizers for:
- Table structure recognition (rows, columns, headers, spanning cells)
- Layout recognition (text, figures, tables, titles, equations)
- OCR (text detection and recognition)

Ported from RAGFlow's deepdoc/vision module.

FAIL-FAST APPROACH:
- Imports fail immediately if dependencies are broken
- Availability flags (ONNX_AVAILABLE, CV2_AVAILABLE, PADDLE_AVAILABLE)
  indicate what features are available
- Code using these features should check flags before use
"""

# Standard imports - these must work
from backend.vision.recognizer import Recognizer, ONNX_AVAILABLE
from backend.vision.table_structure_recognizer import TableStructureRecognizer
from backend.vision.layout_recognizer import (
    LayoutRecognizer,
    LayoutBox,
    LAYOUT_LABELS,
    get_layout_recognizer,
)
from backend.vision.ocr import (
    OCRService,
    OCRResult,
    get_ocr_service,
    ocr_available,
    PADDLE_AVAILABLE,
)
from backend.vision.operators import (
    nms,
    resize_image,
    normalize_image,
    hwc_to_chw,
    chw_to_hwc,
    scale_boxes,
    clip_boxes,
    compute_iou,
    ImagePreprocessor,
    CV2_AVAILABLE,
)

__all__ = [
    # Base
    "Recognizer",
    "ONNX_AVAILABLE",
    # Table
    "TableStructureRecognizer",
    # Layout
    "LayoutRecognizer",
    "LayoutBox",
    "LAYOUT_LABELS",
    "get_layout_recognizer",
    # OCR
    "OCRService",
    "OCRResult",
    "get_ocr_service",
    "ocr_available",
    "PADDLE_AVAILABLE",
    # Operators
    "nms",
    "resize_image",
    "normalize_image",
    "hwc_to_chw",
    "chw_to_hwc",
    "scale_boxes",
    "clip_boxes",
    "compute_iou",
    "ImagePreprocessor",
    "CV2_AVAILABLE",
]
