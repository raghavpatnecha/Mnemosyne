"""
Layout Recognizer for document structure detection.

Detects document layout elements:
- Text, Title, Figure, Figure caption
- Table, Table caption
- Header, Footer, Reference, Equation

Uses YOLOv10-based ONNX model from InfiniFlow/deepdoc.

Ported from RAGFlow's deepdoc/vision/layout_recognizer.py
"""

import logging
import os
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.vision.recognizer import Recognizer, ONNX_AVAILABLE
from backend.vision.operators import nms, resize_image, CV2_AVAILABLE

logger = logging.getLogger(__name__)

# Layout labels detected by the model
LAYOUT_LABELS = [
    "title",
    "text",
    "reference",
    "figure",
    "figure_caption",
    "table",
    "table_caption",
    "header",
    "footer",
    "equation",
]

# Labels considered as garbage (headers/footers to potentially filter)
GARBAGE_LAYOUTS = {"header", "footer", "reference"}


@dataclass
class LayoutBox:
    """Represents a detected layout element."""

    type: str
    score: float
    x0: float
    y0: float
    x1: float
    y1: float
    page_number: int = 0

    @property
    def top(self) -> float:
        return self.y0

    @property
    def bottom(self) -> float:
        return self.y1

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return self.width * self.height

    @property
    def center(self) -> Tuple[float, float]:
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "score": self.score,
            "x0": self.x0,
            "y0": self.y0,
            "x1": self.x1,
            "y1": self.y1,
            "top": self.y0,
            "bottom": self.y1,
            "page_number": self.page_number,
        }

    @classmethod
    def from_bbox(
        cls,
        bbox: List[float],
        label: str,
        score: float,
        page_number: int = 0,
    ) -> "LayoutBox":
        """Create from [x1, y1, x2, y2] format."""
        return cls(
            type=label,
            score=score,
            x0=bbox[0],
            y0=bbox[1],
            x1=bbox[2],
            y1=bbox[3],
            page_number=page_number,
        )


