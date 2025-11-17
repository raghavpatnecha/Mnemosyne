"""
Configuration for Mnemosyne SDK Integration
"""
import os
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration class for Mnemosyne SDK and application settings"""

    class SDK:
        """Mnemosyne SDK Configuration"""
        API_KEY: str = os.getenv("MNEMOSYNE_API_KEY", "")
        BASE_URL: str = os.getenv("MNEMOSYNE_BASE_URL", "http://localhost:8000/api/v1")
        TIMEOUT: int = int(os.getenv("MNEMOSYNE_TIMEOUT", "60"))
        MAX_RETRIES: int = int(os.getenv("MNEMOSYNE_MAX_RETRIES", "3"))

    class SEARCH:
        """Search Configuration"""
        DEFAULT_MODE: str = "hybrid"  # semantic, keyword, hybrid, hierarchical, graph
        ENABLE_GRAPH: bool = True  # Enable graph enhancement by default
        TOP_K: int = 10  # Number of results to retrieve
        RERANK: bool = False  # Enable reranking

    class CHAT:
        """Chat Configuration"""
        STREAM: bool = True  # Enable streaming by default
        TOP_K: int = 5  # Number of chunks to retrieve for chat context
