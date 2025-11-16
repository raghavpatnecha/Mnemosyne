"""
YouTube Parser for video transcripts
Extracts transcripts from YouTube videos using YouTube Transcript API
Supports: Standard, shortened, and embed YouTube URLs
"""

import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional
from urllib.parse import parse_qs, urlparse

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    YOUTUBE_API_AVAILABLE = True
except ImportError:
    YOUTUBE_API_AVAILABLE = False
    YouTubeTranscriptApi = None

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    aiohttp = None

from backend.config import settings

logger = logging.getLogger(__name__)


class YouTubeParser:
    """
    Parser for YouTube videos using Transcript API

    Supports YouTube URL formats:
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID

    Extracts:
    - Video transcript with timestamps
    - Video metadata (title, author, thumbnail)
    """

    SUPPORTED_FORMATS = {
        "text/html",          # YouTube URLs in HTML
        "video/youtube",      # Custom MIME type for YouTube
        "application/x-youtube",  # Alternative MIME type
    }

    # YouTube URL patterns
    YOUTUBE_DOMAINS = {"youtu.be", "www.youtube.com", "youtube.com", "m.youtube.com"}

    def __init__(self):
        """Initialize YouTubeParser"""
        if not YOUTUBE_API_AVAILABLE:
            logger.error("youtube-transcript-api is not installed")
            raise ImportError(
                "youtube-transcript-api is required for YouTubeParser. "
                "Install with: pip install youtube-transcript-api"
            )

        if not AIOHTTP_AVAILABLE:
            logger.error("aiohttp is not installed")
            raise ImportError(
                "aiohttp is required for YouTubeParser. "
                "Install with: pip install aiohttp"
            )

    def can_parse(self, content_type: str) -> bool:
        """
        Check if this parser can handle the content type

        Args:
            content_type: MIME type (e.g., "text/html")

        Returns:
            True if parser supports this content type
        """
        return content_type in self.SUPPORTED_FORMATS

    def is_youtube_url(self, text: str) -> bool:
        """
        Check if text contains a YouTube URL

        Args:
            text: Text to check

        Returns:
            True if text contains YouTube URL
        """
        try:
            parsed = urlparse(text)
            return parsed.hostname in self.YOUTUBE_DOMAINS
        except Exception:
            return False

    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract YouTube video ID from various URL formats

        Args:
            url: YouTube URL

        Returns:
            Video ID if found, None otherwise
        """
        parsed_url = urlparse(url)
        hostname = parsed_url.hostname

        try:
            # Format: https://youtu.be/VIDEO_ID
            if hostname == "youtu.be":
                return parsed_url.path[1:]  # Remove leading slash

            # Format: https://www.youtube.com/watch?v=VIDEO_ID
            if hostname in ("www.youtube.com", "youtube.com", "m.youtube.com"):
                if parsed_url.path == "/watch":
                    query_params = parse_qs(parsed_url.query)
                    return query_params.get("v", [None])[0]

                # Format: https://www.youtube.com/embed/VIDEO_ID
                if parsed_url.path.startswith("/embed/"):
                    return parsed_url.path.split("/")[2]

                # Format: https://www.youtube.com/v/VIDEO_ID
                if parsed_url.path.startswith("/v/"):
                    return parsed_url.path.split("/")[2]

        except (IndexError, KeyError, AttributeError) as e:
            logger.error(f"Error extracting video ID from {url}: {e}")
            return None

        return None

    async def fetch_video_metadata(self, video_id: str) -> Dict[str, Any]:
        """
        Fetch video metadata using YouTube oEmbed API

        Args:
            video_id: YouTube video ID

        Returns:
            Dictionary with video metadata
        """
        oembed_url = "https://www.youtube.com/oembed"
        params = {
            "format": "json",
            "url": f"https://www.youtube.com/watch?v={video_id}",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(oembed_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "title": data.get("title", "Unknown Title"),
                            "author": data.get("author_name", "Unknown Author"),
                            "thumbnail": data.get("thumbnail_url"),
                        }
                    else:
                        logger.warning(
                            f"Failed to fetch metadata for video {video_id}: "
                            f"HTTP {response.status}"
                        )
                        return {}
        except Exception as e:
            logger.error(f"Error fetching video metadata for {video_id}: {e}")
            return {}

    def format_timestamp(self, seconds: float) -> str:
        """
        Format seconds as MM:SS

        Args:
            seconds: Time in seconds

        Returns:
            Formatted timestamp (e.g., "03:45")
        """
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins:02d}:{secs:02d}"

    async def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse YouTube URL and extract transcript

        Args:
            file_path: Path to file containing YouTube URL (or URL string)

        Returns:
            Dict with:
                - content: Transcript with timestamps
                - metadata: Video metadata
                - page_count: None
        """
        # Read URL from file or use path as URL
        url = file_path
        path = Path(file_path)

        if path.exists() and path.is_file():
            try:
                url = path.read_text().strip()
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                url = file_path

        # Extract video ID
        video_id = self.extract_video_id(url)
        if not video_id:
            error_msg = f"Could not extract YouTube video ID from: {url}"
            logger.error(error_msg)
            return {
                "content": "",
                "metadata": {"error": error_msg},
                "page_count": None
            }

        logger.info(f"Extracting transcript for YouTube video: {video_id}")

        try:
            # Fetch transcript
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)

            # Format transcript with timestamps
            transcript_lines = []
            for segment in transcript_list:
                start_time = segment["start"]
                text = segment["text"]
                timestamp = self.format_timestamp(start_time)
                transcript_lines.append(f"[{timestamp}] {text}")

            full_transcript = "\n".join(transcript_lines)

            # Calculate duration
            last_segment = transcript_list[-1]
            duration = last_segment["start"] + last_segment.get("duration", 0)

            # Fetch metadata
            metadata = await self.fetch_video_metadata(video_id)

            # Build result
            result_metadata = {
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "title": metadata.get("title", "Unknown Title"),
                "author": metadata.get("author", "Unknown Author"),
                "thumbnail": metadata.get("thumbnail"),
                "duration_seconds": duration,
                "transcript_segments": len(transcript_list),
                "source": "youtube",
            }

            logger.info(
                f"Successfully extracted YouTube transcript: {video_id} "
                f"({len(transcript_list)} segments, {duration:.1f}s)"
            )

            return {
                "content": full_transcript,
                "metadata": result_metadata,
                "page_count": None
            }

        except Exception as e:
            error_msg = f"Failed to extract transcript for video {video_id}: {str(e)}"
            logger.error(error_msg)
            return {
                "content": "",
                "metadata": {
                    "error": error_msg,
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}"
                },
                "page_count": None
            }
