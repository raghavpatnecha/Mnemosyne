"""
Follow-up Question Generation Service

Generates relevant follow-up questions based on:
- The user's original query
- The LLM response
- The retrieved context
- Media items found in chunks
"""

import asyncio
import json
import logging
from typing import List, Optional
from dataclasses import dataclass

from openai import AsyncOpenAI

from backend.config import settings
from backend.schemas.chat import Source, MediaItem, FollowUpQuestion

logger = logging.getLogger(__name__)


FOLLOWUP_PROMPT = """Based on the conversation below, generate 2-3 relevant follow-up questions the user might want to ask next.

USER QUESTION:
{query}

ASSISTANT RESPONSE:
{response}

AVAILABLE CONTEXT TOPICS:
{context_summary}

{media_section}

Generate follow-up questions that:
1. Dig deeper into topics mentioned in the response
2. Explore related information available in the context
3. Clarify or expand on key points
4. If media (images/tables) exist, ask about them

Output ONLY valid JSON (no markdown, no explanation):
{{
  "questions": [
    {{"question": "...", "relevance": "Brief reason why this is relevant"}}
  ]
}}"""


@dataclass
class FollowUpResult:
    """Result of follow-up question generation"""
    questions: List[FollowUpQuestion]
    generation_time_ms: int


class FollowUpService:
    """
    Service for generating follow-up questions.

    Runs in parallel with judge validation for minimal latency impact.
    """

    def __init__(self):
        """Initialize the follow-up service"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.enabled = True  # Always enabled for now
        self.model = settings.CHAT_MODEL
        self.timeout = 8  # Faster timeout for follow-ups

        logger.info(f"FollowUpService initialized with model: {self.model}")

    def _extract_media_from_sources(self, sources: List[Source]) -> List[MediaItem]:
        """
        Extract media items from source chunks.

        Looks for media references in chunk metadata and content.

        Args:
            sources: List of retrieved source chunks

        Returns:
            List of MediaItem objects
        """
        media_items = []

        for source in sources:
            doc_id = source.document.id
            doc_title = source.document.title or source.document.filename
            metadata = source.metadata or {}

            # Check for images in metadata
            if metadata.get("image_count", 0) > 0:
                images = metadata.get("images", [])
                for img in images:
                    media_items.append(MediaItem(
                        type="image",
                        source_document_id=doc_id,
                        source_document_title=doc_title,
                        description=img.get("caption") or img.get("description"),
                        page_number=img.get("page_number"),
                        url=img.get("url"),
                        content_preview=img.get("extracted_text")
                    ))

            # Check for tables in content (markdown tables)
            content = source.content or ""
            if "|" in content and "---" in content:
                # Likely contains a table
                # Extract first few rows as preview
                lines = content.split("\n")
                table_lines = [l for l in lines if l.strip().startswith("|")]
                if len(table_lines) >= 2:
                    preview = "\n".join(table_lines[:4])
                    media_items.append(MediaItem(
                        type="table",
                        source_document_id=doc_id,
                        source_document_title=doc_title,
                        description="Data table from document",
                        content_preview=preview[:200] + "..." if len(preview) > 200 else preview
                    ))

            # Check for figure references in content
            if "figure" in content.lower() or "fig." in content.lower():
                media_items.append(MediaItem(
                    type="figure",
                    source_document_id=doc_id,
                    source_document_title=doc_title,
                    description="Figure referenced in document"
                ))

            # Check chunk_metadata for media info
            chunk_meta = getattr(source, 'chunk_metadata', None) or {}
            if chunk_meta.get("has_image"):
                media_items.append(MediaItem(
                    type="image",
                    source_document_id=doc_id,
                    source_document_title=doc_title,
                    description=chunk_meta.get("image_description")
                ))

        # Deduplicate by (type, doc_id, description)
        seen = set()
        unique_items = []
        for item in media_items:
            key = (item.type, item.source_document_id, item.description or "")
            if key not in seen:
                seen.add(key)
                unique_items.append(item)

        logger.info(f"Extracted {len(unique_items)} media items from {len(sources)} sources")
        return unique_items

    def _build_context_summary(self, sources: List[Source]) -> str:
        """Build a brief summary of topics covered in sources"""
        topics = []
        for i, source in enumerate(sources[:5], 1):  # Top 5 sources
            doc_name = source.document.title or source.document.filename or "Document"
            # Get first 100 chars of content
            content_preview = (source.content or "")[:100].replace("\n", " ")
            topics.append(f"{i}. {doc_name}: {content_preview}...")

        return "\n".join(topics) if topics else "No additional context available"

    async def generate_follow_ups(
        self,
        query: str,
        response: str,
        sources: List[Source],
        media_items: Optional[List[MediaItem]] = None
    ) -> FollowUpResult:
        """
        Generate follow-up questions based on the conversation.

        Args:
            query: Original user query
            response: LLM response
            sources: Retrieved source chunks
            media_items: Pre-extracted media items (optional)

        Returns:
            FollowUpResult with questions and timing
        """
        import time
        start_time = time.time()

        if not self.enabled:
            return FollowUpResult(questions=[], generation_time_ms=0)

        try:
            # Extract media if not provided
            if media_items is None:
                media_items = self._extract_media_from_sources(sources)

            # Build context summary
            context_summary = self._build_context_summary(sources)

            # Build media section
            media_section = ""
            if media_items:
                media_lines = ["MEDIA IN SOURCES:"]
                for item in media_items[:5]:  # Limit to 5
                    media_lines.append(f"- {item.type}: {item.description or 'No description'} (from {item.source_document_title})")
                media_section = "\n".join(media_lines)

            prompt = FOLLOWUP_PROMPT.format(
                query=query,
                response=response[:1500],  # Limit response length
                context_summary=context_summary,
                media_section=media_section
            )

            result = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,  # Some creativity for diverse questions
                    max_completion_tokens=500,
                    response_format={"type": "json_object"}
                ),
                timeout=self.timeout
            )

            data = json.loads(result.choices[0].message.content)

            questions = [
                FollowUpQuestion(
                    question=q["question"],
                    relevance=q.get("relevance", "Related to the topic")
                )
                for q in data.get("questions", [])[:3]  # Max 3 questions
            ]

            generation_time = int((time.time() - start_time) * 1000)

            logger.info(f"Generated {len(questions)} follow-up questions in {generation_time}ms")

            return FollowUpResult(
                questions=questions,
                generation_time_ms=generation_time
            )

        except asyncio.TimeoutError:
            logger.warning(f"Follow-up generation timed out after {self.timeout}s")
            return FollowUpResult(questions=[], generation_time_ms=int((time.time() - start_time) * 1000))
        except Exception as e:
            logger.error(f"Follow-up generation failed: {e}")
            return FollowUpResult(questions=[], generation_time_ms=int((time.time() - start_time) * 1000))

    def extract_media(self, sources: List[Source]) -> List[MediaItem]:
        """
        Public method to extract media from sources.

        Args:
            sources: List of source chunks

        Returns:
            List of MediaItem objects
        """
        return self._extract_media_from_sources(sources)


# Singleton instance
_followup_service: Optional[FollowUpService] = None


def get_followup_service() -> FollowUpService:
    """Get or create FollowUpService singleton"""
    global _followup_service
    if _followup_service is None:
        _followup_service = FollowUpService()
    return _followup_service
