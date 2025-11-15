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
from backend.embeddings.openai_embedder import OpenAIEmbedder
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

    Supports three search modes:
    - semantic: Vector similarity search only
    - keyword: Full-text search only
    - hybrid: Both searches merged with RRF

    Args:
        request: Retrieval request (query, mode, top_k, etc.)
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
          "collection_id": "uuid-here"
        }
        ```
    """
    start_time = time.time()

    embedder = OpenAIEmbedder()
    search_service = VectorSearchService(db)

    if request.mode in [RetrievalMode.SEMANTIC, RetrievalMode.HYBRID]:
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
    else:
        raise http_400_bad_request(f"Invalid mode: {request.mode}")

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
