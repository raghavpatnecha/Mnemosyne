"""
Vision operators for image preprocessing and postprocessing.

Provides utilities for:
- Image normalization and standardization
- Resizing and padding
- Non-Maximum Suppression (NMS)
- Box manipulation

Ported from RAGFlow's deepdoc/vision/operators.py
"""

import logging
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

# Check for OpenCV availability
CV2_AVAILABLE = False
cv2 = None

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    logger.info("OpenCV not installed - some vision operators unavailable")
except Exception as e:
    logger.warning("OpenCV failed to initialize: %s - vision operators unavailable", e)

# Check for PIL availability
PIL_AVAILABLE = False
Image = None

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    logger.info("PIL not installed - some image operations unavailable")
except Exception as e:
    logger.warning("PIL failed to initialize: %s", e)


def nms(boxes: np.ndarray, scores: np.ndarray, iou_threshold: float = 0.5) -> List[int]:
    """
    Non-Maximum Suppression for bounding boxes.

    Args:
        boxes: Array of boxes with shape (N, 4) as [x1, y1, x2, y2]
        scores: Array of confidence scores with shape (N,)
        iou_threshold: IoU threshold for suppression

    Returns:
        List of indices to keep
    """
    if len(boxes) == 0:
        return []

    # Convert to float
    boxes = boxes.astype(np.float32)
    scores = scores.astype(np.float32)

    # Get coordinates
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]

    # Compute areas
    areas = (x2 - x1) * (y2 - y1)

    # Sort by score descending
    order = scores.argsort()[::-1]

    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)

        if order.size == 1:
            break

        # Compute IoU with remaining boxes
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])

        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        intersection = w * h

        iou = intersection / (areas[i] + areas[order[1:]] - intersection + 1e-6)

        # Keep boxes with IoU below threshold
        inds = np.where(iou <= iou_threshold)[0]
        order = order[inds + 1]

    return keep


