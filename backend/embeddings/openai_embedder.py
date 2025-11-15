"""
OpenAI Embedder
Generate embeddings using OpenAI text-embedding-3-large with Redis caching
"""

from typing import List
from openai import AsyncOpenAI
from backend.config import settings
from backend.services.cache_service import CacheService
import logging

logger = logging.getLogger(__name__)


class OpenAIEmbedder:
    """Generate embeddings using OpenAI API with caching"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.EMBEDDING_MODEL
        self.dimensions = settings.EMBEDDING_DIMENSIONS
        self.cache = CacheService()

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for batch of texts

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors
        """
        batch_size = 100
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            response = await self.client.embeddings.create(
                model=self.model,
                input=batch,
                dimensions=self.dimensions
            )

            embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def embed(self, text: str) -> List[float]:
        """
        Generate embedding for single text with caching

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        # Check cache first
        cached = self.cache.get_embedding(text)
        if cached:
            logger.debug("Embedding cache hit")
            return cached

        # Generate embedding via API
        logger.debug("Embedding cache miss - calling OpenAI API")
        embeddings = await self.embed_batch([text])
        embedding = embeddings[0]

        # Cache result
        self.cache.set_embedding(text, embedding)

        return embedding
