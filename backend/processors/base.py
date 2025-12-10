"""
Base classes for domain-specific document processors.

This module defines the abstract base class and result model that all
domain processors must implement.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProcessorResult(BaseModel):
    """Result from a domain processor.

    Attributes:
        content: The processed document content (may be modified or original)
        document_metadata: Document-level extracted data (stored in processing_info)
        chunk_annotations: Per-section annotations to enrich chunks
        processor_name: Name of the processor that produced this result
        confidence: Confidence score (0-1) of the processing quality
    """

    model_config = ConfigDict(extra="allow")

    content: str = Field(..., description="Processed document content")
    document_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Document-level extracted metadata"
    )
    chunk_annotations: List[Dict[str, Any]] = Field(
        default_factory=list, description="Per-section annotations for chunking"
    )
    processor_name: str = Field(..., description="Name of the processor")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Processing confidence score"
    )


class DomainProcessor(ABC):
    """Abstract base class for domain-specific document processors.

    Each processor implements domain-specific logic to extract structure
    and metadata from documents of a particular type (legal, academic, etc.).

    Attributes:
        name: Unique identifier for this processor type
        supported_content_types: List of MIME types this processor can handle
    """

    name: str = "base"
    supported_content_types: List[str] = []

    @abstractmethod
    async def process(
        self,
        content: str,
        metadata: Dict[str, Any],
        filename: str,
    ) -> ProcessorResult:
        """Process document content and extract domain-specific structure.

        Args:
            content: The raw document text content from parser
            metadata: User-provided metadata from upload
            filename: Original filename of the document

        Returns:
            ProcessorResult containing processed content and extracted metadata
        """
        pass

    @abstractmethod
    def can_process(self, content: str, metadata: Dict[str, Any]) -> float:
        """Determine if this processor can handle the given document.

        This method is used for heuristic-based processor selection when
        no explicit document_type is provided and LLM detection is disabled.

        Args:
            content: The document text content
            metadata: User-provided metadata

        Returns:
            Confidence score (0-1) that this processor should handle the document.
            Return 0.0 if definitely cannot process, 1.0 if definitely can.
        """
        pass

    def __repr__(self) -> str:
        """String representation of the processor."""
        return f"<{self.__class__.__name__}(name='{self.name}')>"
