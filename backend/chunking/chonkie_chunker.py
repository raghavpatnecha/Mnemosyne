"""
Chonkie Chunker - Hierarchical chunking with embedding optimization

Implements SurfSense-inspired two-stage pipeline:
1. RecursiveChunker: Preserves document hierarchy (headers, sections, paragraphs)
2. LateChunker: Optimizes chunk sizes for embedding model's max_seq_length

This prevents the "tiny header fragment" problem where semantic chunking
creates isolated header chunks that lack context.

Research sources:
- SurfSense: https://github.com/MODSetter/SurfSense
- Chonkie: https://github.com/chonkie-inc/chonkie
"""

from typing import List, Dict, Any, Optional
import tiktoken
import logging

from backend.config import settings

logger = logging.getLogger(__name__)


class ChonkieChunker:
    """
    Two-stage hierarchical chunking using Chonkie

    Stage 1 - RecursiveChunker:
    - Splits text respecting document structure (headers, paragraphs, sentences)
    - Uses hierarchy of RecursiveRules with delimiters
    - Prevents tiny header fragments by keeping context together

    Stage 2 - LateChunker:
    - Optimizes chunk sizes for the embedding model
    - Uses embedding model's max_seq_length for optimal chunking
    - Ensures chunks are neither too small (poor retrieval) nor too large (poor precision)
    """

    def __init__(
        self,
        chunk_size: int = settings.CHUNK_SIZE,
        chunk_overlap: int = settings.CHUNK_OVERLAP,
        embedding_model: str = settings.EMBEDDING_MODEL,
        min_characters_per_chunk: int = 50,
    ):
        """
        Initialize the two-stage chunker

        Args:
            chunk_size: Target chunk size in tokens (default from settings)
            chunk_overlap: Overlap between chunks in tokens (used for fallback)
            embedding_model: Model name for LateChunker optimization
            min_characters_per_chunk: Minimum characters to keep a chunk
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.min_characters_per_chunk = min_characters_per_chunk
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Lazy initialization of chunkers (expensive imports)
        self._recursive_chunker = None
        self._late_chunker = None
        self._openai_embeddings = None

    def _get_sentence_transformer_embeddings(self):
        """Lazy load SentenceTransformer embeddings for LateChunker"""
        if self._openai_embeddings is None:
            from chonkie.embeddings import SentenceTransformerEmbeddings
            # Use a fast, high-quality model for chunking optimization
            # all-MiniLM-L6-v2: 384 dimensions, fast, good quality
            self._openai_embeddings = SentenceTransformerEmbeddings(
                model="all-MiniLM-L6-v2"
            )
        return self._openai_embeddings

    def _get_recursive_chunker(self):
        """
        Lazy load RecursiveChunker

        RecursiveChunker respects document hierarchy using RecursiveRules:
        - Level 1: Double newlines (paragraphs/sections)
        - Level 2: Punctuation (.!?)
        - Level 3: Structural characters
        - Level 4: Whitespace
        - Level 5: Character-level (last resort)

        This keeps headers WITH their content instead of isolating them.
        """
        if self._recursive_chunker is None:
            from chonkie import RecursiveChunker
            from chonkie.types.recursive import RecursiveRules, RecursiveLevel

            # Custom rules for document chunking - prioritize structural boundaries
            document_rules = RecursiveRules(
                levels=[
                    # Level 1: Major section boundaries (paragraphs, sections)
                    RecursiveLevel(
                        delimiters=["\n\n\n", "\n\n", "\r\n\r\n"],
                        whitespace=False,
                        include_delim="prev",
                    ),
                    # Level 2: Line boundaries
                    RecursiveLevel(
                        delimiters=["\n", "\r\n", "\r"],
                        whitespace=False,
                        include_delim="prev",
                    ),
                    # Level 3: Sentence boundaries
                    RecursiveLevel(
                        delimiters=[". ", "! ", "? ", ".\n", "!\n", "?\n"],
                        whitespace=False,
                        include_delim="prev",
                    ),
                    # Level 4: Clause boundaries
                    RecursiveLevel(
                        delimiters=["; ", ", ", ": "],
                        whitespace=False,
                        include_delim="prev",
                    ),
                    # Level 5: Word boundaries (whitespace)
                    RecursiveLevel(
                        delimiters=None,
                        whitespace=True,
                        include_delim="prev",
                    ),
                    # Level 6: Character-level (last resort)
                    RecursiveLevel(
                        delimiters=None,
                        whitespace=False,
                        include_delim="prev",
                    ),
                ]
            )

            self._recursive_chunker = RecursiveChunker(
                tokenizer="cl100k_base",  # OpenAI's tokenizer (chonkie 1.4+)
                chunk_size=self.chunk_size,
                rules=document_rules,
                min_characters_per_chunk=self.min_characters_per_chunk,
            )
            logger.info(
                f"RecursiveChunker initialized: size={self.chunk_size}, "
                f"min_chars={self.min_characters_per_chunk}"
            )
        return self._recursive_chunker

    def _get_late_chunker(self):
        """
        Lazy load LateChunker

        LateChunker is a "late" chunking strategy that:
        - Takes the text and applies embedding-aware chunking
        - Optimizes chunk boundaries based on embedding model's max_seq_length
        - Ensures chunks are optimal for the specific embedding model

        This is the SurfSense approach for high-quality embeddings.
        """
        if self._late_chunker is None:
            from chonkie import LateChunker

            embeddings = self._get_sentence_transformer_embeddings()

            self._late_chunker = LateChunker(
                embedding_model=embeddings,
                chunk_size=self.chunk_size,
                min_characters_per_chunk=self.min_characters_per_chunk,
            )
            logger.info(
                f"LateChunker initialized: model=all-MiniLM-L6-v2, "
                f"size={self.chunk_size}"
            )
        return self._late_chunker

    def chunk(self, text: str, use_late_chunking: bool = True) -> List[Dict[str, Any]]:
        """
        Chunk text using two-stage pipeline

        Args:
            text: Input text to chunk
            use_late_chunking: If True, apply LateChunker optimization (default True)
                              Set False for faster processing without embedding optimization

        Returns:
            List of chunks with metadata including:
            - content: The chunk text
            - chunk_index: Position in document
            - metadata: type, tokens, start_char, end_char, chunking_method
        """
        if not text or not text.strip():
            logger.warning("Empty text provided to chunker")
            return []

        # Stage 1: RecursiveChunker - preserve document hierarchy
        recursive_chunker = self._get_recursive_chunker()
        initial_chunks = recursive_chunker.chunk(text)

        logger.debug(
            f"Stage 1 (RecursiveChunker): {len(initial_chunks)} chunks"
        )

        if use_late_chunking and initial_chunks:
            # Stage 2: LateChunker - optimize for embeddings
            late_chunker = self._get_late_chunker()
            final_chunks = late_chunker.chunk(text)
            chunking_method = "recursive+late"

            logger.debug(
                f"Stage 2 (LateChunker): {len(final_chunks)} chunks"
            )
        else:
            final_chunks = initial_chunks
            chunking_method = "recursive"

        # Convert to output format
        result = []
        for idx, chunk in enumerate(final_chunks):
            tokens = len(self.tokenizer.encode(chunk.text))

            # Skip extremely small chunks (likely parsing artifacts)
            if tokens < 10:
                logger.debug(
                    f"Skipping tiny chunk ({tokens} tokens): "
                    f"{chunk.text[:50]}..."
                )
                continue

            result.append({
                "content": chunk.text,
                "chunk_index": idx,
                "metadata": {
                    "type": chunking_method,
                    "tokens": tokens,
                    "start_char": getattr(chunk, 'start_index', 0),
                    "end_char": getattr(chunk, 'end_index', len(chunk.text)),
                }
            })

        # Re-index after filtering
        for idx, chunk in enumerate(result):
            chunk["chunk_index"] = idx

        avg_tokens = (
            sum(c['metadata']['tokens'] for c in result) // max(len(result), 1)
        )
        logger.info(
            f"Chunking complete: {len(result)} chunks "
            f"(method={chunking_method}, avg_tokens={avg_tokens})"
        )

        return result

    def chunk_for_code(
        self, text: str, language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Specialized chunking for code content

        Uses code-aware rules that respect programming constructs.

        Args:
            text: Code content to chunk
            language: Programming language hint (optional)

        Returns:
            List of chunks optimized for code
        """
        from chonkie import RecursiveChunker
        from chonkie.types.recursive import RecursiveRules, RecursiveLevel

        # Code-specific rules
        code_rules = RecursiveRules(
            levels=[
                # Level 1: Class and function definitions
                RecursiveLevel(
                    delimiters=["\n\nclass ", "\n\ndef ", "\n\nasync def "],
                    whitespace=False,
                    include_delim="prev",
                ),
                # Level 2: Blank lines (method separation)
                RecursiveLevel(
                    delimiters=["\n\n"],
                    whitespace=False,
                    include_delim="prev",
                ),
                # Level 3: Single newlines
                RecursiveLevel(
                    delimiters=["\n"],
                    whitespace=False,
                    include_delim="prev",
                ),
                # Level 4: Statements
                RecursiveLevel(
                    delimiters=["; ", ": "],
                    whitespace=False,
                    include_delim="prev",
                ),
                # Level 5: Whitespace
                RecursiveLevel(
                    delimiters=None,
                    whitespace=True,
                    include_delim="prev",
                ),
            ]
        )

        code_chunker = RecursiveChunker(
            tokenizer="cl100k_base",  # OpenAI's tokenizer (chonkie 1.4+)
            chunk_size=self.chunk_size,
            rules=code_rules,
            min_characters_per_chunk=self.min_characters_per_chunk,
        )

        chunks = code_chunker.chunk(text)

        result = []
        for idx, chunk in enumerate(chunks):
            tokens = len(self.tokenizer.encode(chunk.text))
            result.append({
                "content": chunk.text,
                "chunk_index": idx,
                "metadata": {
                    "type": "code",
                    "language": language,
                    "tokens": tokens,
                    "start_char": getattr(chunk, 'start_index', 0),
                    "end_char": getattr(chunk, 'end_index', len(chunk.text)),
                }
            })

        return result
