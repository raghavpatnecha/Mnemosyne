"""Type definitions for Chat API - OpenAI-compatible with RAG enhancements"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Literal
from uuid import UUID
from datetime import datetime
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
        description="Search mode"
    )
    top_k: int = Field(default=5, ge=1, le=50, description="Number of chunks")
    rerank: bool = Field(default=True, description="Enable reranking")
    enable_graph: bool = Field(default=True, description="Enable LightRAG")
    hierarchical: bool = Field(default=True, description="Enable hierarchical search")
    expand_context: bool = Field(default=True, description="Expand with surrounding chunks")
    metadata_filter: Optional[Dict] = Field(None, description="Metadata filters")


class GenerationConfig(BaseModel):
    """Configuration for LLM generation"""
    model: str = Field(default="gpt-4o-mini", description="LLM model")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(default=1000, ge=1, le=4096, description="Max tokens")
    top_p: float = Field(default=1.0, ge=0.0, le=1.0, description="Nucleus sampling")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)


class ChatRequest(BaseModel):
    """
    Request schema for chat endpoint (OpenAI-compatible)

    Supports both messages array and legacy single message.
    """
    messages: Optional[List[Message]] = Field(None, description="Messages array (recommended)")
    message: Optional[str] = Field(None, max_length=10000, description="Single message (deprecated)")
    session_id: Optional[UUID] = Field(None, description="Session ID for multi-turn")
    collection_id: Optional[UUID] = Field(None, description="Filter by collection")
    stream: bool = Field(default=True, description="Enable streaming")
    # NEW: Model override
    model: Optional[str] = Field(None, description="LLM model override (e.g., 'gpt-4o', 'claude-3-opus')")
    # NEW: Answer style preset
    preset: ChatPreset = Field(default=ChatPreset.DETAILED, description="Answer style preset")
    # NEW: Deep reasoning mode
    reasoning_mode: ReasoningMode = Field(default=ReasoningMode.STANDARD, description="Reasoning mode")
    # NEW: Fine-grained controls
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0, description="Temperature override")
    max_tokens: Optional[int] = Field(None, ge=1, le=8192, description="Max tokens override")
    # Sub-configurations
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    # Custom instruction for additional guidance
    custom_instruction: Optional[str] = Field(
        None,
        max_length=2000,
        description="Custom instruction to append to the prompt (e.g., 'focus on security aspects', 'generate 10 MCQs')"
    )
    # Follow-up question flag
    is_follow_up: bool = Field(
        default=False,
        description="Whether this is a follow-up to a previous question. When true, previous context is preserved."
    )


class DocumentInfo(BaseModel):
    """Document metadata in sources"""
    id: str
    title: Optional[str] = None
    filename: Optional[str] = None


class MediaItem(BaseModel):
    """Media item extracted from retrieved chunks"""
    type: Literal["image", "table", "figure", "video", "audio"] = Field(
        ..., description="Type of media"
    )
    source_document_id: str = Field(..., description="Document containing this media")
    source_document_title: Optional[str] = Field(None, description="Document title")
    description: Optional[str] = Field(None, description="Description or caption")
    page_number: Optional[int] = Field(None, description="Page number if applicable")
    url: Optional[str] = Field(None, description="URL to access the media")
    content_preview: Optional[str] = Field(None, description="Text preview for tables")


class FollowUpQuestion(BaseModel):
    """Suggested follow-up question"""
    question: str = Field(..., description="The follow-up question")
    relevance: str = Field(..., description="Why this question is relevant")


class SourceReference(BaseModel):
    """Lightweight source reference showing where info came from"""
    document_id: str = Field(..., description="Document UUID")
    title: Optional[str] = Field(None, description="Document title")
    filename: Optional[str] = Field(None, description="Original filename")
    chunk_index: int = Field(..., description="Chunk position in document")
    score: float = Field(..., description="Relevance score (0-1)")


class Source(BaseModel):
    """Source chunk with full metadata (used by retrieval endpoint)"""
    chunk_id: str
    content: str
    chunk_index: int
    score: float = Field(..., description="Retrieval score (0-1)")
    rerank_score: Optional[float] = Field(None, description="Reranking score (0-1)")
    document: DocumentInfo
    collection_id: str
    expanded_content: Optional[str] = Field(None, description="Content with surrounding context")
    metadata: Optional[Dict] = None


class GraphContext(BaseModel):
    """Knowledge graph context from LightRAG"""
    enabled: bool = Field(default=False)
    context: Optional[str] = Field(None, description="Graph-derived context")
    entities_found: int = Field(default=0)
    relationships_found: int = Field(default=0)


class UsageStats(BaseModel):
    """Token usage statistics (OpenAI-compatible)"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    retrieval_tokens: int = Field(default=0)


class ChatMetadata(BaseModel):
    """Response metadata"""
    session_id: UUID
    user_id: UUID
    collection_id: Optional[UUID] = None
    retrieval_mode: str
    model: str
    latency_ms: int
    retrieval_latency_ms: int = 0
    generation_latency_ms: int = 0
    timestamp: datetime
    # LLM-as-Judge fields
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Response confidence (0-1)")
    judge_corrected: bool = Field(default=False, description="Whether response was corrected")


class ChatCompletionResponse(BaseModel):
    """Complete chat response (non-streaming)"""
    query: str = Field(..., description="Original user query")
    response: str = Field(..., description="Generated response")
    sources: List[SourceReference] = Field(default_factory=list, description="Document sources")
    media: List[MediaItem] = Field(default_factory=list, description="Media items from chunks")
    follow_up_questions: List[FollowUpQuestion] = Field(default_factory=list, description="Suggested follow-ups")
    usage: UsageStats
    metadata: ChatMetadata


class StreamChunk(BaseModel):
    """
    Single chunk in streaming response

    Types:
    - delta: Incremental text content
    - sources: Retrieved sources
    - media: Media items from chunks
    - follow_up: Suggested follow-up questions
    - usage: Token usage (at end)
    - done: Stream completion signal
    - error: Error message
    - reasoning_step: Deep reasoning progress
    - sub_query: Sub-query during deep reasoning
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
    # Deep reasoning fields
    step: Optional[int] = Field(None, description="Reasoning step number (1-3)")
    description: Optional[str] = Field(None, description="Reasoning step description")
    query: Optional[str] = Field(None, description="Sub-query text")


# Legacy alias for backward compatibility
ChatResponse = ChatCompletionResponse


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
