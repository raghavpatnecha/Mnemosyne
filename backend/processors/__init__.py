"""
Domain Processor Framework for Mnemosyne.

This module provides intelligent document processing with domain-specific
extraction for legal documents, academic papers, Q&A content, and tables.

Usage:
    from backend.processors import ProcessorFactory

    # Auto-detect and get appropriate processor
    processor = await ProcessorFactory.detect_and_get_processor(
        content=document_content,
        metadata=user_metadata,
        use_llm=True
    )

    if processor:
        result = await processor.process(content, metadata, filename)
        # result.document_metadata contains extracted structure
"""

import logging
from typing import Dict, Optional, Type

from backend.processors.base import DomainProcessor, ProcessorResult

logger = logging.getLogger(__name__)

# Valid document types for validation
VALID_DOCUMENT_TYPES = {
    "legal", "academic", "qa", "table", "general",
    "book", "email", "manual", "presentation", "resume"  # New types from RAGFlow
}


class ProcessorFactory:
    """Factory for creating and selecting domain processors.

    Uses a registry pattern to manage available processors and provides
    methods for both explicit and auto-detected processor selection.
    """

    _processors: Dict[str, Type[DomainProcessor]] = {}

    @classmethod
    def register(cls, name: str, processor_class: Type[DomainProcessor]) -> None:
        """Register a processor class with the factory.

        Args:
            name: Unique identifier for this processor type
            processor_class: The processor class to register
        """
        cls._processors[name] = processor_class
        logger.debug("Registered domain processor: %s", name)

    @classmethod
    def get_processor(cls, document_type: str) -> Optional[DomainProcessor]:
        """Get a processor instance by document type.

        Args:
            document_type: The type of document (legal, academic, qa, table, book, email, manual, presentation, resume)

        Returns:
            Processor instance or None if type not found
        """
        if document_type in cls._processors:
            return cls._processors[document_type]()
        return None

    @classmethod
    def get_available_processors(cls) -> Dict[str, Type[DomainProcessor]]:
        """Get all registered processors.

        Returns:
            Dictionary mapping processor names to classes
        """
        return cls._processors.copy()

    @classmethod
    async def detect_and_get_processor(
        cls,
        content: str,
        metadata: Optional[Dict] = None,
        use_llm: bool = True,
    ) -> Optional[DomainProcessor]:
        """Detect document type and return appropriate processor.

        Detection priority:
        1. User-specified document_type in metadata (highest priority)
        2. LLM-based classification (if enabled)

        If neither method identifies a specific type, returns None
        and the document uses the default processing pipeline.

        Args:
            content: Document text content
            metadata: User-provided metadata (may contain document_type)
            use_llm: Whether to use LLM for type detection

        Returns:
            Appropriate processor instance or None for general documents
        """
        metadata = metadata or {}

        # 1. Check user-specified type in metadata (highest priority)
        if "document_type" in metadata:
            user_type = metadata["document_type"]
            if user_type == "general":
                logger.debug("User specified 'general' type, skipping domain processing")
                return None
            processor = cls.get_processor(user_type)
            if processor:
                logger.info("Using user-specified processor: %s", user_type)
                return processor
            logger.warning("Unknown document_type '%s', using default pipeline", user_type)
            return None

        # 2. Use LLM detection if enabled
        if use_llm:
            try:
                from backend.processors.detector import DocumentTypeDetector

                detected_type = await DocumentTypeDetector.detect(content)
                logger.debug("LLM detected document type: %s", detected_type)

                if detected_type and detected_type != "general":
                    processor = cls.get_processor(detected_type)
                    if processor:
                        logger.info("Using LLM-detected processor: %s", detected_type)
                        return processor
            except Exception as e:
                logger.warning("LLM detection failed: %s", e)

        logger.debug("No domain processor selected, using default pipeline")
        return None


def _register_processors() -> None:
    """Register all available domain processors.

    This is called on module import to populate the factory registry.
    """
    try:
        from backend.processors.legal_processor import LegalProcessor

        ProcessorFactory.register("legal", LegalProcessor)
    except ImportError as e:
        logger.debug("Legal processor not available: %s", e)

    try:
        from backend.processors.academic_processor import AcademicProcessor

        ProcessorFactory.register("academic", AcademicProcessor)
    except ImportError as e:
        logger.debug("Academic processor not available: %s", e)

    try:
        from backend.processors.qa_processor import QAProcessor

        ProcessorFactory.register("qa", QAProcessor)
    except ImportError as e:
        logger.debug("Q&A processor not available: %s", e)

    try:
        from backend.processors.table_processor import TableProcessor

        ProcessorFactory.register("table", TableProcessor)
    except ImportError as e:
        logger.debug("Table processor not available: %s", e)

    # Sprint 2: New domain processors from RAGFlow
    try:
        from backend.processors.book_processor import BookProcessor

        ProcessorFactory.register("book", BookProcessor)
    except ImportError as e:
        logger.debug("Book processor not available: %s", e)

    try:
        from backend.processors.email_processor import EmailProcessor

        ProcessorFactory.register("email", EmailProcessor)
    except ImportError as e:
        logger.debug("Email processor not available: %s", e)

    try:
        from backend.processors.manual_processor import ManualProcessor

        ProcessorFactory.register("manual", ManualProcessor)
    except ImportError as e:
        logger.debug("Manual processor not available: %s", e)

    try:
        from backend.processors.presentation_processor import PresentationProcessor

        ProcessorFactory.register("presentation", PresentationProcessor)
    except ImportError as e:
        logger.debug("Presentation processor not available: %s", e)

    # Sprint 3: Resume processor
    try:
        from backend.processors.resume_processor import ResumeProcessor

        ProcessorFactory.register("resume", ResumeProcessor)
    except ImportError as e:
        logger.debug("Resume processor not available: %s", e)


# Register processors on module import
_register_processors()

__all__ = [
    "ProcessorFactory",
    "DomainProcessor",
    "ProcessorResult",
    "VALID_DOCUMENT_TYPES",
    "LLMResumeExtractor",
]

# Export LLM resume extractor for direct use
try:
    from backend.processors.llm_resume_extractor import LLMResumeExtractor
except ImportError:
    LLMResumeExtractor = None  # type: ignore
