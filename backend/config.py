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

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
