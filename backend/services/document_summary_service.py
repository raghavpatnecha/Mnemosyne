"""
Document Summary Service
Generate document-level summaries and embeddings for hierarchical search
"""

import logging
from typing import Dict, Any, List
from litellm import acompletion
from backend.config import settings
from backend.embeddings.openai_embedder import OpenAIEmbedder

logger = logging.getLogger(__name__)


class DocumentSummaryService:
    """
    Generate document-level summaries and embeddings for hierarchical retrieval

    Two strategies:
    1. Concatenation: Fast, uses first N chars + metadata (recommended for scale)
    2. LLM Summarization: High quality, uses LLM to generate concise summary

    The summary is then embedded to create document_embedding for tier-1 search.
    """

    def __init__(self):
        """Initialize document summary service"""
        self.embedder = OpenAIEmbedder()
        self.llm_provider = settings.LLM_PROVIDER
        self.chat_model = settings.CHAT_MODEL

    async def generate_document_summary(
        self,
        content: str,
        metadata: Dict[str, Any],
        strategy: str = "concat"
    ) -> str:
        """
        Generate document summary for embedding

        Args:
            content: Full document content
            metadata: Document metadata (title, filename, etc.)
            strategy: "concat" (fast) or "llm" (high quality)

        Returns:
            Summary text for embedding
        """
        if strategy == "concat":
            return self._concat_strategy(content, metadata)
        elif strategy == "llm":
            return await self._llm_summary_strategy(content, metadata)
        else:
            logger.warning(f"Unknown strategy '{strategy}', using 'concat'")
            return self._concat_strategy(content, metadata)

    def _concat_strategy(self, content: str, metadata: Dict) -> str:
        """
        Fast concatenation strategy: metadata + first 2000 chars

        This is the recommended strategy for production as it:
        - No LLM API calls (free, fast)
        - Consistent quality
        - Scales to millions of documents

        Args:
            content: Document content
            metadata: Document metadata

        Returns:
            Concatenated summary
        """
        title = metadata.get("title", "")
        filename = metadata.get("filename", "")

        # Build summary with metadata
        summary_parts = []

        if title:
            summary_parts.append(f"Title: {title}")
        if filename:
            summary_parts.append(f"File: {filename}")

        # Add content preview (first 2000 chars)
        content_preview = content[:2000].strip()
        if content_preview:
            summary_parts.append(content_preview)

        summary = "\n".join(summary_parts)

        logger.debug(f"Generated concat summary: {len(summary)} chars")
        return summary

    async def _llm_summary_strategy(self, content: str, metadata: Dict) -> str:
        """
        LLM-based summarization: high quality, uses API calls

        This strategy is best for:
        - Small document collections (< 10k docs)
        - When quality > cost/speed
        - Documents with complex structure

        Args:
            content: Document content
            metadata: Document metadata

        Returns:
            LLM-generated summary
        """
        title = metadata.get("title", "")
        filename = metadata.get("filename", "")

        # Truncate content to fit context window (leave room for prompt)
        max_content_length = 8000  # ~2000 tokens
        truncated_content = content[:max_content_length].strip()

        # Build LLM prompt
        prompt = f"""Summarize the following document in 2-3 concise paragraphs that capture:
1. Main topic and purpose
2. Key points and concepts
3. Important details

Document Title: {title}
Filename: {filename}

Content:
{truncated_content}

Summary:"""

        try:
            # Use LiteLLM for multi-provider support
            model_string = (
                settings.LLM_MODEL_STRING
                or f"{self.llm_provider}/{self.chat_model}"
            )

            logger.debug(f"Generating LLM summary with {model_string}")

            response = await acompletion(
                model=model_string,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
                timeout=settings.LLM_TIMEOUT
            )

            summary_text = response.choices[0].message.content.strip()

            # Enhance with metadata
            enhanced_summary = f"Title: {title}\nFile: {filename}\n\n{summary_text}"

            logger.debug(f"Generated LLM summary: {len(enhanced_summary)} chars")
            return enhanced_summary

        except Exception as e:
            logger.error(f"LLM summarization failed: {e}, falling back to concat")
            # Fallback to concatenation strategy
            return self._concat_strategy(content, metadata)

    async def generate_document_embedding(self, summary: str) -> List[float]:
        """
        Generate embedding from document summary

        Args:
            summary: Document summary text

        Returns:
            Embedding vector (1536 dimensions)
        """
        embedding = await self.embedder.embed(summary)
        logger.debug(f"Generated document embedding: {len(embedding)} dimensions")
        return embedding

    async def generate_summary_and_embedding(
        self,
        content: str,
        metadata: Dict[str, Any],
        strategy: str = "concat"
    ) -> Dict[str, Any]:
        """
        Generate both summary and embedding in one call

        Args:
            content: Full document content
            metadata: Document metadata
            strategy: Summarization strategy

        Returns:
            Dict with 'summary' and 'embedding' keys
        """
        summary = await self.generate_document_summary(content, metadata, strategy)
        embedding = await self.generate_document_embedding(summary)

        return {
            "summary": summary,
            "embedding": embedding
        }
