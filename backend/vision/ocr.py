"""
OCR (Optical Character Recognition) integration.

Provides text detection and recognition using:
- PaddleOCR (primary, if available)
- ONNX-based models (fallback)

Ported from RAGFlow's deepdoc/vision/ocr.py
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

# Check for PaddleOCR availability
# Note: PaddleOCR can fail on some platforms due to dependencies
PADDLE_AVAILABLE = False
PaddleOCR = None

try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
    logger.debug("PaddleOCR available")
except ImportError:
    logger.info("PaddleOCR not installed - OCR features disabled")
except Exception as e:
    logger.warning("PaddleOCR failed to initialize: %s - OCR features disabled", e)

# Check for OpenCV
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False
    cv2 = None


@dataclass
class OCRResult:
    """Represents an OCR detection result."""

    text: str
    confidence: float
    bbox: List[List[float]]  # Four corner points
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def top(self) -> float:
        return self.y0

    @property
    def bottom(self) -> float:
        return self.y1

    @property
    def left(self) -> float:
        return self.x0

    @property
    def right(self) -> float:
        return self.x1

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "bbox": self.bbox,
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "top": self.y0,
            "bottom": self.y1,
            "left": self.x0,
            "right": self.x1,
        }

    @classmethod
    def from_paddle_result(
        cls, box: List[List[float]], text: str, confidence: float
    ) -> "OCRResult":
        """Create from PaddleOCR result format."""
        # box is [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
        xs = [p[0] for p in box]
        ys = [p[1] for p in box]
        return cls(
            text=text,
            confidence=confidence,
            bbox=box,
            x0=min(xs),
            y0=min(ys),
            x1=max(xs),
            y1=max(ys),
        )


class OCRService:
    """
    OCR service for text detection and recognition.

    Supports multiple backends:
    - PaddleOCR (recommended, most accurate)
    - Docling fallback (basic)
    """

    def __init__(
        self,
        lang: str = "en",
        use_gpu: bool = False,
        det_model_dir: Optional[str] = None,
        rec_model_dir: Optional[str] = None,
        use_angle_cls: bool = True,
        show_log: bool = False,
    ):
        """
        Initialize OCR service.

        Args:
            lang: Language code (e.g., 'en', 'ch', 'japan')
            use_gpu: Whether to use GPU acceleration
            det_model_dir: Custom text detection model directory
            rec_model_dir: Custom text recognition model directory
            use_angle_cls: Whether to use angle classification
            show_log: Whether to show PaddleOCR logs
        """
        self.lang = lang
        self.use_gpu = use_gpu
        self.paddle_ocr: Optional["PaddleOCR"] = None

        if PADDLE_AVAILABLE:
            try:
                self.paddle_ocr = PaddleOCR(
                    lang=lang,
                    use_gpu=use_gpu,
                    det_model_dir=det_model_dir,
                    rec_model_dir=rec_model_dir,
                    use_angle_cls=use_angle_cls,
                    show_log=show_log,
                )
                logger.info("PaddleOCR initialized with lang=%s, gpu=%s", lang, use_gpu)
            except Exception as e:
                logger.error("Failed to initialize PaddleOCR: %s", e)
                self.paddle_ocr = None
        else:
            logger.warning("PaddleOCR not available")

    def is_available(self) -> bool:
        """Check if OCR service is available."""
        return self.paddle_ocr is not None

    def detect_and_recognize(
        self,
        image: Union[np.ndarray, str],
        det_only: bool = False,
        cls: bool = True,
    ) -> List[OCRResult]:
        """
        Detect and recognize text in an image.

        Args:
            image: Image as numpy array (H, W, C) or file path
            det_only: Only run detection, skip recognition
            cls: Whether to run angle classification

        Returns:
            List of OCRResult objects
        """
        if not self.is_available():
            logger.warning("OCR not available")
            return []

        try:
            # Run PaddleOCR
            results = self.paddle_ocr.ocr(image, det=True, rec=not det_only, cls=cls)

            if results is None or len(results) == 0:
                return []

            # Parse results
            ocr_results = []
            for page_result in results:
                if page_result is None:
                    continue

                for line in page_result:
                    if det_only:
                        # Detection only: line is just the box
                        box = line
                        text = ""
                        confidence = 1.0
                    else:
                        # Full OCR: line is (box, (text, confidence))
                        box = line[0]
                        text, confidence = line[1]

                    ocr_results.append(
                        OCRResult.from_paddle_result(box, text, confidence)
                    )

            return ocr_results

        except Exception as e:
            logger.error("OCR failed: %s", e)
            return []

    def detect_text_regions(self, image: Union[np.ndarray, str]) -> List[OCRResult]:
        """
        Detect text regions without recognition.

        Args:
            image: Image as numpy array or file path

        Returns:
            List of OCRResult objects with empty text
        """
        return self.detect_and_recognize(image, det_only=True)

    def recognize_text(
        self,
        image: np.ndarray,
        boxes: List[List[List[float]]],
    ) -> List[Tuple[str, float]]:
        """
        Recognize text in given regions.

        Args:
            image: Full image as numpy array
            boxes: List of text region boxes

        Returns:
            List of (text, confidence) tuples
        """
        if not self.is_available():
            return [("", 0.0) for _ in boxes]

        results = []
        for box in boxes:
            try:
                # Crop region
                cropped = self._crop_region(image, box)
                if cropped is None:
                    results.append(("", 0.0))
                    continue

                # Run recognition only
                ocr_result = self.paddle_ocr.ocr(cropped, det=False, rec=True, cls=False)

                if ocr_result and len(ocr_result) > 0 and len(ocr_result[0]) > 0:
                    # Get first result with defensive parsing
                    first_result = ocr_result[0][0]
                    if isinstance(first_result, (list, tuple)) and len(first_result) >= 2:
                        text, confidence = first_result[0], float(first_result[1])
                    elif isinstance(first_result, str):
                        text, confidence = first_result, 0.5
                    else:
                        raise ValueError(f"Unexpected OCR result format: {type(first_result)}")
                    results.append((text, confidence))
                else:
                    results.append(("", 0.0))

            except Exception as e:
                logger.debug("Recognition failed for region: %s", e)
                results.append(("", 0.0))

        return results

    def _crop_region(
        self, image: np.ndarray, box: List[List[float]]
    ) -> Optional[np.ndarray]:
        """Crop a region from image given box coordinates."""
        if not CV2_AVAILABLE:
            return None

        try:
            # Get bounding rectangle
            pts = np.array(box, dtype=np.float32)
            x, y, w, h = cv2.boundingRect(pts)

            # Ensure valid bounds
            h_img, w_img = image.shape[:2]
            x = max(0, x)
            y = max(0, y)
            w = min(w, w_img - x)
            h = min(h, h_img - y)

            if w <= 0 or h <= 0:
                return None

            return image[y : y + h, x : x + w]

        except Exception:
            return None

    def batch_ocr(
        self,
        images: List[Union[np.ndarray, str]],
    ) -> List[List[OCRResult]]:
        """
        Run OCR on multiple images.

        Args:
            images: List of images

        Returns:
            List of OCRResult lists, one per image
        """
        return [self.detect_and_recognize(img) for img in images]


class TextDetector:
    """
    Standalone text detector using ONNX models.

    For use when PaddleOCR is not available.
    """

    def __init__(self, model_dir: Optional[str] = None):
        """
        Initialize text detector.

        Args:
            model_dir: Directory containing ONNX detection model
        """
        self.model_dir = model_dir
        self.session = None

        # Try to load ONNX model
        try:
            import onnxruntime as ort

            model_path = self._find_model()
            if model_path and os.path.exists(model_path):
                self.session = ort.InferenceSession(
                    model_path,
                    providers=["CPUExecutionProvider"],
                )
                logger.info("Text detector loaded: %s", model_path)
        except ImportError:
            logger.debug("ONNX runtime not available for text detection")
        except Exception as e:
            logger.debug("Failed to load text detector: %s", e)

    def _find_model(self) -> Optional[str]:
        """Find detection model file."""
        if self.model_dir:
            candidates = [
                os.path.join(self.model_dir, "det.onnx"),
                os.path.join(self.model_dir, "text_det.onnx"),
            ]
            for path in candidates:
                if os.path.exists(path):
                    return path
        return None

    def is_available(self) -> bool:
        """Check if detector is available."""
        return self.session is not None

    def detect(self, image: np.ndarray) -> List[List[List[float]]]:
        """
        Detect text regions in image.

        Args:
            image: Image as numpy array

        Returns:
            List of text region boxes
        """
        if not self.is_available():
            return []

        # TODO: Implement ONNX-based detection
        # For now, return empty list
        logger.debug("ONNX text detection not fully implemented")
        return []


class TextRecognizer:
    """
    Standalone text recognizer using ONNX models.

    For use when PaddleOCR is not available.
    """

    def __init__(self, model_dir: Optional[str] = None):
        """
        Initialize text recognizer.

        Args:
            model_dir: Directory containing ONNX recognition model
        """
        self.model_dir = model_dir
        self.session = None
        self.char_dict: List[str] = []

        # Try to load ONNX model
        try:
            import onnxruntime as ort

            model_path = self._find_model()
            if model_path and os.path.exists(model_path):
                self.session = ort.InferenceSession(
                    model_path,
                    providers=["CPUExecutionProvider"],
                )
                self._load_char_dict()
                logger.info("Text recognizer loaded: %s", model_path)
        except ImportError:
            logger.debug("ONNX runtime not available for text recognition")
        except Exception as e:
            logger.debug("Failed to load text recognizer: %s", e)

    def _find_model(self) -> Optional[str]:
        """Find recognition model file."""
        if self.model_dir:
            candidates = [
                os.path.join(self.model_dir, "rec.onnx"),
                os.path.join(self.model_dir, "text_rec.onnx"),
            ]
            for path in candidates:
                if os.path.exists(path):
                    return path
        return None

    def _load_char_dict(self) -> None:
        """Load character dictionary."""
        if not self.model_dir:
            return

        dict_path = os.path.join(self.model_dir, "ocr.res")
        if os.path.exists(dict_path):
            try:
                with open(dict_path, "r", encoding="utf-8") as f:
                    self.char_dict = [line.strip() for line in f]
                logger.debug("Loaded %d characters", len(self.char_dict))
            except Exception as e:
                logger.debug("Failed to load char dict: %s", e)

    def is_available(self) -> bool:
        """Check if recognizer is available."""
        return self.session is not None and len(self.char_dict) > 0

    def recognize(self, images: List[np.ndarray]) -> List[Tuple[str, float]]:
        """
        Recognize text in cropped images.

        Args:
            images: List of cropped text region images

        Returns:
            List of (text, confidence) tuples
        """
        if not self.is_available():
            return [("", 0.0) for _ in images]

        # TODO: Implement ONNX-based recognition
        # For now, return empty results
        logger.debug("ONNX text recognition not fully implemented")
        return [("", 0.0) for _ in images]


# Singleton instances
_ocr_service: Optional[OCRService] = None


def get_ocr_service(
    lang: str = "en",
    use_gpu: bool = False,
    **kwargs,
) -> OCRService:
    """
    Get OCR service singleton.

    Args:
        lang: Language code
        use_gpu: Whether to use GPU

    Returns:
        OCRService instance
    """
    global _ocr_service
    if _ocr_service is None:
        _ocr_service = OCRService(lang=lang, use_gpu=use_gpu, **kwargs)
    return _ocr_service


def ocr_available() -> bool:
    """Check if OCR is available."""
    return PADDLE_AVAILABLE
