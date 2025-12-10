"""
NLP utilities for Mnemosyne.

Provides natural language processing enhancements:
- Synonym expansion for query reformulation
- Term weighting (future)
- Entity recognition helpers (future)

Ported from RAGFlow's rag/nlp module.
"""

from backend.nlp.synonym import SynonymService, SynonymSource

__all__ = [
    "SynonymService",
    "SynonymSource",
]
