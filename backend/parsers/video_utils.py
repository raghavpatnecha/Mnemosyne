"""
Video processing utilities
Helper functions for ffmpeg operations and metadata extraction
"""

import json
import logging
import subprocess
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def check_ffmpeg_installed(ffmpeg_path: str = "ffmpeg") -> bool:
    """
    Check if ffmpeg is installed and accessible

    Args:
        ffmpeg_path: Path to ffmpeg binary

    Returns:
        True if ffmpeg is available
    """
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def extract_audio_from_video(
    video_path: str,
    output_path: str,
    ffmpeg_path: str = "ffmpeg"
) -> bool:
    """
    Extract audio from video file using ffmpeg

    Args:
        video_path: Path to video file
        output_path: Path for output WAV file
        ffmpeg_path: Path to ffmpeg binary

    Returns:
        True if extraction succeeded
    """
    if not check_ffmpeg_installed(ffmpeg_path):
        raise RuntimeError(
            f"ffmpeg not found at {ffmpeg_path}. "
            "Install with: apt-get install ffmpeg (Linux) or brew install ffmpeg (Mac)"
        )

    cmd = [
        ffmpeg_path,
        "-i", video_path,  # Input video
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # PCM 16-bit
        "-ar", "16000",  # 16kHz sample rate
        "-ac", "1",  # Mono
        "-y",  # Overwrite output
        output_path
    ]

    try:
        logger.info(f"Extracting audio from video using ffmpeg")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr}")
            return False

        logger.info(f"Audio extracted successfully")
        return True

    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timeout: video processing took > 5 minutes")
        return False
    except Exception as e:
        logger.error(f"Error extracting audio: {e}")
        return False


def get_video_metadata(
    video_path: str,
    ffprobe_path: str = "ffprobe"
) -> Dict[str, Any]:
    """
    Extract video metadata using ffprobe

    Args:
        video_path: Path to video file
        ffprobe_path: Path to ffprobe binary

    Returns:
        Dictionary with video metadata
    """
    cmd = [
        ffprobe_path,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        video_path
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            logger.warning(f"ffprobe failed: {result.stderr}")
            return {}

        data = json.loads(result.stdout)

        # Extract format info
        format_info = data.get("format", {})

        # Find video stream
        video_stream = next(
            (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
            {}
        )

        # Calculate FPS
        fps = 0
        if video_stream.get("r_frame_rate"):
            try:
                num, den = map(int, video_stream["r_frame_rate"].split("/"))
                fps = num / den if den != 0 else 0
            except (ValueError, ZeroDivisionError):
                fps = 0

        return {
            "duration_seconds": float(format_info.get("duration", 0)),
            "file_size_bytes": int(format_info.get("size", 0)),
            "format_name": format_info.get("format_name"),
            "bit_rate": int(format_info.get("bit_rate", 0)),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": round(fps, 2),
            "codec": video_stream.get("codec_name"),
        }

    except (json.JSONDecodeError, subprocess.TimeoutExpired, Exception) as e:
        logger.error(f"Error extracting video metadata: {e}")
        return {}
