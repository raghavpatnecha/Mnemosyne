"""
Configuration management for Mnemosyne API
Uses pydantic-settings for environment variable validation
"""

from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Database (all from environment - no defaults for credentials)
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "mnemosyne"
    DATABASE_URL: str = ""  # Required: set via environment variable

    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    DEBUG: bool = True

    # Security (all from environment - no defaults for secrets)
    SECRET_KEY: str = ""  # Required: set via environment variable
    API_KEY_PREFIX: str = "mn_"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Application
    APP_NAME: str = "Mnemosyne"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"  # development or production
    DOMAIN: str = "localhost"  # API domain

    # Redis & Celery
    REDIS_PASSWORD: str = ""  # Redis password (leave empty for no auth)
    REDIS_URL: str = "redis://localhost:6379/0"

    # Storage
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 100 * 1024 * 1024  # 100MB
    STORAGE_BACKEND: str = "local"  # "local" or "s3"

    # S3 Storage (if STORAGE_BACKEND="s3")
    S3_BUCKET_NAME: str = "mnemosyne-documents"
    S3_ACCESS_KEY_ID: str = ""  # Optional: uses AWS credentials if empty
    S3_SECRET_ACCESS_KEY: str = ""  # Optional: uses AWS credentials if empty
    S3_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: str = ""  # Optional: for MinIO, DigitalOcean Spaces, etc.
    S3_PRESIGNED_URL_EXPIRY: int = 3600  # Pre-signed URL expiry in seconds (1 hour)

    # OpenAI
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS: int = 1536

    # Processing
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 128

    # Chat (model from environment for consistency)
    CHAT_MODEL: str = "gpt-4o-mini"  # Default model, override via CHAT_MODEL env var
    CHAT_TEMPERATURE: float = 0.7
    CHAT_MAX_TOKENS: int = 1000

    # LLM Provider (LiteLLM format: provider/model)
    LLM_PROVIDER: str = "openai"  # openai, anthropic, groq, ollama, etc.
    LLM_MODEL_STRING: str = ""  # Optional: override full model string (e.g., "openai/gpt-4o-mini")
    LLM_API_BASE: str = ""  # Optional: custom API base URL
    LLM_TIMEOUT: int = 60  # Timeout in seconds for LLM requests

    # Reranking (Week 5)
    RERANK_ENABLED: bool = True
    RERANK_PROVIDER: str = "jina"  # flashrank, cohere, jina, voyage, mixedbread
    RERANK_MODEL: str = "jina-reranker-v2-base-multilingual"  # Provider-specific model name
    RERANK_TOP_K: int = 10
    RERANK_API_KEY: str = ""  # API key for Cohere, Jina, Voyage, Mixedbread (uses JINA_API_KEY if empty)

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

    # Speech-to-Text (STT) Configuration (Phase 2)
    STT_SERVICE: str = "whisper-1"  # LiteLLM format: "whisper-1", "azure/whisper", "groq/whisper-large-v3", etc.
    STT_SERVICE_API_KEY: str = ""  # API key for STT service (uses OPENAI_API_KEY if empty)
    STT_SERVICE_API_BASE: str = ""  # Optional: custom API base URL for STT
    STT_LOCAL_ENABLED: bool = False  # Enable local Faster-Whisper fallback
    STT_LOCAL_MODEL: str = "base"  # Faster-Whisper model: tiny, base, small, medium, large

    # Video Processing (Phase 2)
    VIDEO_FFMPEG_PATH: str = "ffmpeg"  # Path to ffmpeg binary
    VIDEO_FFPROBE_PATH: str = "ffprobe"  # Path to ffprobe binary
    VIDEO_TEMP_DIR: str = "/tmp/mnemosyne_video"  # Temp directory for audio extraction
    VIDEO_MAX_DURATION: int = 3600  # Max video duration in seconds (1 hour)

    # LightRAG (Graph-based RAG)
    LIGHTRAG_ENABLED: bool = True  # Enable/disable LightRAG knowledge graph
    LIGHTRAG_WORKING_DIR: str = "./data/lightrag"  # Storage for graph data
    LIGHTRAG_CHUNK_SIZE: int = 512  # Token size per chunk (align with Chonkie)
    LIGHTRAG_CHUNK_OVERLAP: int = 128  # Overlap between chunks
    LIGHTRAG_TOP_K: int = 20  # Number of entities to retrieve
    LIGHTRAG_CHUNK_TOP_K: int = 10  # Number of chunks in context
    LIGHTRAG_MAX_ENTITY_TOKENS: int = 6000  # Max tokens for entities
    LIGHTRAG_MAX_RELATION_TOKENS: int = 8000  # Max tokens for relationships
    LIGHTRAG_MAX_TOKENS: int = 30000  # Max total tokens in context
    LIGHTRAG_DEFAULT_MODE: str = "hybrid"  # local, global, hybrid, naive
    LIGHTRAG_RERANK_ENABLED: bool = True  # Enable LightRAG internal reranking
    JINA_API_KEY: str = ""  # Jina API key for LightRAG reranking

    # Domain Processors (intelligent document type processing)
    DOMAIN_PROCESSORS_ENABLED: bool = True  # Enable domain-specific document processing
    DOMAIN_DETECTION_USE_LLM: bool = True  # Use LLM for document type detection (uses CHAT_MODEL)

    # LLM-as-Judge (response validation and correction)
    JUDGE_ENABLED: bool = True  # Enable response validation and correction
    JUDGE_MODEL: str = ""  # Empty = use CHAT_MODEL, override via JUDGE_MODEL env var
    JUDGE_TIMEOUT: int = 10  # Max seconds for pre-analysis/validation

    # Figure/Image Description (Vision model for RAG-searchable image content)
    FIGURE_DESCRIPTION_ENABLED: bool = True  # Use Vision model to describe figures/charts in documents
    VISION_MODEL: str = "gpt-4o"  # Vision-capable model, override via VISION_MODEL env var
    FIGURE_MAX_CONCURRENT: int = 5  # Max concurrent Vision API calls
    FIGURE_MIN_SIZE_BYTES: int = 1000  # Skip images smaller than this (likely icons/decorations)

    # Monitoring (from environment only)
    GRAFANA_ADMIN_USER: str = ""
    GRAFANA_ADMIN_PASSWORD: str = ""

    # Backup (Production)
    BACKUP_RETENTION_DAYS: int = 7

    @model_validator(mode='after')
    def detect_docker_environment(self):
        """
        Detect if running inside Docker container and adjust paths/URLs accordingly

        Replacements:
        - Host (Windows/Mac/Linux): Use localhost (connects via exposed ports)
        - Docker container: Use service names (connects via Docker network)
          - localhost:5432 → postgres:5432 (PostgreSQL)
          - localhost:6379 → redis:6379 (Redis)
          - /app/data/lightrag → ./data/lightrag (LightRAG)

        Detection method: Check for /.dockerenv file (created by Docker)
        """
        is_docker = os.path.exists('/.dockerenv')

        if is_docker:
            # Replace localhost with service names for Docker networking
            if 'localhost' in self.DATABASE_URL:
                self.DATABASE_URL = self.DATABASE_URL.replace('localhost', 'postgres')
                print(f"[Docker detected] Database URL adjusted to use service name 'postgres'")

            if 'localhost' in self.REDIS_URL:
                self.REDIS_URL = self.REDIS_URL.replace('localhost', 'redis')
                print(f"[Docker detected] Redis URL adjusted to use service name 'redis'")
        else:
            print(f"[Host detected] Using localhost for all services")

            # Adjust LightRAG path from Docker path to local path
            # Docker uses /app/data/lightrag, but locally we use ./data/lightrag
            if self.LIGHTRAG_WORKING_DIR.startswith('/app/'):
                local_path = self.LIGHTRAG_WORKING_DIR.replace('/app/', './')
                self.LIGHTRAG_WORKING_DIR = local_path
                print(f"[Host detected] LightRAG path adjusted: {local_path}")

        return self

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# Chat preset configurations
# Maps preset name to default settings for that style
CHAT_PRESETS = {
    "concise": {
        "temperature": 0.3,
        "max_tokens": 500,
        "system_prompt_style": "brief",
        "citation_style": "inline",  # [1] inline
    },
    "detailed": {
        "temperature": 0.5,
        "max_tokens": 2000,
        "system_prompt_style": "comprehensive",
        "citation_style": "academic",  # [1], [2] with references
    },
    "research": {
        "temperature": 0.2,
        "max_tokens": 4000,
        "system_prompt_style": "academic",
        "citation_style": "academic_full",  # [1] with full bibliography
    },
    "technical": {
        "temperature": 0.1,
        "max_tokens": 3000,
        "system_prompt_style": "technical",
        "citation_style": "inline",
    },
    "creative": {
        "temperature": 0.8,
        "max_tokens": 2000,
        "system_prompt_style": "exploratory",
        "citation_style": "narrative",
    },
    "qna": {
        "temperature": 0.4,
        "max_tokens": 4000,
        "system_prompt_style": "qna",
        "citation_style": "inline",
    },
}
