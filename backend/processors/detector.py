"""
LLM-based document type detection.

Uses a language model to classify documents into domain categories
for intelligent processor selection.
"""

import logging
from typing import Optional

import litellm

from backend.config import settings

logger = logging.getLogger(__name__)

# Detection prompt template
DETECTION_PROMPT = """Classify this document into exactly one of these categories based on its content and structure:

- legal: Laws, contracts, regulations, legal agreements, terms of service, privacy policies, NDAs, court documents, legislation
- academic: Research papers, academic articles, scientific publications, journal papers, theses, dissertations, conference papers
- qa: FAQ documents, Q&A formats, exam papers, interview questions, quizzes, help documentation with question-answer structure
- table: Documents primarily containing tabular data, spreadsheets, data reports, financial statements with tables
- book: Books, novels, long-form documents with chapters, parts, volumes, table of contents, preface, appendix
- email: Email messages, email threads, correspondence with From/To/Subject headers, .eml files
- manual: Technical documentation, user guides, installation guides, how-to documents, troubleshooting guides, procedures
- presentation: Slide decks, presentations, PowerPoint files, slides with bullet points and titles
- resume: CVs, resumes, curriculum vitae, job applications with experience, education, skills sections
- general: Everything else that doesn't clearly fit the above categories

Document excerpt (analyze this content):
---
{content}
---

Important: Respond with ONLY the category name (one word). No explanation needed."""


class DocumentTypeDetector:
    """Detects document type using LLM classification."""

    # Valid document types
    VALID_TYPES = {
        "legal", "academic", "qa", "table", "general",
        "book", "email", "manual", "presentation", "resume",
    }

    # Excerpt length for classification (balance accuracy vs cost)
    EXCERPT_LENGTH = 3000

    @classmethod
    async def detect(
        cls,
        content: str,
        model: Optional[str] = None,
    ) -> str:
        """Detect document type using LLM classification.

        Args:
            content: Full document text content
            model: LLM model to use (defaults to CHAT_MODEL setting)

        Returns:
            Detected document type (legal, academic, qa, table, book, email, manual, presentation, resume, or general)
        """
        # Use configured model (same as chat for consistency)
        # User can override via LLM_MODEL_STRING or pass model directly
        detection_model = model or settings.LLM_MODEL_STRING or settings.CHAT_MODEL

        # Take excerpt from beginning and middle for better representation
        excerpt = cls._get_representative_excerpt(content)

        try:
            response = await litellm.acompletion(
                model=detection_model,
                messages=[
                    {
                        "role": "user",
                        "content": DETECTION_PROMPT.format(content=excerpt),
                    }
                ],
                temperature=0,  # Deterministic output
                max_tokens=20,  # Only need single word
            )

            detected = response.choices[0].message.content.strip().lower()

            # Validate response
            if detected in cls.VALID_TYPES:
                logger.debug("LLM classified document as: %s", detected)
                return detected

            # Handle variations
            detected_cleaned = cls._normalize_response(detected)
            if detected_cleaned in cls.VALID_TYPES:
                logger.debug("LLM classified document as: %s", detected_cleaned)
                return detected_cleaned

            logger.warning(
                "LLM returned invalid type '%s', defaulting to 'general'", detected
            )
            return "general"

        except Exception as e:
            logger.error("Document type detection failed: %s", e)
            return "general"

    @classmethod
    def _get_representative_excerpt(cls, content: str) -> str:
        """Get representative excerpt from document.

        Takes content from beginning and middle of document to capture
        both headers/intro and body content.

        Args:
            content: Full document content

        Returns:
            Representative excerpt string
        """
        content = content.strip()
        total_length = len(content)

        if total_length <= cls.EXCERPT_LENGTH:
            return content

        # Take 2/3 from beginning (captures title, headers, intro)
        # Take 1/3 from middle (captures body content)
        begin_length = (cls.EXCERPT_LENGTH * 2) // 3
        middle_length = cls.EXCERPT_LENGTH - begin_length

        begin_excerpt = content[:begin_length]

        # Get middle excerpt
        middle_start = (total_length - middle_length) // 2
        middle_excerpt = content[middle_start : middle_start + middle_length]

        return f"{begin_excerpt}\n\n[...]\n\n{middle_excerpt}"

    @classmethod
    def _normalize_response(cls, response: str) -> str:
        """Normalize LLM response to valid type.

        Handles common variations like "Legal Document" -> "legal"

        Args:
            response: Raw LLM response

        Returns:
            Normalized type string
        """
        response = response.lower().strip()

        # Remove common suffixes
        for suffix in [" document", " paper", " content", " format", " type"]:
            if response.endswith(suffix):
                response = response[: -len(suffix)]

        # Handle common variations
        variations = {
            "law": "legal",
            "contract": "legal",
            "legislation": "legal",
            "research": "academic",
            "paper": "academic",
            "scientific": "academic",
            "faq": "qa",
            "question": "qa",
            "exam": "qa",
            "tabular": "table",
            "spreadsheet": "table",
            "data": "table",
            "novel": "book",
            "chapter": "book",
            "volume": "book",
            "correspondence": "email",
            "mail": "email",
            "message": "email",
            "guide": "manual",
            "documentation": "manual",
            "technical": "manual",
            "howto": "manual",
            "how-to": "manual",
            "slides": "presentation",
            "deck": "presentation",
            "powerpoint": "presentation",
            "ppt": "presentation",
            "cv": "resume",
            "curriculum": "resume",
            "other": "general",
            "none": "general",
            "unknown": "general",
        }

        return variations.get(response, response)
