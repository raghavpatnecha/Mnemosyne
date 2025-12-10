/**
 * Type definitions for Chat API - OpenAI-compatible with RAG enhancements
 */

/**
 * Message role enum
 */
export type MessageRole = 'system' | 'user' | 'assistant';

/**
 * Chat preset for answer style
 */
export type ChatPreset = 'concise' | 'detailed' | 'research' | 'technical' | 'creative' | 'qna';

/**
 * Reasoning mode
 */
export type ReasoningMode = 'standard' | 'deep';

/**
 * Single chat message (OpenAI-compatible)
 */
export interface Message {
  role: MessageRole;
  content: string;
}

/**
 * Retrieval configuration
 */
export interface RetrievalConfig {
  mode?: 'semantic' | 'keyword' | 'hybrid' | 'graph';
  top_k?: number;
  rerank?: boolean;
  enable_graph?: boolean;
  hierarchical?: boolean;
  expand_context?: boolean;
  metadata_filter?: Record<string, unknown>;
}

/**
 * Generation configuration
 */
export interface GenerationConfig {
  model?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
}

/**
 * Request schema for chat endpoint (OpenAI-compatible)
 */
export interface ChatRequest {
  messages?: Message[];
  message?: string;
  session_id?: string;
  collection_id?: string;
  stream?: boolean;
  /** LLM model override (e.g., 'gpt-4o', 'claude-3-opus') */
  model?: string;
  /** Answer style preset */
  preset?: ChatPreset;
  /** Reasoning mode: standard (single-pass) or deep (multi-step iterative) */
  reasoning_mode?: ReasoningMode;
  /** Temperature override (0.0-2.0) */
  temperature?: number;
  /** Max tokens override */
  max_tokens?: number;
  retrieval?: RetrievalConfig;
  generation?: GenerationConfig;
  /** Custom instruction to append to the prompt (e.g., 'focus on security aspects', 'generate 10 MCQs') */
  custom_instruction?: string;
  /** Whether this is a follow-up to a previous question. When true, previous context is preserved. */
  is_follow_up?: boolean;
}

/**
 * Document info in sources
 */
export interface DocumentInfo {
  id: string;
  title?: string;
  filename?: string;
}

/**
 * Media item extracted from retrieved chunks
 */
export interface MediaItem {
  type: 'image' | 'table' | 'figure' | 'video' | 'audio';
  source_document_id: string;
  source_document_title?: string;
  description?: string;
  page_number?: number;
  url?: string;
  content_preview?: string;
}

/**
 * Suggested follow-up question
 */
export interface FollowUpQuestion {
  question: string;
  relevance: string;
}

/**
 * Lightweight source reference for API responses
 */
export interface SourceReference {
  document_id: string;
  title?: string;
  filename?: string;
  chunk_index: number;
  score: number;
}

/**
 * Full source chunk (used internally)
 */
export interface Source {
  chunk_id: string;
  content: string;
  chunk_index: number;
  score: number;
  rerank_score?: number;
  document: DocumentInfo;
  collection_id: string;
  expanded_content?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Token usage statistics (OpenAI-compatible)
 */
export interface UsageStats {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  retrieval_tokens?: number;
}

/**
 * Response metadata
 */
export interface ChatMetadata {
  session_id: string;
  user_id: string;
  collection_id?: string;
  retrieval_mode: string;
  model: string;
  latency_ms: number;
  retrieval_latency_ms?: number;
  generation_latency_ms?: number;
  timestamp: string;
  /** Response confidence score from judge (0-1) */
  confidence?: number;
  /** Whether the response was corrected by the judge */
  judge_corrected?: boolean;
}

/**
 * Complete chat response (non-streaming)
 */
export interface ChatCompletionResponse {
  query: string;
  response: string;
  sources: SourceReference[];
  /** Media items (images, tables, figures) from retrieved chunks */
  media?: MediaItem[];
  /** Suggested follow-up questions based on the response */
  follow_up_questions?: FollowUpQuestion[];
  usage: UsageStats;
  metadata: ChatMetadata;
}

/**
 * Stream chunk types
 */
export type StreamChunkType =
  | 'delta'
  | 'sources'
  | 'media'
  | 'follow_up'
  | 'usage'
  | 'done'
  | 'error'
  | 'reasoning_step'
  | 'sub_query';

/**
 * Single chunk in streaming response
 */
export interface StreamChunk {
  type: StreamChunkType;
  /** Text content (alias: delta) */
  content?: string;
  /** Text content for delta events (same as content, for SSE compatibility) */
  delta?: string;
  sources?: SourceReference[];
  /** Media items from retrieved chunks */
  media?: MediaItem[];
  /** Suggested follow-up questions */
  follow_up_questions?: FollowUpQuestion[];
  usage?: UsageStats;
  metadata?: ChatMetadata;
  /** Stream completion flag for done events */
  done?: boolean;
  /** Session ID for done events */
  session_id?: string;
  error?: string;
  /** Reasoning step number (1-3) for deep reasoning mode */
  step?: number;
  /** Reasoning step description for reasoning_step type */
  description?: string;
  /** Sub-query text for sub_query type */
  query?: string;
}

/**
 * Chat session metadata
 */
export interface ChatSessionResponse {
  id: string;
  user_id: string;
  collection_id?: string;
  title?: string;
  created_at: string;
  last_message_at?: string;
  message_count: number;
}

/**
 * Chat message response
 */
export interface ChatMessageResponse {
  id: string;
  session_id: string;
  role: string;
  content: string;
  created_at: string;
}

// Legacy alias for backward compatibility
export type ChatResponse = ChatCompletionResponse;
