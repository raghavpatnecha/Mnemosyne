"""
Vector Search Service
Semantic search using pgvector + hybrid search with RRF
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from backend.models.chunk import DocumentChunk
from backend.models.document import Document
from uuid import UUID


class VectorSearchService:
    """Vector similarity search using pgvector"""

    def __init__(self, db: Session):
        self.db = db

    def search(
        self,
        query_embedding: List[float],
        collection_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        top_k: int = 10,
        metadata_filter: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search using cosine similarity

        Args:
            query_embedding: Query embedding vector (1536 dims)
            collection_id: Filter by collection
            user_id: Filter by user ownership
            top_k: Number of results
            metadata_filter: Metadata filters

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

        if filters:
            query = query.filter(and_(*filters))

        if metadata_filter:
            query = self._apply_metadata_filters(query, metadata_filter)

        results = query.order_by('distance').limit(top_k).all()

        return [
            {
                'chunk_id': str(result.id),
                'content': result.content,
                'chunk_index': result.chunk_index,
                'score': 1 - result.distance,
                'metadata': result.metadata_ or {},
                'chunk_metadata': result.chunk_metadata or {},
                'document': {
                    'id': str(result.document_id),
                    'title': result.document_title,
                    'filename': result.document_filename,
                },
                'collection_id': str(result.collection_id)
            }
            for result in results
        ]

    def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        collection_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: Semantic + Full-text with RRF

        Args:
            query_text: Query text for full-text search
            query_embedding: Query embedding for semantic search
            collection_id: Filter by collection
            user_id: Filter by user ownership
            top_k: Number of results

        Returns:
            Merged and ranked results using RRF
        """
        semantic_results = self.search(
            query_embedding=query_embedding,
            collection_id=collection_id,
            user_id=user_id,
            top_k=top_k * 2
        )

        keyword_results = self._keyword_search(
            query_text=query_text,
            collection_id=collection_id,
            user_id=user_id,
            top_k=top_k * 2
        )

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
        top_k: int
    ) -> List[Dict[str, Any]]:
        """Full-text search using PostgreSQL ts_vector"""
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
            func.ts_rank(
                func.to_tsvector('english', DocumentChunk.content),
                func.plainto_tsquery('english', query_text)
            ).label('rank')
        ).join(
            Document,
            Document.id == DocumentChunk.document_id
        ).filter(
            func.to_tsvector('english', DocumentChunk.content).match(
                func.plainto_tsquery('english', query_text)
            )
        )

        if user_id:
            query = query.filter(DocumentChunk.user_id == user_id)
        if collection_id:
            query = query.filter(DocumentChunk.collection_id == collection_id)

        results = query.order_by(
            func.ts_rank(
                func.to_tsvector('english', DocumentChunk.content),
                func.plainto_tsquery('english', query_text)
            ).desc()
        ).limit(top_k).all()

        return [
            {
                'chunk_id': str(result.id),
                'content': result.content,
                'chunk_index': result.chunk_index,
                'score': float(result.rank),
                'metadata': result.metadata_ or {},
                'chunk_metadata': result.chunk_metadata or {},
                'document': {
                    'id': str(result.document_id),
                    'title': result.document_title,
                    'filename': result.document_filename,
                },
                'collection_id': str(result.collection_id)
            }
            for result in results
        ]

    def _reciprocal_rank_fusion(
        self,
        results_a: List[Dict],
        results_b: List[Dict],
        k: int = 60
    ) -> List[Dict]:
        """
        Merge results using Reciprocal Rank Fusion

        RRF formula: score = sum(1 / (k + rank))

        Args:
            results_a: First result list
            results_b: Second result list
            k: RRF constant (default 60)

        Returns:
            Merged and ranked results
        """
        scores = {}

        for rank, result in enumerate(results_a, 1):
            chunk_id = result['chunk_id']
            scores[chunk_id] = scores.get(chunk_id, {'result': result, 'score': 0})
            scores[chunk_id]['score'] += 1 / (k + rank)

        for rank, result in enumerate(results_b, 1):
            chunk_id = result['chunk_id']
            scores[chunk_id] = scores.get(chunk_id, {'result': result, 'score': 0})
            scores[chunk_id]['score'] += 1 / (k + rank)

        merged = sorted(
            scores.values(),
            key=lambda x: x['score'],
            reverse=True
        )

        return [
            {**item['result'], 'score': item['score']}
            for item in merged
        ]

    def _apply_metadata_filters(
        self,
        query,
        metadata_filter: Dict
    ):
        """Apply metadata JSON filters"""
        for key, value in metadata_filter.items():
            query = query.filter(
                DocumentChunk.metadata_[key].astext == str(value)
            )
        return query
