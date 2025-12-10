"""
Table Structure Recognizer using ONNX.

Detects table structure elements:
- Table boundaries
- Rows and columns
- Header cells
- Spanning cells

Ported from RAGFlow's deepdoc/vision/table_structure_recognizer.py
"""

import logging
import os
import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from backend.vision.recognizer import Recognizer, ONNX_AVAILABLE

logger = logging.getLogger(__name__)

# Model download URL (HuggingFace)
MODEL_REPO = "InfiniFlow/deepdoc"
MODEL_FILE = "tsr.onnx"

# Default model directory
DEFAULT_MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "models",
    "deepdoc",
)


class TableStructureRecognizer(Recognizer):
    """ONNX-based table structure recognizer.

    Detects table structure elements including rows, columns,
    headers, and spanning cells from table images.
    """

    # Table structure labels
    labels = [
        "table",
        "table column",
        "table row",
        "table column header",
        "table projected row header",
        "table spanning cell",
    ]

    def __init__(self, model_dir: Optional[str] = None):
        """Initialize the table structure recognizer.

        Args:
            model_dir: Directory containing the ONNX model.
                      If None, uses default location.
        """
        if model_dir is None:
            model_dir = DEFAULT_MODEL_DIR

        # Ensure model directory exists
        os.makedirs(model_dir, exist_ok=True)

        super().__init__(self.labels, "tsr", model_dir)

        # Input size for the model
        self.input_size = (640, 640)

    @classmethod
    def download_model(cls, model_dir: Optional[str] = None) -> bool:
        """Download the ONNX model from HuggingFace.

        Args:
            model_dir: Directory to save the model

        Returns:
            True if download successful
        """
        if model_dir is None:
            model_dir = DEFAULT_MODEL_DIR

        os.makedirs(model_dir, exist_ok=True)
        model_path = os.path.join(model_dir, "tsr.onnx")

        if os.path.exists(model_path):
            logger.info("Model already exists: %s", model_path)
            return True

        try:
            from huggingface_hub import hf_hub_download

            logger.info("Downloading table structure model from HuggingFace...")
            hf_hub_download(
                repo_id=MODEL_REPO,
                filename=MODEL_FILE,
                local_dir=model_dir,
                local_dir_use_symlinks=False,
            )
            logger.info("Model downloaded to: %s", model_path)
            return True

        except ImportError:
            logger.error(
                "huggingface_hub not installed. "
                "Install with: pip install huggingface_hub"
            )
            return False
        except Exception as e:
            logger.error("Failed to download model: %s", e)
            return False

    def preprocess(
        self, images: List[np.ndarray]
    ) -> List[Dict[str, np.ndarray]]:
        """Preprocess images for table structure detection.

        Args:
            images: List of table images as numpy arrays

        Returns:
            List of preprocessed input dictionaries
        """
        results = []

        for img in images:
            # Get original dimensions
            orig_h, orig_w = img.shape[:2]

            # Resize to input size
            resized = self._resize_image(img, self.input_size)

            # Normalize to [0, 1] and transpose to CHW
            normalized = resized.astype(np.float32) / 255.0

            if len(normalized.shape) == 2:
                # Grayscale to RGB
                normalized = np.stack([normalized] * 3, axis=-1)

            # Transpose HWC to CHW
            transposed = np.transpose(normalized, (2, 0, 1))

            # Add batch dimension
            batched = np.expand_dims(transposed, axis=0)

            results.append({
                "image": batched,
                "orig_size": (orig_h, orig_w),
                "scale": (
                    self.input_size[0] / orig_h,
                    self.input_size[1] / orig_w,
                ),
            })

        return results

    def postprocess(
        self,
        outputs: List[np.ndarray],
        inputs: Dict[str, Any],
        threshold: float,
    ) -> List[Dict[str, Any]]:
        """Postprocess model outputs to get table structure.

        Args:
            outputs: Model output arrays
            inputs: Original input dictionary with size info
            threshold: Confidence threshold

        Returns:
            List of detected table structure elements
        """
        # Model outputs: boxes, scores, labels
        # Adjust indices based on actual model output format
        if len(outputs) < 3:
            return []

        boxes = outputs[0]  # [N, 4] - x1, y1, x2, y2
        scores = outputs[1]  # [N]
        labels = outputs[2]  # [N]

        orig_h, orig_w = inputs["orig_size"]
        scale_y, scale_x = inputs["scale"]

        detections = []

        for i in range(len(scores)):
            score = float(scores[i])
            if score < threshold:
                continue

            label_idx = int(labels[i])
            if label_idx >= len(self.labels):
                continue

            # Scale boxes back to original size
            x1 = float(boxes[i][0]) / scale_x
            y1 = float(boxes[i][1]) / scale_y
            x2 = float(boxes[i][2]) / scale_x
            y2 = float(boxes[i][3]) / scale_y

            detections.append({
                "type": self.labels[label_idx],
                "score": score,
                "bbox": [x1, y1, x2, y2],
                "x0": x1,
                "x1": x2,
                "top": y1,
                "bottom": y2,
            })

        return detections

    def _resize_image(
        self, img: np.ndarray, target_size: Tuple[int, int]
    ) -> np.ndarray:
        """Resize image to target size.

        Args:
            img: Input image
            target_size: (height, width) tuple

        Returns:
            Resized image
        """
        try:
            from PIL import Image

            pil_img = Image.fromarray(img)
            resized = pil_img.resize(
                (target_size[1], target_size[0]),
                Image.Resampling.BILINEAR,
            )
            return np.array(resized)
        except ImportError:
            # Fallback to basic resize using numpy
            h, w = img.shape[:2]
            th, tw = target_size

            # Simple nearest-neighbor resize
            row_indices = (np.arange(th) * h / th).astype(int)
            col_indices = (np.arange(tw) * w / tw).astype(int)

            return img[row_indices][:, col_indices]

    def __call__(
        self, images: List[Any], threshold: float = 0.2
    ) -> List[List[Dict[str, Any]]]:
        """Detect table structure in images.

        Args:
            images: List of table images
            threshold: Confidence threshold (default 0.2)

        Returns:
            List of structure elements per image
        """
        raw_results = super().__call__(images, threshold)

        # Post-process to align rows and columns
        processed_results = []
        for detections in raw_results:
            processed = self._align_structure(detections)
            processed_results.append(processed)

        return processed_results

    def _align_structure(
        self, detections: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Align detected rows and columns.

        Ported from RAGFlow's alignment logic.

        Args:
            detections: Raw detection results

        Returns:
            Aligned detection results
        """
        if not detections:
            return detections

        # Separate by type
        rows = [d for d in detections if "row" in d["type"]]
        cols = [d for d in detections if "column" in d["type"]]

        # Align row left/right edges
        if rows:
            left_edges = [d["x0"] for d in rows]
            right_edges = [d["x1"] for d in rows]

            left = np.mean(left_edges) if len(left_edges) > 4 else np.min(left_edges)
            right = np.mean(right_edges) if len(right_edges) > 4 else np.max(right_edges)

            for d in rows:
                if d["x0"] > left:
                    d["x0"] = left
                if d["x1"] < right:
                    d["x1"] = right

        # Align column top/bottom edges
        if cols:
            top_edges = [d["top"] for d in cols]
            bottom_edges = [d["bottom"] for d in cols]

            top = np.median(top_edges) if len(top_edges) > 4 else np.min(top_edges)
            bottom = np.median(bottom_edges) if len(bottom_edges) > 4 else np.max(bottom_edges)

            for d in cols:
                if d["top"] > top:
                    d["top"] = top
                if d["bottom"] < bottom:
                    d["bottom"] = bottom

        return detections

    @staticmethod
    def is_caption(box: Dict[str, Any]) -> bool:
        """Check if a text box is a table caption.

        Args:
            box: Box dictionary with text and layout info

        Returns:
            True if box is likely a caption
        """
        text = box.get("text", "").strip()
        layout = box.get("layout_type", "")

        caption_patterns = [
            r"^[Tt]able\s*[0-9]+",
            r"^[Ff]ig(?:ure)?\s*[0-9]+",
        ]

        if any(re.match(p, text) for p in caption_patterns):
            return True

        if "caption" in layout.lower():
            return True

        return False

    @staticmethod
    def construct_table(
        boxes: List[Dict[str, Any]],
        is_english: bool = False,
        as_html: bool = True,
    ) -> str:
        """Construct table representation from detected cells.

        Args:
            boxes: List of cell boxes with text
            is_english: Whether content is English
            as_html: Return HTML format (vs plain text)

        Returns:
            Table as HTML or plain text
        """
        if not boxes:
            return ""

        # Remove captions
        boxes = [b for b in boxes if not TableStructureRecognizer.is_caption(b)]
        if not boxes:
            return ""

        # Sort by position
        row_heights = [b.get("bottom", 0) - b.get("top", 0) for b in boxes]
        min_height = np.min(row_heights) if row_heights else 10

        boxes = Recognizer.sort_Y_firstly(boxes, min_height / 2)

        # Group into rows
        rows = []
        current_row = [boxes[0]] if boxes else []
        current_bottom = boxes[0].get("bottom", 0) if boxes else 0

        for box in boxes[1:]:
            if box.get("top", 0) >= current_bottom - 3:
                # New row
                rows.append(current_row)
                current_row = [box]
                current_bottom = box.get("bottom", 0)
            else:
                current_row.append(box)
                current_bottom = (current_bottom + box.get("bottom", 0)) / 2

        if current_row:
            rows.append(current_row)

        # Sort cells within each row by X position
        for row in rows:
            row.sort(key=lambda b: b.get("x0", 0))

        # Build output
        if as_html:
            return TableStructureRecognizer._to_html(rows)
        else:
            return TableStructureRecognizer._to_text(rows, is_english)

    @staticmethod
    def _to_html(rows: List[List[Dict]]) -> str:
        """Convert rows to HTML table.

        Args:
            rows: List of row cell lists

        Returns:
            HTML table string
        """
        html = "<table>\n"

        for i, row in enumerate(rows):
            html += "  <tr>\n"
            for cell in row:
                text = cell.get("text", "").strip()
                colspan = cell.get("colspan", 1)
                rowspan = cell.get("rowspan", 1)

                attrs = ""
                if colspan > 1:
                    attrs += f' colspan="{colspan}"'
                if rowspan > 1:
                    attrs += f' rowspan="{rowspan}"'

                # Use th for first row (header)
                tag = "th" if i == 0 else "td"
                html += f"    <{tag}{attrs}>{text}</{tag}>\n"

            html += "  </tr>\n"

        html += "</table>"
        return html

    @staticmethod
    def _to_text(rows: List[List[Dict]], is_english: bool) -> str:
        """Convert rows to plain text representation.

        Args:
            rows: List of row cell lists
            is_english: Whether content is English

        Returns:
            Plain text table representation
        """
        lines = []
        separator = " | " if is_english else " | "

        for row in rows:
            texts = [cell.get("text", "").strip() for cell in row]
            lines.append(separator.join(texts))

        return "\n".join(lines)
