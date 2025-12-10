"""
Pydantic Schemas for Chat endpoints
OpenAI-compatible request/response with RAG enhancements
"""

from pydantic import BaseModel, Field, model_validator
from typing import List, Dict, Optional, Literal, Self
from uuid import UUID
from datetime import datetime, timezone
from enum import Enum


class MessageRole(str, Enum):
    """Message roles"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class ChatPreset(str, Enum):
    """Predefined answer style configurations"""
    CONCISE = "concise"      # Brief, to-the-point answers
    DETAILED = "detailed"    # Comprehensive explanations
    RESEARCH = "research"    # Academic style with citations
    TECHNICAL = "technical"  # Precise, detail-oriented answers
    CREATIVE = "creative"    # More exploratory responses
    QNA = "qna"              # Question generation and answer creation mode


class ReasoningMode(str, Enum):
    """Reasoning depth modes"""
    STANDARD = "standard"    # Single-pass retrieval + generation
    DEEP = "deep"            # Multi-step iterative reasoning


class Message(BaseModel):
    """Single chat message (OpenAI-compatible)"""
    role: MessageRole = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class RetrievalConfig(BaseModel):
    """Configuration for retrieval phase"""
    mode: Literal["semantic", "keyword", "hybrid", "graph"] = Field(
        default="hybrid",
        description="Search mode: semantic, keyword, hybrid, or graph"
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Number of chunks to retrieve"
    )
    rerank: bool = Field(
        default=True,
        description="Enable cross-encoder reranking"
    )
    enable_graph: bool = Field(
        default=True,
        description="Enable LightRAG knowledge graph enhancement"
    )
    hierarchical: bool = Field(
        default=True,
        description="Enable two-tier hierarchical search"
    )
    expand_context: bool = Field(
        default=True,
        description="Expand results with surrounding chunks"
    )
    metadata_filter: Optional[Dict] = Field(
        None,
        description="Metadata filters for retrieval"
    )


class GenerationConfig(BaseModel):
    """Configuration for LLM generation phase"""
    model: str = Field(
        default=None,  # Uses settings.CHAT_MODEL if not specified
        description="LLM model to use (defaults to CHAT_MODEL from settings)"
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=1000,
        ge=1,
        le=4096,
        description="Maximum tokens to generate"
    )
    top_p: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling parameter"
    )
    frequency_penalty: float = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="Frequency penalty"
    )
    presence_penalty: float = Field(
        default=0.0,
        ge=-2.0,
        le=2.0,
        description="Presence penalty"
    )


class ChatRequest(BaseModel):
    """
    Request schema for chat endpoint (OpenAI-compatible)

    Supports both single message (backward compatible) and messages array.
    """
    # Message input (supports both formats)
    messages: Optional[List[Message]] = Field(
        None,
        description="Array of messages (OpenAI-compatible)"
    )
    message: Optional[str] = Field(
        None,
        max_length=10000,
        description="Single user message (backward compatible, deprecated)"
    )

    # Session management
    session_id: Optional[UUID] = Field(
        None,
        description="Session ID for multi-turn (creates new if not provided)"
    )

    # Collection scope
    collection_id: Optional[UUID] = Field(
        None,
        description="Filter retrieval by collection"
    )

    # Response format
    stream: bool = Field(
        default=True,
        description="Enable streaming (SSE)"
    )

    # NEW: Model selection (LiteLLM compatible) - overrides generation.model
    model: Optional[str] = Field(
        None,
        description="LLM model override (e.g., 'gpt-4o', 'claude-3-opus', 'ollama/llama3')"
    )

    # NEW: Answer style preset
    preset: ChatPreset = Field(
        default=ChatPreset.DETAILED,
        description="Answer style preset (concise, detailed, research, technical, creative)"
    )

    # NEW: Deep reasoning mode
    reasoning_mode: ReasoningMode = Field(
        default=ReasoningMode.STANDARD,
        description="Reasoning mode: standard (single-pass) or deep (multi-step iterative)"
    )

    # NEW: Fine-grained controls (override preset defaults)
    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Temperature override (0.0-2.0)"
    )
    max_tokens: Optional[int] = Field(
        None,
        ge=1,
        le=8192,
        description="Max tokens override"
    )

    # Sub-configurations
    retrieval: RetrievalConfig = Field(
        default_factory=RetrievalConfig,
        description="Retrieval configuration"
    )
    generation: GenerationConfig = Field(
        default_factory=GenerationConfig,
        description="Generation configuration"
    )

    # NEW: Custom instruction for additional guidance
    custom_instruction: Optional[str] = Field(
        None,
        max_length=2000,
        description="Custom instruction to append to the prompt (e.g., 'focus on security aspects', 'generate 10 MCQs')"
    )

    # NEW: Follow-up question flag
    is_follow_up: bool = Field(
        default=False,
        description="Whether this is a follow-up to a previous question. When true, previous context is preserved and merged with new context."
    )

    @model_validator(mode='after')
    def validate_message_input(self) -> Self:
        """Validate that either messages or message is provided"""
        if not self.messages and not self.message:
            raise ValueError("Either 'messages' or 'message' must be provided")
        return self

    def get_user_message(self) -> str:
        """Extract user message from either format"""
        if self.messages:
            # Find last user message
            for msg in reversed(self.messages):
                if msg.role == MessageRole.USER:
                    return msg.content
            raise ValueError("No user message found in messages array")
        elif self.message:
            return self.message
        else:
            raise ValueError("Either 'messages' or 'message' must be provided")

    def get_system_prompt(self) -> Optional[str]:
        """Extract system prompt if provided"""
        if self.messages:
            for msg in self.messages:
                if msg.role == MessageRole.SYSTEM:
                    return msg.content
        return None


class DocumentInfo(BaseModel):
    """Document metadata in sources"""
    id: str
    title: Optional[str] = None
    filename: Optional[str] = None


class MediaItem(BaseModel):
    """Media item extracted from chunks"""
    type: Literal["image", "table", "figure", "video", "audio"] = Field(
        ..., description="Type of media"
    )
    source_document_id: str = Field(..., description="Document containing this media")
    source_document_title: Optional[str] = Field(None, description="Document title")
    description: Optional[str] = Field(None, description="Description or caption")
    page_number: Optional[int] = Field(None, description="Page number if applicable")
    url: Optional[str] = Field(None, description="URL to access the media (if stored)")
    content_preview: Optional[str] = Field(
        None, description="Text preview for tables or extracted text from images"
    )


class FollowUpQuestion(BaseModel):
    """Suggested follow-up question"""
    question: str = Field(..., description="The follow-up question")
    relevance: str = Field(
        ..., description="Why this question is relevant (brief explanation)"
    )


class SourceReference(BaseModel):
    """Lightweight source reference showing where info came from"""
    document_id: str = Field(..., description="Document UUID")
    title: Optional[str] = Field(None, description="Document title")
    filename: Optional[str] = Field(None, description="Original filename")
    chunk_index: int = Field(..., description="Chunk position in document")
    score: float = Field(..., description="Relevance score (0-1)")


class Source(BaseModel):
    """Source chunk with full metadata (used internally)"""
    chunk_id: str
    content: str
    chunk_index: int
    score: float = Field(..., description="Retrieval score (0-1)")
    rerank_score: Optional[float] = Field(
        None,
        description="Cross-encoder reranking score (0-1)"
    )
    document: DocumentInfo
    collection_id: str
    expanded_content: Optional[str] = Field(
        None,
        description="Content with surrounding context merged"
    )
    metadata: Optional[Dict] = None


class GraphContext(BaseModel):
    """Knowledge graph context from LightRAG"""
    enabled: bool = Field(
        default=False,
        description="Whether graph enhancement was used"
    )
    context: Optional[str] = Field(
        None,
        description="Graph-derived context narrative"
    )
    entities_found: int = Field(
        default=0,
        description="Number of entities extracted"
    )
    relationships_found: int = Field(
        default=0,
        description="Number of relationships found"
    )


class UsageStats(BaseModel):
    """Token usage statistics (OpenAI-compatible)"""
    prompt_tokens: int = Field(..., description="Tokens in prompt")
    completion_tokens: int = Field(..., description="Tokens in response")
    total_tokens: int = Field(..., description="Total tokens used")
    retrieval_tokens: int = Field(
        default=0,
        description="Tokens used in retrieval context"
    )


class ChatMetadata(BaseModel):
    """Response metadata"""
    session_id: UUID
    user_id: UUID
    collection_id: Optional[UUID] = None
    retrieval_mode: str
    model: str
    latency_ms: int = Field(..., description="Total response time in milliseconds")
    retrieval_latency_ms: int = Field(
        default=0,
        description="Retrieval phase latency in milliseconds"
    )
    generation_latency_ms: int = Field(
        default=0,
        description="Generation phase latency in milliseconds"
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Response timestamp"
    )
    # LLM-as-Judge fields
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Response confidence score from judge (0-1)"
    )
    judge_corrected: bool = Field(
        default=False,
        description="Whether the response was corrected by the judge"
    )


class ChatCompletionResponse(BaseModel):
    """
    Complete chat response (non-streaming)

    OpenAI-compatible structure with RAG enhancements.
    """
    # Core response
    query: str = Field(..., description="Original user query")
    response: str = Field(..., description="Generated response")

    # Sources - lightweight references showing where info came from
    sources: List[SourceReference] = Field(
        default_factory=list,
        description="Document sources used to generate the response"
    )

    # Media items extracted from retrieved chunks
    media: List[MediaItem] = Field(
        default_factory=list,
        description="Media items (images, tables, figures) from retrieved chunks"
    )

    # Follow-up questions for continued exploration
    follow_up_questions: List[FollowUpQuestion] = Field(
        default_factory=list,
        description="Suggested follow-up questions based on the response"
    )

    # Usage tracking
    usage: UsageStats = Field(..., description="Token usage statistics")

    # Metadata
    metadata: ChatMetadata = Field(..., description="Response metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What is machine learning?",
                "response": "Machine learning is a subset of artificial intelligence...",
                "sources": [
                    {
                        "document_id": "8c06e14d-caf4-4abd-9795-0d886f4fa80e",
                        "title": "AI Fundamentals.pdf",
                        "filename": "AI Fundamentals.pdf",
                        "chunk_index": 5,
                        "score": 0.92
                    }
                ],
                "usage": {
                    "prompt_tokens": 1250,
                    "completion_tokens": 350,
                    "total_tokens": 1600,
                    "retrieval_tokens": 800
                },
                "metadata": {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "123e4567-e89b-12d3-a456-426614174000",
                    "collection_id": "789e0123-e45b-67d8-b901-234567890abc",
                    "retrieval_mode": "hybrid",
                    "model": "gpt-4o-mini",
                    "latency_ms": 1250,
                    "retrieval_latency_ms": 450,
                    "generation_latency_ms": 800,
                    "timestamp": "2025-01-15T10:30:00Z"
                }
            }
        }


class StreamChunk(BaseModel):
    """
    Single chunk in streaming response (SSE format)

    Types:
    - delta: Incremental text content
    - sources: Retrieved sources (sent once at start)
    - media: Media items from retrieved chunks (sent after sources)
    - follow_up: Suggested follow-up questions (sent near end)
    - usage: Token usage (sent at end)
    - done: Stream completion signal
    - error: Error message
    - reasoning_step: Deep reasoning progress (step number + description)
    - sub_query: Sub-query generated during deep reasoning
    """
    type: Literal[
        "delta", "sources", "media", "follow_up", "usage", "done", "error",
        "reasoning_step", "sub_query"
    ]
    content: Optional[str] = None
    sources: Optional[List[SourceReference]] = None
    media: Optional[List[MediaItem]] = None
    follow_up_questions: Optional[List[FollowUpQuestion]] = None
    usage: Optional[UsageStats] = None
    metadata: Optional[ChatMetadata] = None
    error: Optional[str] = None
    # NEW: Deep reasoning fields
    step: Optional[int] = Field(None, description="Reasoning step number (1-3)")
    description: Optional[str] = Field(None, description="Reasoning step description")
    query: Optional[str] = Field(None, description="Sub-query text for sub_query type")


# Session management schemas (unchanged)
class ChatSessionResponse(BaseModel):
    """Chat session metadata"""
    id: UUID
    user_id: UUID
    collection_id: Optional[UUID]
    title: Optional[str]
    created_at: datetime
    last_message_at: Optional[datetime]
    message_count: int

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    """Chat message response"""
    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
