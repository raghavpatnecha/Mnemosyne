"""
Deep Reasoning Service - Multi-step iterative reasoning for complex queries

Inspired by RAGFlow's agentic reasoning, this service:
1. Decomposes complex queries into sub-queries
2. Performs iterative retrieval for each sub-query
3. Aggregates and deduplicates results
4. Provides enhanced context for final answer generation
"""

import logging
from typing import List, Optional, Dict, Any, AsyncGenerator
from dataclasses import dataclass
from uuid import UUID

import litellm

from backend.config import settings
from backend.schemas.chat import StreamChunk, RetrievalConfig

logger = logging.getLogger(__name__)


@dataclass
class ReasoningResult:
    """Result from deep reasoning pipeline"""
    context: str  # Combined context from all sub-queries
    sub_queries: List[str]  # Generated sub-queries
    all_sources: List[Any]  # All unique sources found
    iterations: int  # Number of retrieval iterations
    reasoning_trace: List[Dict[str, Any]]  # Trace of reasoning steps


class DeepReasoningService:
    """
    Multi-step iterative reasoning service.

    Pipeline:
    1. Query Analysis: Decompose complex query into sub-queries
    2. Iterative Retrieval: Search for each sub-query
    3. Aggregation: Combine and deduplicate results
    4. Synthesis: Build comprehensive context
    """

    MAX_SUB_QUERIES = 3
    DEFAULT_TOP_K_PER_QUERY = 5

    def __init__(self):
        """Initialize reasoning service with LLM for query decomposition"""
        self.model = self._get_model_string()

    def _get_model_string(self) -> str:
        """Get LLM model string for decomposition"""
        if settings.LLM_MODEL_STRING:
            return settings.LLM_MODEL_STRING
        return f"{settings.LLM_PROVIDER}/{settings.CHAT_MODEL}"

    async def decompose_query(self, query: str) -> List[str]:
        """
        Break complex query into searchable sub-queries.

        Uses LLM to analyze the question and generate focused sub-questions
        that together would comprehensively answer the original.

        Args:
            query: Original user question

        Returns:
            List of sub-queries (including original)
        """
        decomposition_prompt = f"""You are a query decomposition specialist. Break down this question into search-optimized sub-queries.

QUESTION: {query}

THINK STEP BY STEP:
1. What is the user's core intent?
2. What key entities (names, concepts, terms) must appear in searches?
3. What different aspects need coverage? (definition, process, comparison, cause, timeline)

GENERATE 2-3 SUB-QUERIES that:
- Are search-friendly (short, keyword-rich, specific)
- Cover DIFFERENT aspects (no overlap)
- Include key entities from the original question

OUTPUT: Only the sub-queries, one per line, prefixed with "- "
No explanations or other text.

SUB-QUERIES:"""

        try:
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": decomposition_prompt}],
                temperature=0.2,
                max_tokens=500,
                api_key=settings.OPENAI_API_KEY if "openai" in self.model else None,
            )

            response_text = response.choices[0].message.content

            # Parse sub-queries from response
            sub_queries = [
                line.strip().lstrip("- ").lstrip("* ")
                for line in response_text.split("\n")
                if line.strip() and (line.strip().startswith("-") or line.strip().startswith("*"))
            ]

            # Limit and always include original
            sub_queries = sub_queries[:self.MAX_SUB_QUERIES]

            logger.info(f"Decomposed query into {len(sub_queries)} sub-queries")
            return [query] + sub_queries

        except Exception as e:
            logger.warning(f"Query decomposition failed: {e}, using original query only")
            return [query]

    async def reason_with_streaming(
        self,
        query: str,
        user: Any,
        collection_id: Optional[UUID],
        retrieval_config: RetrievalConfig,
        call_retrieval_fn: Any,
        build_sources_fn: Any,
    ) -> AsyncGenerator[StreamChunk, None]:
        """
        Execute deep reasoning with streaming progress updates.

        Yields StreamChunk objects for each reasoning step.

        Args:
            query: Original user query
            user: User object for retrieval
            collection_id: Collection to search
            retrieval_config: Base retrieval configuration
            call_retrieval_fn: Function to call retrieval endpoint
            build_sources_fn: Function to build source objects

        Yields:
            StreamChunk objects (reasoning_step, sub_query types)
        """
        reasoning_trace = []

        # Step 1: Query Decomposition
        yield StreamChunk(
            type="reasoning_step",
            step=1,
            description="Analyzing query and identifying sub-questions..."
        )

        sub_queries = await self.decompose_query(query)
        reasoning_trace.append({
            "step": 1,
            "action": "decompose",
            "sub_queries": sub_queries
        })

        # Yield each sub-query
        for i, sq in enumerate(sub_queries[1:], 1):  # Skip original (first)
            yield StreamChunk(
                type="sub_query",
                step=i,
                query=sq
            )

        # Step 2: Iterative Retrieval
        yield StreamChunk(
            type="reasoning_step",
            step=2,
            description=f"Searching knowledge base ({len(sub_queries)} queries)..."
        )

        all_results = []
        seen_chunk_ids = set()

        for i, sq in enumerate(sub_queries):
            # Adjust top_k for sub-queries
            config = RetrievalConfig(
                mode=retrieval_config.mode,
                top_k=self.DEFAULT_TOP_K_PER_QUERY,
                rerank=retrieval_config.rerank,
                enable_graph=retrieval_config.enable_graph,
                hierarchical=retrieval_config.hierarchical,
                expand_context=retrieval_config.expand_context,
                metadata_filter=retrieval_config.metadata_filter,
            )

            try:
                result = await call_retrieval_fn(
                    query=sq,
                    user=user,
                    collection_id=collection_id,
                    config=config
                )

                # Deduplicate results by chunk_id
                for r in result["results"]:
                    if r.chunk_id not in seen_chunk_ids:
                        seen_chunk_ids.add(r.chunk_id)
                        all_results.append(r)

            except Exception as e:
                logger.warning(f"Retrieval failed for sub-query '{sq}': {e}")

        reasoning_trace.append({
            "step": 2,
            "action": "retrieve",
            "total_unique_chunks": len(all_results)
        })

        # Step 3: Synthesis
        yield StreamChunk(
            type="reasoning_step",
            step=3,
            description="Synthesizing comprehensive answer..."
        )

        # Sort by score (best first)
        all_results.sort(key=lambda x: x.score, reverse=True)

        # Limit total results
        max_results = retrieval_config.top_k * 2  # Allow more for deep reasoning
        all_results = all_results[:max_results]

        # Build sources
        sources = build_sources_fn(all_results)

        reasoning_trace.append({
            "step": 3,
            "action": "synthesize",
            "final_sources": len(sources)
        })

        # Store result for retrieval by caller
        self._last_result = ReasoningResult(
            context="",  # Will be built by caller
            sub_queries=sub_queries,
            all_sources=sources,
            iterations=len(sub_queries),
            reasoning_trace=reasoning_trace
        )

    async def reason(
        self,
        query: str,
        user: Any,
        collection_id: Optional[UUID],
        retrieval_config: RetrievalConfig,
        call_retrieval_fn: Any,
        build_sources_fn: Any,
    ) -> ReasoningResult:
        """
        Execute deep reasoning (non-streaming).

        Args:
            query: Original user query
            user: User object for retrieval
            collection_id: Collection to search
            retrieval_config: Base retrieval configuration
            call_retrieval_fn: Function to call retrieval endpoint
            build_sources_fn: Function to build source objects

        Returns:
            ReasoningResult with aggregated context and sources
        """
        reasoning_trace = []

        # Step 1: Decompose query
        sub_queries = await self.decompose_query(query)
        reasoning_trace.append({
            "step": 1,
            "action": "decompose",
            "sub_queries": sub_queries
        })

        # Step 2: Iterative retrieval
        all_results = []
        seen_chunk_ids = set()

        for sq in sub_queries:
            config = RetrievalConfig(
                mode=retrieval_config.mode,
                top_k=self.DEFAULT_TOP_K_PER_QUERY,
                rerank=retrieval_config.rerank,
                enable_graph=retrieval_config.enable_graph,
                hierarchical=retrieval_config.hierarchical,
                expand_context=retrieval_config.expand_context,
                metadata_filter=retrieval_config.metadata_filter,
            )

            try:
                result = await call_retrieval_fn(
                    query=sq,
                    user=user,
                    collection_id=collection_id,
                    config=config
                )

                for r in result["results"]:
                    if r.chunk_id not in seen_chunk_ids:
                        seen_chunk_ids.add(r.chunk_id)
                        all_results.append(r)

            except Exception as e:
                logger.warning(f"Retrieval failed for sub-query '{sq}': {e}")

        reasoning_trace.append({
            "step": 2,
            "action": "retrieve",
            "total_unique_chunks": len(all_results)
        })

        # Sort and limit
        all_results.sort(key=lambda x: x.score, reverse=True)
        max_results = retrieval_config.top_k * 2
        all_results = all_results[:max_results]

        # Build sources
        sources = build_sources_fn(all_results)

        reasoning_trace.append({
            "step": 3,
            "action": "synthesize",
            "final_sources": len(sources)
        })

        return ReasoningResult(
            context="",  # Will be built by caller
            sub_queries=sub_queries,
            all_sources=sources,
            iterations=len(sub_queries),
            reasoning_trace=reasoning_trace
        )

    def get_last_result(self) -> Optional[ReasoningResult]:
        """Get the result from the last streaming reasoning call"""
        return getattr(self, '_last_result', None)