def resize_image(
    image: np.ndarray,
    target_size: Tuple[int, int],
    keep_ratio: bool = True,
    pad_value: int = 114,
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Resize image with optional aspect ratio preservation.

    Args:
        image: Input image as numpy array (H, W, C)
        target_size: Target size as (height, width)
        keep_ratio: Whether to preserve aspect ratio
        pad_value: Value for padding when keeping ratio

    Returns:
        Tuple of (resized image, resize info dict)
    """
    if not CV2_AVAILABLE:
        raise RuntimeError("OpenCV required for resize_image")

    h, w = image.shape[:2]
    target_h, target_w = target_size

    if keep_ratio:
        # Calculate scale factor
        scale = min(target_h / h, target_w / w)
        new_h = int(h * scale)
        new_w = int(w * scale)

        # Resize
        resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        # Calculate padding
        pad_h = target_h - new_h
        pad_w = target_w - new_w
        top = pad_h // 2
        bottom = pad_h - top
        left = pad_w // 2
        right = pad_w - left

        # Apply padding
        if len(image.shape) == 3:
            padded = cv2.copyMakeBorder(
                resized, top, bottom, left, right,
                cv2.BORDER_CONSTANT, value=(pad_value, pad_value, pad_value)
            )
        else:
            padded = cv2.copyMakeBorder(
                resized, top, bottom, left, right,
                cv2.BORDER_CONSTANT, value=pad_value
            )

        info = {
            "scale": scale,
            "pad_top": top,
            "pad_left": left,
            "original_size": (h, w),
            "resized_size": (new_h, new_w),
        }
        return padded, info
    else:
        resized = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_LINEAR)
        info = {
            "scale_x": target_w / w,
            "scale_y": target_h / h,
            "original_size": (h, w),
        }
        return resized, info


def normalize_image(
    image: np.ndarray,
    mean: Optional[List[float]] = None,
    std: Optional[List[float]] = None,
    scale: float = 1.0 / 255.0,
) -> np.ndarray:
    """
    Normalize image with mean subtraction and std division.

    Args:
        image: Input image as numpy array
        mean: Mean values per channel (default: ImageNet mean)
        std: Std values per channel (default: ImageNet std)
        scale: Scale factor before normalization

    Returns:
        Normalized image
    """
    if mean is None:
        mean = [0.485, 0.456, 0.406]
    if std is None:
        std = [0.229, 0.224, 0.225]

    # Convert to float and scale
    img = image.astype(np.float32) * scale

    # Normalize
    mean = np.array(mean, dtype=np.float32).reshape(1, 1, -1)
    std = np.array(std, dtype=np.float32).reshape(1, 1, -1)

    img = (img - mean) / std
    return img


def hwc_to_chw(image: np.ndarray) -> np.ndarray:
    """Convert image from HWC to CHW format."""
    if image.ndim == 3:
        return image.transpose(2, 0, 1)
    return image


def chw_to_hwc(image: np.ndarray) -> np.ndarray:
    """Convert image from CHW to HWC format."""
    if image.ndim == 3:
        return image.transpose(1, 2, 0)
    return image


def scale_boxes(
    boxes: np.ndarray,
    scale_info: Dict[str, Any],
    to_original: bool = True,
) -> np.ndarray:
    """
    Scale bounding boxes based on resize info.

    Args:
        boxes: Boxes with shape (N, 4) as [x1, y1, x2, y2]
        scale_info: Dict from resize_image containing scale/pad info
        to_original: If True, scale from resized to original coords

    Returns:
        Scaled boxes
    """
    boxes = boxes.copy().astype(np.float32)

    if "scale" in scale_info:
        # Aspect-ratio preserving resize was used
        scale = scale_info["scale"]
        pad_left = scale_info.get("pad_left", 0)
        pad_top = scale_info.get("pad_top", 0)

        if to_original:
            # Remove padding offset
            boxes[:, [0, 2]] -= pad_left
            boxes[:, [1, 3]] -= pad_top
            # Scale back to original
            boxes /= scale
        else:
            # Scale to resized
            boxes *= scale
            # Add padding offset
            boxes[:, [0, 2]] += pad_left
            boxes[:, [1, 3]] += pad_top
    else:
        # Non-aspect-ratio preserving resize
        scale_x = scale_info.get("scale_x", 1.0)
        scale_y = scale_info.get("scale_y", 1.0)

        if to_original:
            boxes[:, [0, 2]] /= scale_x
            boxes[:, [1, 3]] /= scale_y
        else:
            boxes[:, [0, 2]] *= scale_x
            boxes[:, [1, 3]] *= scale_y

    return boxes


def clip_boxes(boxes: np.ndarray, image_shape: Tuple[int, int]) -> np.ndarray:
    """
    Clip boxes to image boundaries.

    Args:
        boxes: Boxes with shape (N, 4) as [x1, y1, x2, y2]
        image_shape: Image shape as (height, width)

    Returns:
        Clipped boxes
    """
    boxes = boxes.copy()
    h, w = image_shape

    boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, w)
    boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, h)

    return boxes


def compute_iou(box1: np.ndarray, box2: np.ndarray) -> float:
    """
    Compute IoU between two boxes.

    Args:
        box1: First box as [x1, y1, x2, y2]
        box2: Second box as [x1, y1, x2, y2]

    Returns:
        IoU value
    """
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection

    return intersection / (union + 1e-6)


def box_area(boxes: np.ndarray) -> np.ndarray:
    """
    Compute area of boxes.

    Args:
        boxes: Boxes with shape (N, 4) as [x1, y1, x2, y2]

    Returns:
        Areas with shape (N,)
    """
    return (boxes[:, 2] - boxes[:, 0]) * (boxes[:, 3] - boxes[:, 1])


class ImagePreprocessor:
    """
    Configurable image preprocessing pipeline.

    Combines multiple preprocessing steps into a single callable.
    """

    def __init__(
        self,
        target_size: Optional[Tuple[int, int]] = None,
        keep_ratio: bool = True,
        normalize: bool = True,
        mean: Optional[List[float]] = None,
        std: Optional[List[float]] = None,
        to_chw: bool = True,
        to_float32: bool = True,
    ):
        """
        Initialize preprocessor.

        Args:
            target_size: Target size as (height, width), None to skip resize
            keep_ratio: Whether to preserve aspect ratio when resizing
            normalize: Whether to apply normalization
            mean: Mean values for normalization
            std: Std values for normalization
            to_chw: Whether to convert to CHW format
            to_float32: Whether to convert to float32
        """
        self.target_size = target_size
        self.keep_ratio = keep_ratio
        self.normalize = normalize
        self.mean = mean
        self.std = std
        self.to_chw = to_chw
        self.to_float32 = to_float32

    def __call__(
        self, image: Union[np.ndarray, "Image.Image"]
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Process an image.

        Args:
            image: Input image (numpy array or PIL Image)

        Returns:
            Tuple of (processed image, preprocessing info)
        """
        # Convert PIL to numpy
        if PIL_AVAILABLE and isinstance(image, Image.Image):
            image = np.array(image)

        info = {"original_shape": image.shape}

        # Resize if target size specified
        if self.target_size is not None:
            if not CV2_AVAILABLE:
                raise RuntimeError("OpenCV required for resizing")
            image, resize_info = resize_image(
                image, self.target_size, self.keep_ratio
            )
            info.update(resize_info)

        # Normalize
        if self.normalize:
            image = normalize_image(image, self.mean, self.std)
        elif self.to_float32:
            image = image.astype(np.float32) / 255.0

        # Convert to CHW
        if self.to_chw:
            image = hwc_to_chw(image)

        return image, info