class LayoutRecognizer(Recognizer):
    """
    YOLOv10-based layout recognizer for document structure detection.

    Detects layout elements in document images including:
    - Text blocks and titles
    - Figures and their captions
    - Tables and their captions
    - Headers, footers, and references
    - Equations

    Requires ONNX model from InfiniFlow/deepdoc repository.
    """

    # Default model configuration
    DEFAULT_MODEL_NAME = "layout"
    DEFAULT_INPUT_SIZE = (640, 640)  # YOLOv10 input size
    DEFAULT_THRESHOLD = 0.25

    def __init__(
        self,
        model_dir: Optional[str] = None,
        model_name: str = DEFAULT_MODEL_NAME,
        input_size: Tuple[int, int] = DEFAULT_INPUT_SIZE,
        threshold: float = DEFAULT_THRESHOLD,
    ):
        """
        Initialize LayoutRecognizer.

        Args:
            model_dir: Directory containing the ONNX model
            model_name: Name of the model file (without .onnx extension)
            input_size: Model input size as (height, width)
            threshold: Confidence threshold for detections
        """
        self.input_size = input_size
        self.threshold = threshold
        self.garbage_layouts = GARBAGE_LAYOUTS

        # Determine model directory
        if model_dir is None:
            model_dir = self._get_default_model_dir()

        super().__init__(
            labels=LAYOUT_LABELS,
            model_name=model_name,
            model_dir=model_dir,
        )

        # Store input shape from model if available
        if self.session is not None:
            try:
                input_shape = self.session.get_inputs()[0].shape
                if len(input_shape) >= 4:
                    self.input_size = (input_shape[2], input_shape[3])
            except Exception:
                pass

        logger.info(
            "LayoutRecognizer initialized: model=%s, input_size=%s, threshold=%s",
            model_name,
            self.input_size,
            self.threshold,
        )

    def _get_default_model_dir(self) -> str:
        """Get default model directory."""
        # Check common locations
        candidates = [
            os.path.join(os.path.dirname(__file__), "models"),
            os.path.join(os.path.dirname(__file__), "..", "..", "models", "deepdoc"),
            os.path.expanduser("~/.cache/mnemosyne/models/deepdoc"),
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return candidates[0]  # Return first as default

    def preprocess(self, images: List[np.ndarray]) -> List[Dict[str, Any]]:
        """
        Preprocess images for YOLOv10 model.

        Args:
            images: List of images as numpy arrays (H, W, C) in BGR format

        Returns:
            List of input dictionaries for the model
        """
        if not CV2_AVAILABLE:
            raise RuntimeError("OpenCV required for layout recognition")

        import cv2

        inputs = []
        target_h, target_w = self.input_size

        for img in images:
            h, w = img.shape[:2]

            # Calculate scale to fit in target size
            scale = min(target_h / h, target_w / w)
            new_h = int(h * scale)
            new_w = int(w * scale)

            # Resize image
            if img.shape[2] == 3:
                img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            else:
                img_rgb = img

            resized = cv2.resize(
                img_rgb.astype(np.float32),
                (new_w, new_h),
                interpolation=cv2.INTER_LINEAR,
            )

            # Calculate padding
            dw = (target_w - new_w) / 2
            dh = (target_h - new_h) / 2

            # Apply padding
            top = int(round(dh - 0.1))
            bottom = int(round(dh + 0.1))
            left = int(round(dw - 0.1))
            right = int(round(dw + 0.1))

            padded = cv2.copyMakeBorder(
                resized, top, bottom, left, right,
                cv2.BORDER_CONSTANT, value=(114, 114, 114)
            )

            # Normalize to [0, 1]
            padded = padded / 255.0

            # Convert to CHW and add batch dimension
            tensor = padded.transpose(2, 0, 1)[np.newaxis, :, :, :].astype(np.float32)

            inputs.append({
                self.input_names[0] if self.input_names else "images": tensor,
                "scale_factor": (w / new_w, h / new_h),
                "pad": (dw, dh),
                "original_size": (h, w),
            })

        return inputs

    def postprocess(
        self,
        outputs: List[np.ndarray],
        inputs: Dict[str, Any],
        threshold: float,
    ) -> List[Dict[str, Any]]:
        """
        Postprocess YOLOv10 model outputs.

        Args:
            outputs: Model output arrays
            inputs: Preprocessing info dictionary
            threshold: Confidence threshold

        Returns:
            List of detected layout boxes
        """
        # YOLOv10 output format: (batch, num_detections, 6)
        # Each detection: [x1, y1, x2, y2, score, class_id]
        boxes = np.squeeze(outputs[0] if isinstance(outputs, list) else outputs)

        if boxes.ndim == 1:
            boxes = boxes.reshape(1, -1)

        if boxes.shape[1] != 6:
            logger.warning("Unexpected output shape: %s", boxes.shape)
            return []

        # Filter by confidence
        scores = boxes[:, 4]
        mask = scores >= threshold
        boxes = boxes[mask]
        scores = scores[mask]

        if len(boxes) == 0:
            return []

        class_ids = boxes[:, 5].astype(int)
        coords = boxes[:, :4].astype(np.float32)

        # Undo padding and scaling
        if "pad" in inputs:
            dw, dh = inputs["pad"]
            coords[:, [0, 2]] -= dw
            coords[:, [1, 3]] -= dh

        if "scale_factor" in inputs:
            sx, sy = inputs["scale_factor"]
            coords[:, [0, 2]] *= sx
            coords[:, [1, 3]] *= sy

        # Apply NMS per class
        keep_indices = []
        for class_id in np.unique(class_ids):
            idx = np.where(class_ids == class_id)[0]
            class_boxes = coords[idx]
            class_scores = scores[idx]
            keep = nms(class_boxes, class_scores, 0.45)
            keep_indices.extend(idx[keep])

        # Build results
        results = []
        for i in keep_indices:
            cid = int(class_ids[i])
            if 0 <= cid < len(self.labels):
                results.append({
                    "type": self.labels[cid].lower(),
                    "bbox": coords[i].tolist(),
                    "score": float(scores[i]),
                })

        return results

    def detect(
        self,
        images: List[np.ndarray],
        threshold: Optional[float] = None,
        scale_factor: float = 1.0,
    ) -> List[List[LayoutBox]]:
        """
        Detect layout elements in images.

        Args:
            images: List of page images as numpy arrays
            threshold: Confidence threshold (uses default if None)
            scale_factor: Scale factor for output coordinates

        Returns:
            List of LayoutBox lists, one per image
        """
        if not ONNX_AVAILABLE or self.session is None:
            logger.warning("Layout model not available")
            return [[] for _ in images]

        if threshold is None:
            threshold = self.threshold

        # Run base detection
        raw_results = self(images, threshold)

        # Convert to LayoutBox objects
        results = []
        for page_num, page_results in enumerate(raw_results):
            page_boxes = []
            for det in page_results:
                # Apply scale factor
                bbox = [c / scale_factor for c in det["bbox"]]
                box = LayoutBox.from_bbox(
                    bbox=bbox,
                    label=det["type"],
                    score=det["score"],
                    page_number=page_num,
                )
                page_boxes.append(box)

            # Sort by Y coordinate
            page_boxes.sort(key=lambda b: (b.y0, b.x0))
            results.append(page_boxes)

        return results

    def filter_garbage(
        self,
        boxes: List[LayoutBox],
        image_height: float,
        margin_ratio: float = 0.1,
    ) -> List[LayoutBox]:
        """
        Filter out garbage layouts (headers/footers).

        Args:
            boxes: List of LayoutBox objects
            image_height: Height of the image
            margin_ratio: Ratio of image height to consider as margin

        Returns:
            Filtered list of LayoutBox objects
        """
        margin = image_height * margin_ratio
        filtered = []

        for box in boxes:
            if box.type in self.garbage_layouts:
                # Keep header only if not in top margin
                if box.type == "header" and box.y0 < margin:
                    continue
                # Keep footer only if not in bottom margin
                if box.type == "footer" and box.y1 > image_height - margin:
                    continue
            filtered.append(box)

        return filtered

    def assign_layout_to_text(
        self,
        text_boxes: List[Dict[str, Any]],
        layout_boxes: List[LayoutBox],
        overlap_threshold: float = 0.4,
    ) -> List[Dict[str, Any]]:
        """
        Assign layout types to text boxes based on overlap.

        Args:
            text_boxes: List of text boxes with x0, y0, x1, y1 keys
            layout_boxes: List of detected layout boxes
            overlap_threshold: Minimum overlap ratio to assign layout

        Returns:
            Text boxes with layout_type added
        """
        for text_box in text_boxes:
            text_box["layout_type"] = ""

            # Find best overlapping layout
            best_overlap = 0
            best_layout = None

            for layout in layout_boxes:
                overlap = self._compute_overlap(text_box, layout)
                if overlap > best_overlap and overlap >= overlap_threshold:
                    best_overlap = overlap
                    best_layout = layout

            if best_layout:
                text_box["layout_type"] = best_layout.type
                text_box["layoutno"] = f"{best_layout.type}-{id(best_layout)}"

        return text_boxes

    def _compute_overlap(
        self,
        text_box: Dict[str, Any],
        layout: LayoutBox,
    ) -> float:
        """Compute overlap ratio between text box and layout box."""
        # Get text box coordinates
        tx0 = text_box.get("x0", text_box.get("left", 0))
        ty0 = text_box.get("y0", text_box.get("top", 0))
        tx1 = text_box.get("x1", text_box.get("right", 0))
        ty1 = text_box.get("y1", text_box.get("bottom", 0))

        # Compute intersection
        ix0 = max(tx0, layout.x0)
        iy0 = max(ty0, layout.y0)
        ix1 = min(tx1, layout.x1)
        iy1 = min(ty1, layout.y1)

        if ix1 <= ix0 or iy1 <= iy0:
            return 0.0

        intersection = (ix1 - ix0) * (iy1 - iy0)
        text_area = (tx1 - tx0) * (ty1 - ty0)

        if text_area <= 0:
            return 0.0

        return intersection / text_area


def get_layout_recognizer(
    model_dir: Optional[str] = None,
    **kwargs,
) -> Optional[LayoutRecognizer]:
    """
    Get a LayoutRecognizer instance if available.

    Args:
        model_dir: Optional model directory

    Returns:
        LayoutRecognizer instance or None if not available
    """
    if not ONNX_AVAILABLE:
        logger.warning("ONNX runtime not available - layout recognition disabled")
        return None

    if not CV2_AVAILABLE:
        logger.warning("OpenCV not available - layout recognition disabled")
        return None

    try:
        return LayoutRecognizer(model_dir=model_dir, **kwargs)
    except Exception as e:
        logger.error("Failed to initialize LayoutRecognizer: %s", e)
        return None
