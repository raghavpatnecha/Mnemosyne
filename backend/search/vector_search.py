"""
Vector Search Service
Semantic search using pgvector + hybrid search with RRF

Architecture:
- Semantic: pgvector cosine similarity on embedding column
- Keyword: PostgreSQL FTS on pre-computed search_vector column
- Hybrid: Reciprocal Rank Fusion (RRF) to merge both

The search_vector column is populated at INDEX TIME with normalized
content (slashes/hyphens → spaces). This is the standard RAG practice -
normalize during ingestion, not at query time.

References:
- ParadeDB Hybrid Search: https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual
- RRF Paper: https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from backend.models.chunk import DocumentChunk
from backend.models.document import Document
from uuid import UUID

logger = logging.getLogger(__name__)

# Score thresholds for filtering low-quality results
# These are applied BEFORE RRF fusion to remove noise
SEMANTIC_SCORE_THRESHOLD = 0.35  # Minimum cosine similarity
KEYWORD_SCORE_THRESHOLD = 0.001  # Minimum ts_rank score


class VectorSearchService:
    """
    Vector similarity search using pgvector with hybrid FTS support.

    This service implements the standard RAG retrieval pattern:
    1. Semantic search via pgvector cosine similarity
    2. Keyword search via PostgreSQL tsvector (pre-indexed)
    3. Hybrid search via Reciprocal Rank Fusion (RRF)

    The keyword search uses pre-computed search_vector column that is
    populated at index time with normalized content. This ensures that
    compound terms like "React/Vue" are tokenized as "React Vue" and
    are searchable by individual components.
    """

    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        query_embedding: List[float],
        collection_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        top_k: int = 10,
        metadata_filter: Optional[Dict] = None,
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using cosine similarity.

        Args:
            query_embedding: Query embedding vector (1536 dims)
            collection_id: Filter by collection
            user_id: Filter by user ownership
            top_k: Number of results
            metadata_filter: Metadata filters
            document_type: Filter by document type (legal, academic, qa, table, book, email, manual, presentation, resume, general)

        Returns:
            List of chunks with scores and metadata
        """
        query = self.db.query(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.chunk_index,
            DocumentChunk.metadata_,
            DocumentChunk.chunk_metadata,
            DocumentChunk.document_id,
            DocumentChunk.collection_id,
            Document.title.label('document_title'),
            Document.filename.label('document_filename'),
            DocumentChunk.embedding.cosine_distance(query_embedding).label('distance')
        ).join(
            Document,
            Document.id == DocumentChunk.document_id
        )

        filters = []
        if user_id:
            filters.append(DocumentChunk.user_id == user_id)
        if collection_id:
            filters.append(DocumentChunk.collection_id == collection_id)
        if document_type:
            # Filter by document_type stored in chunk metadata
            filters.append(
                DocumentChunk.metadata_['document_type'].astext == document_type
            )

        if filters:
            query = query.filter(and_(*filters))

        if metadata_filter:
            query = self._apply_metadata_filters(query, metadata_filter)

        results = query.order_by('distance').limit(top_k).all()

        chunks = []
        for result in results:
            score = 1 - result.distance
            if score >= SEMANTIC_SCORE_THRESHOLD:
                chunks.append({
                    'chunk_id': str(result.id),
                    'content': result.content,
                    'chunk_index': result.chunk_index,
                    'score': score,
                    'metadata': result.metadata_ or {},
                    'chunk_metadata': result.chunk_metadata or {},
                    'document': {
                        'id': str(result.document_id),
                        'title': result.document_title,
                        'filename': result.document_filename,
                    },
                    'collection_id': str(result.collection_id)
                })

        filtered_count = len(results) - len(chunks)
        if filtered_count > 0:
            logger.debug(
                f"Semantic search: filtered {filtered_count} results "
                f"below threshold {SEMANTIC_SCORE_THRESHOLD}"
            )

        return chunks

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        collection_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        top_k: int = 10,
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: Semantic + Full-text with RRF fusion.

        This is the recommended approach for production RAG systems.
        RRF (Reciprocal Rank Fusion) combines rankings from both
        search methods without requiring score normalization.

        Args:
            query_text: Query text for full-text search
            query_embedding: Query embedding for semantic search
            collection_id: Filter by collection
            user_id: Filter by user ownership
            top_k: Number of results
            document_type: Filter by document type (legal, academic, qa, table, book, email, manual, presentation, resume, general)

        Returns:
            Merged and ranked results using RRF
        """
        # Get 2x candidates from each method for better fusion
        semantic_results = self.search(
            query_embedding=query_embedding,
            collection_id=collection_id,
            user_id=user_id,
            top_k=top_k * 2,
            document_type=document_type
        )

        keyword_results = self._keyword_search(
            query_text=query_text,
            collection_id=collection_id,
            user_id=user_id,
            top_k=top_k * 2,
            document_type=document_type
        )

        # RRF fusion with k=60 (standard constant)
        merged = self._reciprocal_rank_fusion(
            semantic_results,
            keyword_results,
            k=60
        )

        return merged[:top_k]

    def _keyword_search(
        self,
        query_text: str,
        collection_id: Optional[UUID],
        user_id: Optional[UUID],
        top_k: int,
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Full-text search using tsvector.

        Uses search_vector column if available (pre-computed at index time),
        otherwise falls back to computing tsvector from content at query time.

        The search_vector approach ensures proper tokenization of compound
        terms like "React/Vue" → "React Vue".

        Args:
            query_text: Query text for full-text search
            collection_id: Filter by collection
            user_id: Filter by user ownership
            top_k: Number of results
            document_type: Filter by document type (legal, academic, qa, table, book, email, manual, presentation, resume, general)
        """
        # Use plainto_tsquery for natural language queries
        tsquery = func.plainto_tsquery('english', query_text)

        # Check if search_vector column exists and has data
        # Fall back to content-based tsvector if not
        try:
            # Try using pre-indexed search_vector first
            if hasattr(DocumentChunk, 'search_vector') and DocumentChunk.search_vector is not None:
                tsvector_col = DocumentChunk.search_vector
            else:
                # Fallback: compute tsvector from content at query time
                tsvector_col = func.to_tsvector('english', DocumentChunk.content)
        except Exception:
            tsvector_col = func.to_tsvector('english', DocumentChunk.content)

        query = self.db.query(
            DocumentChunk.id,
            DocumentChunk.content,
            DocumentChunk.chunk_index,
            DocumentChunk.metadata_,
            DocumentChunk.chunk_metadata,
            DocumentChunk.document_id,
            DocumentChunk.collection_id,
            Document.title.label('document_title'),
            Document.filename.label('document_filename'),
            func.ts_rank(tsvector_col, tsquery).label('rank')
        ).join(
            Document,
            Document.id == DocumentChunk.document_id
        ).filter(
            tsvector_col.op('@@')(tsquery)
        )

        if user_id:
            query = query.filter(DocumentChunk.user_id == user_id)
        if collection_id:
            query = query.filter(DocumentChunk.collection_id == collection_id)
        if document_type:
            # Filter by document_type stored in chunk metadata
            query = query.filter(
                DocumentChunk.metadata_['document_type'].astext == document_type
            )

        results = query.order_by(
            func.ts_rank(tsvector_col, tsquery).desc()
        ).limit(top_k).all()

        chunks = []
        for result in results:
            score = float(result.rank) if result.rank else 0.0
            if score >= KEYWORD_SCORE_THRESHOLD:
                chunks.append({
                    'chunk_id': str(result.id),
                    'content': result.content,
                    'chunk_index': result.chunk_index,
                    'score': score,
                    'metadata': result.metadata_ or {},
                    'chunk_metadata': result.chunk_metadata or {},
                    'document': {
                        'id': str(result.document_id),
                        'title': result.document_title,
                        'filename': result.document_filename,
                    },
                    'collection_id': str(result.collection_id)
                })

        logger.debug(f"Keyword search: query='{query_text}' results={len(chunks)}")
        return chunks

    def _reciprocal_rank_fusion(
        self,
        results_a: List[Dict],
        results_b: List[Dict],
        k: int = 60
    ) -> List[Dict]:
        """
        Merge results using Reciprocal Rank Fusion (RRF).

        RRF is the standard method for combining rankings from different
        retrieval systems. It's robust because it uses ranks instead of
        scores, avoiding normalization issues.

        Formula: rrf_score = sum(1 / (k + rank))

        Args:
            results_a: First result list (semantic)
            results_b: Second result list (keyword)
            k: RRF constant (default 60, from original paper)

        Returns:
            Merged results ranked by RRF score
        """
        scores = {}

        for rank, result in enumerate(results_a, 1):
            chunk_id = result['chunk_id']
            if chunk_id not in scores:
                scores[chunk_id] = {
                    'result': result,
                    'rrf_score': 0,
                    'original_score': result['score'],
                    'sources': []
                }
            scores[chunk_id]['rrf_score'] += 1 / (k + rank)
            scores[chunk_id]['sources'].append('semantic')

        for rank, result in enumerate(results_b, 1):
            chunk_id = result['chunk_id']
            if chunk_id not in scores:
                scores[chunk_id] = {
                    'result': result,
                    'rrf_score': 0,
                    'original_score': result['score'],
                    'sources': []
                }
            scores[chunk_id]['rrf_score'] += 1 / (k + rank)
            scores[chunk_id]['sources'].append('keyword')
            # Keep higher original score if found in both
            scores[chunk_id]['original_score'] = max(
                scores[chunk_id]['original_score'],
                result['score']
            )

        merged = sorted(
            scores.values(),
            key=lambda x: x['rrf_score'],
            reverse=True
        )

        logger.debug(
            f"RRF fusion: {len(results_a)} semantic + {len(results_b)} keyword "
            f"→ {len(merged)} merged"
        )

        # Return with original score for interpretability, ranked by RRF
        return [
            {**item['result'], 'score': item['original_score']}
            for item in merged
        ]

    def _apply_metadata_filters(
        self,
        query,
        metadata_filter: Dict
    ):
        """Apply metadata JSON filters."""
        for key, value in metadata_filter.items():
            query = query.filter(
                DocumentChunk.metadata_[key].astext == str(value)
            )
        return query
