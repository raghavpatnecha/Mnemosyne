"""
Retrieval API endpoints
Semantic search, hybrid search, and ranking
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
import time

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models.user import User
from backend.schemas.retrieval import (
    RetrievalRequest,
    RetrievalResponse,
    ChunkResult,
    DocumentInfo,
    RetrievalMode
)
from backend.search.vector_search import VectorSearchService
from backend.search.hierarchical_search import HierarchicalSearchService
from backend.embeddings.openai_embedder import OpenAIEmbedder
from backend.services.lightrag_service import get_lightrag_service
from backend.services.reranker_service import RerankerService
from backend.config import settings
from backend.core.exceptions import http_400_bad_request

router = APIRouter(prefix="/retrievals", tags=["retrievals"])


@router.post("", response_model=RetrievalResponse, status_code=status.HTTP_200_OK)
async def retrieve(
    request: RetrievalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve relevant chunks for a query

    Supports five search modes:
    - semantic: Vector similarity search only
    - keyword: Full-text search only
    - hybrid: Both searches merged with RRF
    - hierarchical: Two-tier search (document → chunk)
    - graph: LightRAG graph-based retrieval (entity + relationship)

    Optional reranking improves results by 15-25% using:
    - Flashrank (local, fast, free)
    - Cohere, Jina, Voyage, Mixedbread (API-based)

    Args:
        request: Retrieval request (query, mode, top_k, rerank, etc.)
        db: Database session
        current_user: Authenticated user

    Returns:
        RetrievalResponse: Ranked chunks with scores and metadata

    Example:
        ```json
        {
          "query": "What is machine learning?",
          "mode": "hybrid",
          "top_k": 10,
          "rerank": true,
          "collection_id": "uuid-here"
        }
        ```
    """
    start_time = time.time()

    embedder = OpenAIEmbedder()
    search_service = VectorSearchService(db)
    hierarchical_service = HierarchicalSearchService(db)
    reranker = RerankerService()

    if request.mode in [RetrievalMode.SEMANTIC, RetrievalMode.HYBRID, RetrievalMode.HIERARCHICAL]:
        query_embedding = await embedder.embed(request.query)
    else:
        query_embedding = None

    if request.mode == RetrievalMode.SEMANTIC:
        results = search_service.search(
            query_embedding=query_embedding,
            collection_id=request.collection_id,
            user_id=current_user.id,
            top_k=request.top_k,
            metadata_filter=request.metadata_filter
        )
    elif request.mode == RetrievalMode.HYBRID:
        results = search_service.hybrid_search(
            query_text=request.query,
            query_embedding=query_embedding,
            collection_id=request.collection_id,
            user_id=current_user.id,
            top_k=request.top_k
        )
    elif request.mode == RetrievalMode.KEYWORD:
        results = search_service._keyword_search(
            query_text=request.query,
            collection_id=request.collection_id,
            user_id=current_user.id,
            top_k=request.top_k
        )
    elif request.mode == RetrievalMode.HIERARCHICAL:
        results = await hierarchical_service.search(
            query_embedding=query_embedding,
            user_id=current_user.id,
            collection_id=request.collection_id,
            top_k=request.top_k
        )
    elif request.mode == RetrievalMode.GRAPH:
        # LightRAG graph-based retrieval with source extraction
        if not settings.LIGHTRAG_ENABLED:
            raise http_400_bad_request("LightRAG is not enabled")

        lightrag = get_lightrag_service()
        graph_result = await lightrag.query(
            query_text=request.query,
            mode=settings.LIGHTRAG_DEFAULT_MODE,  # hybrid, local, or global
            top_k=request.top_k,
            db_session=db,
            user_id=current_user.id,
            collection_id=request.collection_id
        )

        # Use real source chunks from database for consistent response format
        # This provides actual chunk IDs and document references
        results = graph_result.get('chunks', [])
    else:
        raise http_400_bad_request(f"Invalid mode: {request.mode}")

    # Apply reranking if requested and available
    if request.rerank and reranker.is_available() and results:
        results = reranker.rerank(
            query=request.query,
            chunks=results,
            top_k=request.top_k
        )

    chunk_results = [
        ChunkResult(
            chunk_id=r['chunk_id'],
            content=r['content'],
            chunk_index=r['chunk_index'],
            score=r['score'],
            metadata=r['metadata'],
            chunk_metadata=r['chunk_metadata'],
            document=DocumentInfo(**r['document']),
            collection_id=r['collection_id']
        )
        for r in results
    ]

    return RetrievalResponse(
        results=chunk_results,
        query=request.query,
        mode=request.mode.value,
        total_results=len(chunk_results)
    )
