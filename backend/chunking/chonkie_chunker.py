"""
Chonkie Chunker - Intelligent semantic chunking
Preserves context boundaries and optimizes for RAG
"""

from typing import List, Dict, Any
from chonkie import SemanticChunker
import tiktoken
from backend.config import settings


class ChonkieChunker:
    """Intelligent chunking using Chonkie"""

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
        embedding_model: str = settings.EMBEDDING_MODEL
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker = SemanticChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_model=embedding_model
        )
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def chunk(self, text: str) -> List[Dict[str, Any]]:
        """
        Chunk text using semantic chunking

        Args:
            text: Input text to chunk

        Returns:
            List of chunks with metadata
        """
        chunks = self.chunker.chunk(text)

        result = []
        for idx, chunk in enumerate(chunks):
            tokens = len(self.tokenizer.encode(chunk.text))
            result.append({
                "content": chunk.text,
                "chunk_index": idx,
                "metadata": {
                    "type": "semantic",
                    "tokens": tokens,
                    "start_char": chunk.start_index,
                    "end_char": chunk.end_index,
                }
            })

        return result
