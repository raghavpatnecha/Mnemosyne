"""
Retrieval API endpoints
Best-in-class RAG search with hybrid, hierarchical, graph, and reranking
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import logging
import asyncio

from backend.database import get_db
from backend.api.deps import (
    get_current_user,
    get_cache_service,
    get_reranker_service,
    get_query_reformulation_service
)
from backend.models.user import User
from backend.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    ChunkResult,
    DocumentInfo,
    RetrievalMode,
    GraphReference
)
from backend.search.vector_search import VectorSearchService
from backend.search.hierarchical_search import HierarchicalSearchService
from backend.search.context_expander import ContextExpander
from backend.embeddings.openai_embedder import OpenAIEmbedder
from backend.services.lightrag_service import get_lightrag_manager
from backend.config import settings
from backend.core.exceptions import http_400_bad_request
from backend.utils.metadata_validator import validate_metadata_filter
from backend.schemas.retrieval import ContextWindow
from backend.processors import VALID_DOCUMENT_TYPES

router = APIRouter(prefix="/retrievals", tags=["retrievals"])
logger = logging.getLogger(__name__)


def _build_chunk_results(results: list) -> list[ChunkResult]:
    """
    Build ChunkResult objects from search results

    Centralized function to avoid code duplication

    Args:
        results: List of search result dicts

    Returns:
        List of ChunkResult objects
    """
    chunk_results = []
    for r in results:
        # Build context window if present
        context_window = None
        if r.get('context_window'):
            context_window = ContextWindow(**r['context_window'])

        chunk_results.append(
            ChunkResult(
                chunk_id=r['chunk_id'],
                content=r['content'],
                chunk_index=r['chunk_index'],
                score=r['score'],
                rerank_score=r.get('rerank_score'),
                metadata=r['metadata'],
                chunk_metadata=r['chunk_metadata'],
                document=DocumentInfo(**r['document']),
                collection_id=r['collection_id'],
                expanded_content=r.get('expanded_content'),
                context_window=context_window
            )
        )
    return chunk_results


def _build_graph_references(raw_references: list) -> list[GraphReference]:
    """Convert raw LightRAG references to GraphReference objects"""
    graph_refs = []
    for ref in raw_references:
        if isinstance(ref, dict):
            graph_refs.append(GraphReference(
                reference_id=ref.get('reference_id') or ref.get('id'),
                file_path=ref.get('file_path') or ref.get('path'),
                content=ref.get('content') or ref.get('text')
            ))
        elif isinstance(ref, str):
            # Simple string reference
            graph_refs.append(GraphReference(content=ref))
    return graph_refs


def _enrich_with_graph_context(
    base_results: list,
    graph_result: dict
) -> tuple[list, str, list]:
    """
    Enrich base search results with knowledge graph context

    This implements HybridRAG by combining:
    - Base retrieval (semantic/keyword/hybrid/hierarchical)
    - Graph context (relationships, entities, multi-hop reasoning)

    Args:
        base_results: Results from base search (vector/keyword/hybrid/hierarchical)
        graph_result: Result from LightRAG query (answer + references)

    Returns:
        Tuple of (enriched_results, graph_context_string, graph_references)
    """
    # Extract graph context narrative and references
    graph_context = graph_result.get('answer', '')
    raw_references = graph_result.get('references', [])
    graph_references = _build_graph_references(raw_references)

    # For now, we don't merge graph references into chunk results
    # because they have different formats. We return them separately.
    # The chat service will handle combining and deduplicating sources.

    logger.info(
        f"Graph enrichment: {len(base_results)} base results, "
        f"{len(graph_references)} graph references"
    )

    return base_results, graph_context, graph_references


@router.post("", response_model=RetrievalResponse, status_code=status.HTTP_200_OK)
async def retrieve(
    request: RetrievalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    cache: "CacheService" = Depends(get_cache_service),
    reranker: "RerankerService" = Depends(get_reranker_service),
    query_reformulator: "QueryReformulationService" = Depends(get_query_reformulation_service)
):
    """
    Best-in-class RAG retrieval endpoint

    Default configuration delivers optimal results:
    - mode=hybrid: Semantic + Keyword with RRF fusion
    - hierarchical=true: Two-tier search (document → chunk filtering)
    - enable_graph=true: LightRAG knowledge graph enhancement
    - rerank=true: Cross-encoder reranking for precision

    Search modes:
    - semantic: Vector similarity search only
    - keyword: Full-text search (BM25) only
    - hybrid: Both merged with RRF (default, recommended)
    - graph: Pure LightRAG graph-based retrieval

    Flags:
    - hierarchical: Filter documents first, then search chunks within (20-30% better precision)
    - enable_graph: Add knowledge graph context (35-80% better for complex queries)
    - rerank: Cross-encoder reranking (15-25% accuracy boost)

    Example (minimal - uses optimal defaults):
        ```json
        {
          "query": "What is machine learning?",
          "collection_id": "uuid-here"
        }
        ```

    Example (explicit):
        ```json
        {
          "query": "What is machine learning?",
          "collection_id": "uuid-here",
          "mode": "hybrid",
          "hierarchical": true,
          "enable_graph": true,
          "rerank": true,
          "top_k": 5
        }
        ```

    Flow:
    1. Check cache (instant return if hit)
    2. Reformulate query (expand with synonyms)
    3. Generate embedding
    4. If hierarchical: Find top documents first, then search within them
    5. Execute search with chosen mode (semantic/keyword/hybrid)
    6. Enhance with graph context (parallel LightRAG query)
    7. Rerank results with cross-encoder
    8. Cache and return
    """
    # DEBUG: Log request at retrieve() entry point
    logger.info(f"[DEBUG] retrieve() called with collection_id={request.collection_id}, enable_graph={request.enable_graph}")

    # Validate metadata filter (Issue #1 fix)
    validated_metadata_filter = validate_metadata_filter(request.metadata_filter)

    # Validate document_type filter
    if request.document_type and request.document_type not in VALID_DOCUMENT_TYPES:
        raise http_400_bad_request(
            f"Invalid document_type '{request.document_type}'. "
            f"Valid types: {', '.join(sorted(VALID_DOCUMENT_TYPES))}"
        )

    # Services are now injected via dependency injection (singletons)
    embedder = OpenAIEmbedder()
    search_service = VectorSearchService(db)
    hierarchical_service = HierarchicalSearchService(db)

    # Check cache first (before any processing)
    cache_params = {
        "mode": request.mode.value,
        "top_k": request.top_k,
        "collection_id": str(request.collection_id) if request.collection_id else None,
        "document_type": request.document_type,
        "rerank": request.rerank,
        "enable_graph": request.enable_graph,
        "hierarchical": request.hierarchical,
        "expand_context": request.expand_context,
        "metadata_filter": validated_metadata_filter,
        "user_id": str(current_user.id)
    }

    cached_results = cache.get_search_results(request.query, cache_params)
    if cached_results:
        # Cache hit - return immediately
        try:
            # Handle both old cache format (list) and new format (dict with results + context)
            if isinstance(cached_results, dict):
                chunk_results = _build_chunk_results(cached_results['results'])
                graph_context = cached_results.get('graph_context')
                # Convert cached references back to GraphReference objects
                raw_refs = cached_results.get('graph_references', [])
                if raw_refs and isinstance(raw_refs[0], dict):
                    graph_references = _build_graph_references(raw_refs)
                else:
                    graph_references = raw_refs  # Already GraphReference objects
                graph_enhanced = cached_results.get('graph_enhanced', False)
            else:
                chunk_results = _build_chunk_results(cached_results)
                graph_context = None
                graph_references = []
                graph_enhanced = False

            logger.info(f"Cache hit for query: {request.query[:50]}...")
            return RetrievalResponse(
                results=chunk_results,
                query=request.query,
                mode=request.mode.value,
                total_results=len(chunk_results),
                graph_enhanced=graph_enhanced,
                graph_context=graph_context,
                graph_references=graph_references
            )
        except (KeyError, TypeError, ValueError) as e:
            # Corrupted cache data - log warning and fall through to normal search
            logger.warning(
                f"Corrupted cache data for query '{request.query[:50]}...': {e}. "
                "Falling back to normal search."
            )

    # Cache miss - proceed with search
    # Apply query reformulation if enabled
    query_text = request.query
    if query_reformulator.is_available():
        query_text = await query_reformulator.reformulate(
            request.query,
            mode="expand"  # Expand with synonyms and related terms
        )

    # Initialize graph enhancement variables
    graph_context = None
    graph_references = []
    graph_enhanced = False

    # Validate graph enhancement request (fail-fast)
    if request.enable_graph and request.mode != RetrievalMode.GRAPH:
        # HybridRAG: Run base search + graph query in parallel
        if not settings.LIGHTRAG_ENABLED:
            raise http_400_bad_request(
                "Graph enhancement requested but LightRAG is not enabled. "
                "Set LIGHTRAG_ENABLED=true in configuration."
            )
        logger.info(f"Running HybridRAG: {request.mode.value} + graph (parallel)")

    # Generate embedding if needed (for semantic/hybrid modes or hierarchical flag)
    needs_embedding = request.mode in [RetrievalMode.SEMANTIC, RetrievalMode.HYBRID] or request.hierarchical
    if needs_embedding:
        query_embedding = await embedder.embed(query_text)
    else:
        query_embedding = None

    # Define async functions for parallel execution
    async def run_base_search():
        """Execute base search based on mode and hierarchical flag"""
        # If hierarchical is enabled, use HierarchicalSearchService with the chosen mode
        if request.hierarchical and request.mode != RetrievalMode.GRAPH:
            mode_map = {
                RetrievalMode.SEMANTIC: "semantic",
                RetrievalMode.KEYWORD: "keyword",
                RetrievalMode.HYBRID: "hybrid"
            }
            tier2_mode = mode_map.get(request.mode, "hybrid")

            logger.info(f"Running hierarchical search with tier2_mode={tier2_mode}")
            return await hierarchical_service.search(
                query_embedding=query_embedding,
                user_id=current_user.id,
                collection_id=request.collection_id,
                top_k=request.top_k,
                mode=tier2_mode,
                query_text=query_text if tier2_mode in ["keyword", "hybrid"] else None,
                document_type=request.document_type
            )

        # Non-hierarchical search
        if request.mode == RetrievalMode.SEMANTIC:
            return search_service.search(
                query_embedding=query_embedding,
                collection_id=request.collection_id,
                user_id=current_user.id,
                top_k=request.top_k,
                metadata_filter=validated_metadata_filter,
                document_type=request.document_type
            )
        elif request.mode == RetrievalMode.HYBRID:
            return search_service.hybrid_search(
                query_text=query_text,
                query_embedding=query_embedding,
                collection_id=request.collection_id,
                user_id=current_user.id,
                top_k=request.top_k,
                document_type=request.document_type
            )
        elif request.mode == RetrievalMode.KEYWORD:
            return search_service._keyword_search(
                query_text=query_text,
                collection_id=request.collection_id,
                user_id=current_user.id,
                top_k=request.top_k,
                document_type=request.document_type
            )
        else:
            raise http_400_bad_request(f"Invalid mode: {request.mode}")

    async def run_graph_query():
        """Execute LightRAG graph query"""
        if not settings.LIGHTRAG_ENABLED:
            return None

        # DEBUG: Log collection_id before calling LightRAG
        logger.info(f"[DEBUG] run_graph_query - request.collection_id={request.collection_id}")

        lightrag_manager = get_lightrag_manager()

        # LightRAG returns dict with 'answer' (context) and 'references' (sources)
        result = await lightrag_manager.query(
            user_id=current_user.id,
            collection_id=request.collection_id,
            query=query_text,
            mode=settings.LIGHTRAG_DEFAULT_MODE
        )

        return {
            "answer": result.get("answer", ""),
            "references": result.get("references", [])
        }

    # Execute search based on mode and graph enhancement
    if request.mode == RetrievalMode.GRAPH:
        # Pure graph mode - no base search needed
        if not settings.LIGHTRAG_ENABLED:
            raise http_400_bad_request("LightRAG is not enabled")

        graph_result = await run_graph_query()
        if not graph_result:
            raise http_400_bad_request("Graph mode failed - LightRAG returned no results")

        results = []  # No chunk results in pure graph mode
        graph_context = graph_result.get('answer', '')
        graph_references = _build_graph_references(graph_result.get('references', []))
        graph_enhanced = True

    elif request.enable_graph:
        # HybridRAG: Run base search + graph query in parallel
        base_results, graph_result = await asyncio.gather(
            run_base_search(),
            run_graph_query()
        )

        if not graph_result:
            raise http_400_bad_request(
                "Graph enhancement failed - LightRAG returned no results. "
                "Check LightRAG configuration and ensure documents are indexed."
            )

        results, graph_context, graph_references = _enrich_with_graph_context(base_results, graph_result)
        graph_enhanced = True

    else:
        # Base search only (no graph enhancement)
        results = await run_base_search()

    # Enforce top_k limit (graph enrichment might have added extra chunks)
    if len(results) > request.top_k:
        original_count = len(results)
        results = results[:request.top_k]
        logger.debug(f"Trimmed results from {original_count} to top_k={request.top_k}")

    # Apply context expansion FIRST (before reranking)
    # This ensures the reranker validates the FINAL content going to the LLM
    # Research: "Retrieval is efficient with small chunks, LLM benefits from larger context"
    # Source: https://glaforge.dev/posts/2025/02/25/advanced-rag-sentence-window-retrieval/
    if request.expand_context and results:
        context_expander = ContextExpander(db)
        results = context_expander.expand_context(
            results=results,
            window_before=1,  # 1 chunk before
            window_after=2,   # 2 chunks after
            merge_overlapping=True
        )

    # Apply reranking AFTER context expansion
    # This validates the expanded_content against the query, preventing context rot
    # where irrelevant surrounding chunks pollute the context
    # Research: Cross-encoder reranking adds +10-20% precision
    # Source: https://superlinked.com/vectorhub/articles/optimizing-rag-with-hybrid-search-reranking
    RERANK_SCORE_THRESHOLD = 0.3  # Minimum rerank score (cross-encoder confidence)
    if request.rerank and reranker.is_available() and results:
        results = reranker.rerank_with_threshold(
            query=request.query,  # Use original query for reranking
            chunks=results,
            threshold=RERANK_SCORE_THRESHOLD,
            top_k=request.top_k,
            use_expanded_content=True  # Rerank on expanded_content, not original
        )

    # Cache results (using original query as key)
    if results or graph_references:
        # Create cache payload with graph context if present
        cache_payload = {
            'results': results,
            'graph_enhanced': graph_enhanced,
            'graph_context': graph_context,
            'graph_references': graph_references
        }

        success = cache.set_search_results(
            query=request.query,  # Cache with original query
            params=cache_params,
            results=cache_payload
        )
        if not success:
            logger.warning(
                f"Failed to cache search results for query: {request.query[:50]}..."
            )

    chunk_results = _build_chunk_results(results)

    return RetrievalResponse(
        results=chunk_results,
        query=request.query,
        mode=request.mode.value,
        total_results=len(chunk_results),
        graph_enhanced=graph_enhanced,
        graph_context=graph_context,
        graph_references=graph_references
    )
