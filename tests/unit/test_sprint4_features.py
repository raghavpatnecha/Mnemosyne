"""
Sprint 4 Unit Tests - Vision Pipeline

Tests for:
- Vision Operators (NMS, resize, normalize)
- Layout Recognizer (structure and interfaces)
- OCR Service (structure and interfaces)
"""

import pytest
import numpy as np


class TestVisionOperators:
    """Tests for vision operator utilities."""

    def test_operators_import(self):
        """Test operators can be imported."""
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
        assert nms is not None
        assert resize_image is not None
        assert normalize_image is not None
        assert ImagePreprocessor is not None

    def test_nms_empty(self):
        """Test NMS with empty input."""
        from backend.vision.operators import nms

        boxes = np.array([]).reshape(0, 4)
        scores = np.array([])
        result = nms(boxes, scores, 0.5)
        assert result == []

    def test_nms_single_box(self):
        """Test NMS with single box."""
        from backend.vision.operators import nms

        boxes = np.array([[10, 10, 50, 50]])
        scores = np.array([0.9])
        result = nms(boxes, scores, 0.5)
        assert result == [0]

    def test_nms_multiple_boxes(self):
        """Test NMS with overlapping boxes."""
        from backend.vision.operators import nms

        boxes = np.array([
            [10, 10, 50, 50],
            [12, 12, 52, 52],  # Highly overlapping with first
            [100, 100, 150, 150],  # Non-overlapping
        ])
        scores = np.array([0.9, 0.8, 0.7])
        result = nms(boxes, scores, 0.5)

        # Should keep first (highest score) and third (non-overlapping)
        assert 0 in result
        assert 2 in result
        assert len(result) <= 3

    def test_compute_iou(self):
        """Test IoU computation."""
        from backend.vision.operators import compute_iou

        # Identical boxes
        box1 = np.array([0, 0, 10, 10])
        iou = compute_iou(box1, box1)
        assert abs(iou - 1.0) < 0.01

        # Non-overlapping boxes
        box2 = np.array([20, 20, 30, 30])
        iou = compute_iou(box1, box2)
        assert iou == 0.0

        # Partially overlapping
        box3 = np.array([5, 5, 15, 15])
        iou = compute_iou(box1, box3)
        assert 0 < iou < 1

    def test_normalize_image(self):
        """Test image normalization."""
        from backend.vision.operators import normalize_image

        # Create test image
        image = np.ones((100, 100, 3), dtype=np.uint8) * 128

        normalized = normalize_image(image)
        assert normalized.dtype == np.float32
        assert normalized.shape == image.shape

    def test_hwc_chw_conversion(self):
        """Test HWC to CHW conversion."""
        from backend.vision.operators import hwc_to_chw, chw_to_hwc

        hwc = np.zeros((100, 200, 3))
        chw = hwc_to_chw(hwc)
        assert chw.shape == (3, 100, 200)

        back = chw_to_hwc(chw)
        assert back.shape == (100, 200, 3)

    def test_clip_boxes(self):
        """Test box clipping."""
        from backend.vision.operators import clip_boxes

        boxes = np.array([
            [-10, -10, 50, 50],  # Extends beyond top-left
            [90, 90, 150, 150],  # Extends beyond bottom-right
        ])
        clipped = clip_boxes(boxes, (100, 100))

        assert clipped[0, 0] == 0
        assert clipped[0, 1] == 0
        assert clipped[1, 2] == 100
        assert clipped[1, 3] == 100

    def test_box_area(self):
        """Test box area computation."""
        from backend.vision.operators import box_area

        boxes = np.array([
            [0, 0, 10, 10],   # Area = 100
            [0, 0, 20, 10],   # Area = 200
        ])
        areas = box_area(boxes)

        assert areas[0] == 100
        assert areas[1] == 200

    def test_image_preprocessor(self):
        """Test ImagePreprocessor class."""
        from backend.vision.operators import ImagePreprocessor

        preprocessor = ImagePreprocessor(
            target_size=None,  # Skip resize (requires cv2)
            normalize=True,
            to_chw=True,
        )

        # Create test image
        image = np.ones((100, 200, 3), dtype=np.uint8) * 128

        processed, info = preprocessor(image)
        assert processed.shape[0] == 3  # CHW format
        assert "original_shape" in info


