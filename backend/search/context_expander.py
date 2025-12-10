"""
Context Window Expansion Service
Implements "Sentence Window Retrieval" pattern for richer RAG context

When a chunk is retrieved, this service fetches surrounding chunks from the
same document to provide more complete context to the LLM.

Research (2025):
- "Retrieval processes are more efficient with smaller chunks, while LLM
   generation benefits from larger, contextually rich chunks"
- Source: https://glaforge.dev/posts/2025/02/25/advanced-rag-sentence-window-retrieval/
"""

import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict
from sqlalchemy.orm import Session
from sqlalchemy import and_
from uuid import UUID

from backend.models.chunk import DocumentChunk
from backend.models.document import Document

logger = logging.getLogger(__name__)

# Context window configuration
CONTEXT_WINDOW_BEFORE = 1  # Number of chunks before the matched chunk
CONTEXT_WINDOW_AFTER = 2   # Number of chunks after the matched chunk
MIN_CONTENT_LENGTH = 100   # Minimum content length to avoid expanding tiny header chunks


class ContextExpander:
    """
    Expands retrieved chunks with surrounding context from the same document

    Pattern: Small-to-Big Retrieval
    - Index and retrieve small chunks (better precision)
    - Expand with surrounding chunks (richer context for LLM)
    """

    def __init__(self, db: Session):
        self.db = db

    def expand_context(
        self,
        results: List[Dict[str, Any]],
        window_before: int = CONTEXT_WINDOW_BEFORE,
        window_after: int = CONTEXT_WINDOW_AFTER,
        merge_overlapping: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Expand search results with surrounding chunks

        Args:
            results: Search results with chunk_id, document.id, chunk_index
            window_before: Number of chunks to fetch before each result
            window_after: Number of chunks to fetch after each result
            merge_overlapping: Merge chunks that overlap into continuous context

        Returns:
            Results with expanded 'content' and 'expanded_context' metadata
        """
        if not results:
            return results

        # Group results by document to minimize DB queries
        doc_chunks = defaultdict(list)
        for result in results:
            doc_id = result['document']['id']
            chunk_index = result['chunk_index']
            doc_chunks[doc_id].append({
                'result': result,
                'chunk_index': chunk_index
            })

        # Fetch surrounding chunks for each document
        expanded_results = []
        for doc_id, chunks in doc_chunks.items():
            # Calculate all indices we need to fetch
            indices_needed = set()
            for chunk_info in chunks:
                idx = chunk_info['chunk_index']
                for i in range(max(0, idx - window_before), idx + window_after + 1):
                    indices_needed.add(i)

            # Fetch all needed chunks in one query
            surrounding_chunks = self._fetch_chunks_by_indices(
                document_id=doc_id,
                indices=list(indices_needed)
            )

            # Build expanded context for each result
            for chunk_info in chunks:
                result = chunk_info['result'].copy()
                idx = chunk_info['chunk_index']

                # Get surrounding chunks
                start_idx = max(0, idx - window_before)
                end_idx = idx + window_after

                # Build expanded content
                context_chunks = []
                for i in range(start_idx, end_idx + 1):
                    if i in surrounding_chunks:
                        context_chunks.append({
                            'index': i,
                            'content': surrounding_chunks[i]['content'],
                            'is_match': i == idx
                        })

                # Merge content if we have context
                if len(context_chunks) > 1:
                    expanded_content = self._merge_chunks(context_chunks)
                    result['expanded_content'] = expanded_content
                    result['context_window'] = {
                        'original_index': idx,
                        'start_index': start_idx,
                        'end_index': min(end_idx, max(c['index'] for c in context_chunks)),
                        'chunks_merged': len(context_chunks)
                    }
                else:
                    result['expanded_content'] = result['content']
                    result['context_window'] = None

                expanded_results.append(result)

        # Sort by original score
        expanded_results.sort(key=lambda x: x.get('score', 0), reverse=True)

        # Deduplicate if merge_overlapping is True
        if merge_overlapping:
            expanded_results = self._deduplicate_overlapping(expanded_results)

        logger.info(
            f"Context expansion: {len(results)} results → {len(expanded_results)} "
            f"(window: -{window_before}/+{window_after})"
        )

        return expanded_results

    def _fetch_chunks_by_indices(
        self,
        document_id: str,
        indices: List[int]
    ) -> Dict[int, Dict[str, Any]]:
        """Fetch multiple chunks by their indices from a document"""
        chunks = self.db.query(
            DocumentChunk.chunk_index,
            DocumentChunk.content
        ).filter(
            DocumentChunk.document_id == document_id,
            DocumentChunk.chunk_index.in_(indices)
        ).all()

        return {
            chunk.chunk_index: {'content': chunk.content}
            for chunk in chunks
        }

    def _merge_chunks(self, context_chunks: List[Dict]) -> str:
        """Merge multiple chunks into continuous text"""
        # Sort by index
        sorted_chunks = sorted(context_chunks, key=lambda x: x['index'])

        # Merge with separator for readability
        merged_parts = []
        for chunk in sorted_chunks:
            content = chunk['content'].strip()
            if content:
                merged_parts.append(content)

        return "\n\n".join(merged_parts)

    def _deduplicate_overlapping(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove results that would create duplicate context

        If two results from the same document have overlapping context windows,
        keep only the higher-scoring one.
        """
        seen_ranges = {}  # doc_id -> list of (start, end) ranges
        deduplicated = []

        for result in results:
            doc_id = result['document']['id']
            context = result.get('context_window')

            if context is None:
                # No context expansion, always keep
                deduplicated.append(result)
                continue

            start = context['start_index']
            end = context['end_index']

            # Check for overlap with existing ranges for this document
            if doc_id not in seen_ranges:
                seen_ranges[doc_id] = []

            has_overlap = False
            for existing_start, existing_end in seen_ranges[doc_id]:
                # Check if ranges overlap
                if start <= existing_end and end >= existing_start:
                    has_overlap = True
                    break

            if not has_overlap:
                seen_ranges[doc_id].append((start, end))
                deduplicated.append(result)

        if len(deduplicated) < len(results):
            logger.debug(
                f"Deduplicated {len(results) - len(deduplicated)} "
                f"overlapping context windows"
            )

        return deduplicated
