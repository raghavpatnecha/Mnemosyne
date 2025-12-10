"""
Synonym Expansion Service for query enhancement.

Provides synonym lookup using:
1. Custom dictionary (domain-specific terms)
2. WordNet fallback (general English synonyms)
3. Caching for performance

Ported from RAGFlow's rag/nlp/synonym.py
"""

import logging
import os
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class SynonymSource(str, Enum):
    """Source of synonyms."""

    CUSTOM = "custom"
    WORDNET = "wordnet"
    COMBINED = "combined"


# Try to import NLTK WordNet
try:
    from nltk.corpus import wordnet as wn
    import nltk

    # Ensure WordNet data is available
    try:
        wn.synsets("test")
        WORDNET_AVAILABLE = True
    except LookupError:
        # Try to download WordNet data
        try:
            nltk.download("wordnet", quiet=True)
            nltk.download("omw-1.4", quiet=True)
            WORDNET_AVAILABLE = True
        except Exception as e:
            logger.warning(f"Failed to download WordNet: {e}")
            WORDNET_AVAILABLE = False
except ImportError:
    WORDNET_AVAILABLE = False
    wn = None
    logger.info("NLTK not installed - WordNet synonyms unavailable")


class SynonymService:
    """
    Synonym expansion service for query enhancement.

    Provides synonym lookup from multiple sources with caching.
    Integrates with QueryReformulationService for enhanced retrieval.

    Features:
    - Custom dictionary support for domain-specific terms
    - WordNet fallback for general English
    - LRU caching for performance
    - Configurable top-N results
    """

    DEFAULT_DICT_PATH = Path(__file__).parent / "data" / "synonyms.txt"
    MAX_SYNONYMS = 5
    CACHE_SIZE = 1000

    def __init__(
        self,
        custom_dict_path: Optional[str] = None,
        use_wordnet: bool = True,
        max_synonyms: int = MAX_SYNONYMS,
    ):
        """
        Initialize SynonymService.

        Args:
            custom_dict_path: Path to custom synonym dictionary file
            use_wordnet: Whether to use WordNet as fallback
            max_synonyms: Maximum synonyms to return per word
        """
        self.max_synonyms = max_synonyms
        self.use_wordnet = use_wordnet and WORDNET_AVAILABLE
        self._custom_dict: Dict[str, Set[str]] = {}

        # Load custom dictionary
        if custom_dict_path:
            self._load_custom_dict(custom_dict_path)
        elif self.DEFAULT_DICT_PATH.exists():
            self._load_custom_dict(str(self.DEFAULT_DICT_PATH))

        logger.info(
            f"SynonymService initialized: "
            f"custom_terms={len(self._custom_dict)}, "
            f"wordnet={'enabled' if self.use_wordnet else 'disabled'}"
        )

    def _load_custom_dict(self, path: str) -> None:
        """
        Load custom synonym dictionary from file.

        File format: word: synonym1, synonym2, synonym3
        Or: word synonym1 synonym2 (space-separated)

        Args:
            path: Path to dictionary file
        """
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    # Try colon format first
                    if ":" in line:
                        word, synonyms = line.split(":", 1)
                        word = word.strip().lower()
                        syns = {s.strip().lower() for s in synonyms.split(",")}
                    else:
                        # Space-separated format
                        parts = line.lower().split()
                        if len(parts) < 2:
                            continue
                        word = parts[0]
                        syns = set(parts[1:])

                    if word and syns:
                        self._custom_dict[word] = syns

            logger.info(f"Loaded {len(self._custom_dict)} custom synonym entries")

        except FileNotFoundError:
            logger.debug(f"Custom synonym dictionary not found: {path}")
        except Exception as e:
            logger.warning(f"Failed to load custom dictionary: {e}")

    @lru_cache(maxsize=CACHE_SIZE)
    def get_synonyms(
        self,
        word: str,
        source: SynonymSource = SynonymSource.COMBINED,
    ) -> List[str]:
        """
        Get synonyms for a word.

        Args:
            word: Word to find synonyms for
            source: Which synonym source(s) to use

        Returns:
            List of synonyms (up to max_synonyms)
        """
        word_lower = word.lower().strip()
        if not word_lower or len(word_lower) < 2:
            return []

        synonyms: Set[str] = set()

        # Try custom dictionary first
        if source in (SynonymSource.CUSTOM, SynonymSource.COMBINED):
            if word_lower in self._custom_dict:
                synonyms.update(self._custom_dict[word_lower])

        # Try WordNet if enabled
        if source in (SynonymSource.WORDNET, SynonymSource.COMBINED):
            if self.use_wordnet and wn:
                wordnet_syns = self._get_wordnet_synonyms(word_lower)
                synonyms.update(wordnet_syns)

        # Remove the original word and return limited results (sorted for determinism)
        synonyms.discard(word_lower)
        return sorted(list(synonyms))[: self.max_synonyms]

    def _get_wordnet_synonyms(self, word: str) -> Set[str]:
        """Get synonyms from WordNet."""
        if not wn:
            return set()

        synonyms = set()
        try:
            for synset in wn.synsets(word):
                for lemma in synset.lemmas():
                    # Get lemma name and clean it
                    name = lemma.name().lower().replace("_", " ")
                    if name != word and len(name) > 1:
                        synonyms.add(name)

                    # Also get antonym-of-antonym (sometimes useful)
                    # Skip for simplicity
        except Exception as e:
            logger.debug(f"WordNet lookup failed for '{word}': {e}")

        return synonyms

    def expand_query(self, query: str, max_expansions: int = 3) -> str:
        """
        Expand a query with synonyms for key terms.

        Args:
            query: Original query text
            max_expansions: Max number of terms to expand

        Returns:
            Expanded query with synonyms added
        """
        words = query.lower().split()
        expanded_terms = []
        expansions_made = 0

        for word in words:
            # Skip short words and common stop words
            if len(word) < 3 or word in STOP_WORDS:
                expanded_terms.append(word)
                continue

            # Get synonyms
            synonyms = self.get_synonyms(word)

            if synonyms and expansions_made < max_expansions:
                # Add word and top synonyms
                expanded_terms.append(word)
                expanded_terms.extend(synonyms[:2])  # Add top 2 synonyms
                expansions_made += 1
            else:
                expanded_terms.append(word)

        return " ".join(expanded_terms)

    def get_related_terms(
        self,
        words: List[str],
        include_original: bool = True,
    ) -> List[str]:
        """
        Get related terms for a list of words.

        Useful for expanding search queries with related vocabulary.

        Args:
            words: List of words to find related terms for
            include_original: Whether to include original words

        Returns:
            List of all related terms
        """
        all_terms = set()

        if include_original:
            all_terms.update(w.lower() for w in words)

        for word in words:
            synonyms = self.get_synonyms(word.lower())
            all_terms.update(synonyms)

        return list(all_terms)

    def add_custom_synonyms(self, word: str, synonyms: List[str]) -> None:
        """
        Add custom synonyms at runtime.

        Args:
            word: Word to add synonyms for
            synonyms: List of synonyms
        """
        word_lower = word.lower()
        if word_lower not in self._custom_dict:
            self._custom_dict[word_lower] = set()

        self._custom_dict[word_lower].update(s.lower() for s in synonyms)

        # Clear cache for this word
        self.get_synonyms.cache_clear()

    def is_available(self) -> bool:
        """Check if synonym service has any sources available."""
        return bool(self._custom_dict) or self.use_wordnet

    def clear_cache(self) -> None:
        """Clear the synonym cache."""
        self.get_synonyms.cache_clear()


# Common English stop words to skip during expansion
STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "been",
    "be", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "must", "can", "this", "that",
    "these", "those", "i", "you", "he", "she", "it", "we", "they",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "just", "also", "now", "here", "there",
}


# Create default singleton instance
_default_service: Optional[SynonymService] = None


def get_synonym_service() -> SynonymService:
    """Get the default synonym service instance."""
    global _default_service
    if _default_service is None:
        _default_service = SynonymService()
    return _default_service