class TestLayoutRecognizer:
    """Tests for LayoutRecognizer class."""

    def test_layout_recognizer_import(self):
        """Test LayoutRecognizer can be imported."""
        from backend.vision.layout_recognizer import (
            LayoutRecognizer,
            LayoutBox,
            LAYOUT_LABELS,
            get_layout_recognizer,
        )
        assert LayoutRecognizer is not None
        assert LayoutBox is not None
        assert len(LAYOUT_LABELS) == 10

    def test_layout_labels(self):
        """Test layout labels are correct."""
        from backend.vision.layout_recognizer import LAYOUT_LABELS

        expected = [
            "title", "text", "reference", "figure", "figure_caption",
            "table", "table_caption", "header", "footer", "equation",
        ]
        assert LAYOUT_LABELS == expected

    def test_layout_box_creation(self):
        """Test LayoutBox dataclass."""
        from backend.vision.layout_recognizer import LayoutBox

        box = LayoutBox(
            type="text",
            score=0.9,
            x0=10,
            y0=20,
            x1=100,
            y1=50,
            page_number=0,
        )

        assert box.type == "text"
        assert box.score == 0.9
        assert box.top == 20
        assert box.bottom == 50
        assert box.width == 90
        assert box.height == 30
        assert box.area == 2700

    def test_layout_box_from_bbox(self):
        """Test LayoutBox.from_bbox factory."""
        from backend.vision.layout_recognizer import LayoutBox

        bbox = [10.0, 20.0, 100.0, 50.0]
        box = LayoutBox.from_bbox(bbox, "figure", 0.85, page_number=1)

        assert box.type == "figure"
        assert box.score == 0.85
        assert box.x0 == 10.0
        assert box.y1 == 50.0
        assert box.page_number == 1

    def test_layout_box_to_dict(self):
        """Test LayoutBox serialization."""
        from backend.vision.layout_recognizer import LayoutBox

        box = LayoutBox(
            type="table",
            score=0.95,
            x0=0,
            y0=0,
            x1=100,
            y1=100,
        )
        d = box.to_dict()

        assert d["type"] == "table"
        assert d["score"] == 0.95
        assert "x0" in d
        assert "top" in d
        assert "bottom" in d

    def test_layout_box_center(self):
        """Test LayoutBox center property."""
        from backend.vision.layout_recognizer import LayoutBox

        box = LayoutBox(
            type="text",
            score=0.9,
            x0=0,
            y0=0,
            x1=100,
            y1=100,
        )
        cx, cy = box.center
        assert cx == 50.0
        assert cy == 50.0

    def test_get_layout_recognizer_graceful(self):
        """Test get_layout_recognizer handles missing deps gracefully."""
        from backend.vision.layout_recognizer import get_layout_recognizer

        # Should not raise, may return None if ONNX not available
        recognizer = get_layout_recognizer()
        # Just verify it doesn't crash


class TestOCRService:
    """Tests for OCR service."""

    def test_ocr_imports(self):
        """Test OCR module can be imported."""
        from backend.vision.ocr import (
            OCRService,
            OCRResult,
            get_ocr_service,
            ocr_available,
            PADDLE_AVAILABLE,
        )
        assert OCRService is not None
        assert OCRResult is not None
        assert get_ocr_service is not None

    def test_ocr_result_creation(self):
        """Test OCRResult dataclass."""
        from backend.vision.ocr import OCRResult

        result = OCRResult(
            text="Hello World",
            confidence=0.95,
            bbox=[[0, 0], [100, 0], [100, 30], [0, 30]],
            x0=0,
            y0=0,
            x1=100,
            y1=30,
        )

        assert result.text == "Hello World"
        assert result.confidence == 0.95
        assert result.width == 100
        assert result.height == 30
        assert result.left == 0
        assert result.right == 100

    def test_ocr_result_from_paddle(self):
        """Test OCRResult.from_paddle_result factory."""
        from backend.vision.ocr import OCRResult

        box = [[10, 10], [110, 10], [110, 40], [10, 40]]
        result = OCRResult.from_paddle_result(box, "Test", 0.88)

        assert result.text == "Test"
        assert result.confidence == 0.88
        assert result.x0 == 10
        assert result.x1 == 110
        assert result.y0 == 10
        assert result.y1 == 40

    def test_ocr_result_to_dict(self):
        """Test OCRResult serialization."""
        from backend.vision.ocr import OCRResult

        result = OCRResult(
            text="Sample",
            confidence=0.9,
            bbox=[[0, 0], [50, 0], [50, 20], [0, 20]],
            x0=0,
            y0=0,
            x1=50,
            y1=20,
        )
        d = result.to_dict()

        assert d["text"] == "Sample"
        assert d["confidence"] == 0.9
        assert "bbox" in d
        assert "left" in d
        assert "right" in d

    def test_ocr_service_initialization(self):
        """Test OCRService can be created."""
        from backend.vision.ocr import OCRService

        service = OCRService(lang="en", use_gpu=False)
        # Just verify it doesn't crash

    def test_ocr_available_function(self):
        """Test ocr_available function."""
        from backend.vision.ocr import ocr_available, PADDLE_AVAILABLE

        # Should match PADDLE_AVAILABLE
        assert ocr_available() == PADDLE_AVAILABLE

    def test_get_ocr_service_singleton(self):
        """Test get_ocr_service returns singleton."""
        from backend.vision.ocr import get_ocr_service

        # Reset singleton for test
        import backend.vision.ocr as ocr_module
        ocr_module._ocr_service = None

        service1 = get_ocr_service()
        service2 = get_ocr_service()
        assert service1 is service2


