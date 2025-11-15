"""
Configuration management for Mnemosyne API
Uses pydantic-settings for environment variable validation
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database
    POSTGRES_USER: str = "mnemosyne"
    POSTGRES_PASSWORD: str = "mnemosyne_dev"
    POSTGRES_DB: str = "mnemosyne"
    DATABASE_URL: str = "postgresql://mnemosyne:mnemosyne_dev@localhost:5432/mnemosyne"

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    DEBUG: bool = True

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    API_KEY_PREFIX: str = "mn_test_"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Application
    APP_NAME: str = "Mnemosyne"
    APP_VERSION: str = "0.1.0"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB

    # OpenAI
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS: int = 1536

    # Processing
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 128

    # Chat
    CHAT_MODEL: str = "gpt-4o-mini"
    CHAT_TEMPERATURE: float = 0.7
    CHAT_MAX_TOKENS: int = 1000

    # LLM Provider (LiteLLM format: provider/model)
    LLM_PROVIDER: str = "openai"  # openai, anthropic, groq, ollama, etc.
    LLM_MODEL_STRING: str = ""  # Optional: override full model string (e.g., "openai/gpt-4o-mini")
    LLM_API_BASE: str = ""  # Optional: custom API base URL
    LLM_TIMEOUT: int = 60  # Timeout in seconds for LLM requests

    # Reranking (Week 5)
    RERANK_ENABLED: bool = True
    RERANK_PROVIDER: str = "flashrank"  # flashrank, cohere, jina, voyage, mixedbread
    RERANK_MODEL: str = "ms-marco-MultiBERT-L-12"  # Provider-specific model name
    RERANK_TOP_K: int = 10
    RERANK_API_KEY: str = ""  # API key for Cohere, Jina, Voyage, Mixedbread

    # Caching (Week 5)
    CACHE_ENABLED: bool = True
    CACHE_EMBEDDING_TTL: int = 86400  # 24 hours
    CACHE_SEARCH_TTL: int = 3600  # 1 hour

    # Rate Limiting (Week 5)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_CHAT: str = "10/minute"
    RATE_LIMIT_RETRIEVAL: str = "100/minute"
    RATE_LIMIT_UPLOAD: str = "20/hour"

    # Query Reformulation (Week 5)
    QUERY_REFORMULATION_ENABLED: bool = False  # Premium feature
    QUERY_REFORMULATION_MODE: str = "expand"

    # Retry Logic (Week 5)
    RETRY_ENABLED: bool = True
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_EXPONENTIAL_BASE: int = 2

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
