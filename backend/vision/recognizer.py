"""
Base ONNX recognizer class.

Ported from RAGFlow's deepdoc/vision/recognizer.py
"""

import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# Check for ONNX runtime availability
# Note: On Windows, ONNX runtime can cause fatal access violations during import
# We catch all exceptions and use a flag to safely disable ONNX-dependent features
ONNX_AVAILABLE = False
ort = None

try:
    import onnxruntime as ort
    # Test that ONNX actually works by checking providers
    _ = ort.get_available_providers()
    ONNX_AVAILABLE = True
    logger.debug("ONNX runtime available with providers: %s", ort.get_available_providers())
except ImportError:
    logger.info("ONNX runtime not installed - vision features disabled")
except Exception as e:
    # Catch any other errors (including Windows access violations that make it here)
    logger.warning("ONNX runtime failed to initialize: %s - vision features disabled", e)
    ort = None


class Recognizer:
    """Base class for ONNX-based document recognizers.

    Provides common functionality for loading and running ONNX models
    for document analysis tasks.
    """

    def __init__(
        self,
        labels: List[str],
        model_name: str,
        model_dir: str,
    ):
        """Initialize the recognizer.

        Args:
            labels: List of class labels the model predicts
            model_name: Name of the ONNX model file (without extension)
            model_dir: Directory containing the model file
        """
        self.labels = labels
        self.model_name = model_name
        self.model_dir = model_dir
        self.session = None
        self.input_names = []
        self.output_names = []

        if ONNX_AVAILABLE:
            self._load_model()

    def _load_model(self) -> None:
        """Load the ONNX model."""
        if not ONNX_AVAILABLE:
            logger.warning("ONNX runtime not available, model not loaded")
            return

        model_path = os.path.join(self.model_dir, f"{self.model_name}.onnx")

        if not os.path.exists(model_path):
            logger.warning("Model file not found: %s", model_path)
            return

        try:
            # Configure session options
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = (
                ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            )

            # Try GPU first, fall back to CPU
            providers = ["CPUExecutionProvider"]
            if "CUDAExecutionProvider" in ort.get_available_providers():
                providers.insert(0, "CUDAExecutionProvider")

            self.session = ort.InferenceSession(
                model_path,
                sess_options,
                providers=providers,
            )

            self.input_names = [i.name for i in self.session.get_inputs()]
            self.output_names = [o.name for o in self.session.get_outputs()]

            logger.info(
                "Loaded ONNX model: %s (providers: %s)",
                model_path,
                self.session.get_providers(),
            )

        except Exception as e:
            logger.error("Failed to load ONNX model: %s", e)
            self.session = None

    def preprocess(
        self, images: List[np.ndarray]
    ) -> List[Dict[str, np.ndarray]]:
        """Preprocess images for model input.

        Override in subclass for model-specific preprocessing.

        Args:
            images: List of images as numpy arrays

        Returns:
            List of input dictionaries for the model
        """
        raise NotImplementedError("Subclass must implement preprocess()")

    def postprocess(
        self,
        outputs: List[np.ndarray],
        inputs: Dict[str, Any],
        threshold: float,
    ) -> List[Dict[str, Any]]:
        """Postprocess model outputs.

        Override in subclass for model-specific postprocessing.

        Args:
            outputs: Model output arrays
            inputs: Original input dictionary
            threshold: Confidence threshold

        Returns:
            List of detected objects with bboxes and labels
        """
        raise NotImplementedError("Subclass must implement postprocess()")

    def __call__(
        self, images: List[Any], threshold: float = 0.5
    ) -> List[List[Dict[str, Any]]]:
        """Run inference on images.

        Args:
            images: List of images (PIL Images or numpy arrays)
            threshold: Confidence threshold for detections

        Returns:
            List of detection results per image
        """
        if not ONNX_AVAILABLE or self.session is None:
            logger.warning("ONNX model not available, returning empty results")
            return [[] for _ in images]

        # Convert images to numpy arrays
        np_images = []
        for img in images:
            if hasattr(img, "numpy"):
                np_images.append(np.array(img))
            elif isinstance(img, np.ndarray):
                np_images.append(img)
            else:
                # Try PIL Image conversion
                np_images.append(np.array(img))

        # Preprocess
        inputs_list = self.preprocess(np_images)

        # Run inference
        results = []
        for inputs in inputs_list:
            try:
                outputs = self.session.run(
                    self.output_names,
                    {name: inputs[name] for name in self.input_names},
                )
                detections = self.postprocess(outputs, inputs, threshold)
                results.append(detections)
            except Exception as e:
                logger.error("Inference failed: %s", e)
                results.append([])

        return results

    @staticmethod
    def sort_Y_firstly(boxes: List[Dict], threshold: float) -> List[Dict]:
        """Sort boxes by Y coordinate first, then X.

        Args:
            boxes: List of box dictionaries with top/bottom/x0/x1 keys
            threshold: Vertical tolerance for grouping

        Returns:
            Sorted list of boxes
        """
        if not boxes:
            return boxes

        # Group by rows
        rows = []
        sorted_boxes = sorted(boxes, key=lambda b: b.get("top", 0))

        for box in sorted_boxes:
            placed = False
            for row in rows:
                if abs(box.get("top", 0) - row[0].get("top", 0)) < threshold:
                    row.append(box)
                    placed = True
                    break
            if not placed:
                rows.append([box])

        # Sort each row by X and flatten
        result = []
        for row in rows:
            row.sort(key=lambda b: b.get("x0", 0))
            result.extend(row)

        return result

    @staticmethod
    def sort_X_firstly(boxes: List[Dict], threshold: float) -> List[Dict]:
        """Sort boxes by X coordinate first, then Y.

        Args:
            boxes: List of box dictionaries
            threshold: Horizontal tolerance for grouping

        Returns:
            Sorted list of boxes
        """
        if not boxes:
            return boxes

        # Group by columns
        cols = []
        sorted_boxes = sorted(boxes, key=lambda b: b.get("x0", 0))

        for box in sorted_boxes:
            placed = False
            for col in cols:
                if abs(box.get("x0", 0) - col[0].get("x0", 0)) < threshold:
                    col.append(box)
                    placed = True
                    break
            if not placed:
                cols.append([box])

        # Sort each column by Y and flatten
        result = []
        for col in cols:
            col.sort(key=lambda b: b.get("top", 0))
            result.extend(col)

        return result