class TestVisionModuleExports:
    """Tests for vision module exports."""

    def test_vision_module_imports(self):
        """Test all expected exports are available."""
        from backend.vision import (
            # Base
            Recognizer,
            ONNX_AVAILABLE,
            # Table
            TableStructureRecognizer,
            # Layout
            LayoutRecognizer,
            LayoutBox,
            LAYOUT_LABELS,
            get_layout_recognizer,
            # OCR
            OCRService,
            OCRResult,
            get_ocr_service,
            ocr_available,
            PADDLE_AVAILABLE,
            # Operators
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

        # All imports should succeed
        assert Recognizer is not None
        assert LayoutRecognizer is not None
        assert OCRService is not None
        assert nms is not None

    def test_availability_flags(self):
        """Test availability flags are booleans."""
        from backend.vision import (
            ONNX_AVAILABLE,
            PADDLE_AVAILABLE,
            CV2_AVAILABLE,
        )

        assert isinstance(ONNX_AVAILABLE, bool)
        assert isinstance(PADDLE_AVAILABLE, bool)
        assert isinstance(CV2_AVAILABLE, bool)


class TestIntegrationScenarios:
    """Integration tests for Sprint 4 features."""

    def test_layout_to_ocr_workflow(self):
        """Test layout detection to OCR workflow structure."""
        from backend.vision.layout_recognizer import LayoutBox
        from backend.vision.ocr import OCRResult

        # Simulate layout detection result
        layout = LayoutBox(
            type="text",
            score=0.9,
            x0=50,
            y0=100,
            x1=200,
            y1=130,
            page_number=0,
        )

        # Simulate OCR result within that region
        ocr_result = OCRResult(
            text="Sample document text",
            confidence=0.95,
            bbox=[[50, 100], [200, 100], [200, 130], [50, 130]],
            x0=50,
            y0=100,
            x1=200,
            y1=130,
        )

        # Verify types match
        assert layout.type == "text"
        assert ocr_result.text == "Sample document text"

        # Verify coordinates align
        assert layout.x0 == ocr_result.x0
        assert layout.y1 == ocr_result.y1

    def test_nms_with_layout_boxes(self):
        """Test NMS can work with layout detection output."""
        from backend.vision.operators import nms
        from backend.vision.layout_recognizer import LayoutBox

        # Create overlapping layout boxes
        boxes = [
            LayoutBox("text", 0.9, 10, 10, 50, 50, 0),
            LayoutBox("text", 0.8, 12, 12, 52, 52, 0),  # Overlaps
            LayoutBox("text", 0.7, 100, 100, 150, 150, 0),  # Separate
        ]

        # Convert to numpy for NMS
        np_boxes = np.array([[b.x0, b.y0, b.x1, b.y1] for b in boxes])
        scores = np.array([b.score for b in boxes])

        keep = nms(np_boxes, scores, 0.5)

        # Should keep at least 2 (non-overlapping)
        assert len(keep) >= 2

    def test_preprocessor_pipeline(self):
        """Test image preprocessing pipeline."""
        from backend.vision.operators import (
            normalize_image,
            hwc_to_chw,
        )

        # Create test image
        image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Normalize
        normalized = normalize_image(image)
        assert normalized.dtype == np.float32

        # Convert to CHW
        chw = hwc_to_chw(normalized)
        assert chw.shape == (3, 480, 640)

        # Should be ready for model input
        batch = chw[np.newaxis, ...]
        assert batch.shape == (1, 3, 480, 640)
