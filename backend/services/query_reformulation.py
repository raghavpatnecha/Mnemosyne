"""
Query Reformulation Service

Improves query understanding and retrieval accuracy through:
- Query expansion (add related terms)
- Query clarification (fix typos, expand acronyms)
- Multi-query generation (generate related queries)
"""

from typing import Union, List
import json
from openai import AsyncOpenAI
from backend.config import settings
from backend.services.cache_service import CacheService
import logging

logger = logging.getLogger(__name__)


class QueryReformulationService:
    """
    Query reformulation for better retrieval

    Techniques:
    1. Expand - Add synonyms and related terms
    2. Clarify - Fix typos, expand acronyms
    3. Multi - Generate 3-5 related queries

    Cost: ~100-200 tokens per reformulation (~$0.00003)
    Recommended: Enable for premium users only
    """

    def __init__(self):
        """Initialize OpenAI client and cache"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.cache = CacheService()
        self.enabled = settings.QUERY_REFORMULATION_ENABLED

    async def reformulate(
        self,
        query: str,
        mode: str = "expand"
    ) -> Union[str, List[str]]:
        """
        Reformulate query based on mode

        Args:
            query: Original query
            mode: Reformulation mode (expand, clarify, multi)

        Returns:
            Reformulated query (str) or list of queries (List[str])
        """
        if not self.enabled:
            logger.debug("Query reformulation disabled")
            return query if mode != "multi" else [query]

        # Check cache first
        cached = self.cache.get_reformulated_query(query, mode)
        if cached:
            if mode == "multi":
                # Use JSON instead of "|" separator to avoid ambiguity
                return json.loads(cached)
            return cached

        try:
            if mode == "expand":
                result = await self._expand_query(query)
            elif mode == "clarify":
                result = await self._clarify_query(query)
            elif mode == "multi":
                result = await self._generate_multi_queries(query)
            else:
                logger.warning(f"Unknown reformulation mode: {mode}")
                return query if mode != "multi" else [query]

            # Cache result - use JSON for multi mode to avoid separator ambiguity
            cache_value = json.dumps(result) if mode == "multi" else result
            self.cache.set_reformulated_query(query, mode, cache_value)

            return result

        except Exception as e:
            logger.error(f"Query reformulation failed: {e}")
            return query if mode != "multi" else [query]

    async def _expand_query(self, query: str) -> str:
        """
        Expand query with related terms and synonyms

        Example:
        Input: "ML models"
        Output: "ML models machine learning algorithms neural networks"
        """
        prompt = f"""Expand this search query by adding 2-3 relevant synonyms or related terms.
Keep it concise and focused on the same topic.
Only output the expanded query, nothing else.

Original query: {query}

Expanded query:"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=100,
                timeout=10.0  # Prevent hanging requests
            )

            expanded = response.choices[0].message.content.strip()

            logger.debug(f"Expanded query: '{query}' -> '{expanded}'")
            return expanded

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return query

    async def _clarify_query(self, query: str) -> str:
        """
        Clarify query by fixing typos and expanding acronyms

        Example:
        Input: "RAG implmntation"
        Output: "Retrieval Augmented Generation implementation"
        """
        prompt = f"""Fix any typos and expand acronyms in this search query.
Keep the meaning the same but make it clearer.
Only output the clarified query, nothing else.

Original query: {query}

Clarified query:"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,  # Lower temperature for clarity
                max_tokens=100,
                timeout=10.0  # Prevent hanging requests
            )

            clarified = response.choices[0].message.content.strip()

            logger.debug(f"Clarified query: '{query}' -> '{clarified}'")
            return clarified

        except Exception as e:
            logger.error(f"Query clarification failed: {e}")
            return query

    async def _generate_multi_queries(self, query: str) -> List[str]:
        """
        Generate multiple related queries

        Example:
        Input: "How does RAG work?"
        Output: [
            "How does RAG work?",
            "What is Retrieval Augmented Generation?",
            "Explain RAG architecture and components"
        ]
        """
        prompt = f"""Generate 3 different ways to search for this information.
Each query should be unique but related to the same topic.
Output only the queries, one per line, without numbering.

Original query: {query}

Alternative queries:"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200,
                timeout=10.0  # Prevent hanging requests
            )

            # Parse response
            content = response.choices[0].message.content.strip()
            lines = content.split("\n")

            # Extract queries (skip empty lines and numbering)
            queries = [query]  # Include original
            for line in lines:
                clean = line.strip().lstrip("123456789.-) ")
                if clean and clean not in queries:
                    queries.append(clean)

            # Limit to 4 total (original + 3 generated)
            queries = queries[:4]

            logger.debug(
                f"Generated {len(queries)-1} alternative queries "
                f"for: '{query}'"
            )
            return queries

        except Exception as e:
            logger.error(f"Multi-query generation failed: {e}")
            return [query]

    async def reformulate_with_context(
        self,
        query: str,
        conversation_history: List[dict],
        mode: str = "expand"
    ) -> Union[str, List[str]]:
        """
        Reformulate query with conversation context

        Uses previous messages to better understand current query

        Args:
            query: Current query
            conversation_history: Previous messages
            mode: Reformulation mode

        Returns:
            Reformulated query or queries
        """
        if not conversation_history or len(conversation_history) == 0:
            return await self.reformulate(query, mode)

        # Build context from last 3 messages
        context_messages = conversation_history[-3:]
        context = "\n".join([
            f"{msg['role']}: {msg['content'][:100]}"
            for msg in context_messages
        ])

        prompt = f"""Given this conversation context, reformulate the current query.

Context:
{context}

Current query: {query}

Reformulated query:"""

        try:
            response = await self.client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150,
                timeout=10.0  # Prevent hanging requests
            )

            reformulated = response.choices[0].message.content.strip()

            logger.debug(
                f"Reformulated with context: '{query}' -> '{reformulated}'"
            )
            return reformulated

        except Exception as e:
            logger.error(f"Context-aware reformulation failed: {e}")
            return await self.reformulate(query, mode)

    def is_available(self) -> bool:
        """Check if reformulation is available"""
        return self.enabled and settings.OPENAI_API_KEY is not None
