/**
 * Type definitions for Mnemosyne SDK
 */

// Common types
export type { Pagination, PaginatedResponse } from './common.js';

// Shared types (additional common types)
export type {
  PaginationOptions,
  LimitOffsetPagination,
  Metadata,
  Timestamp,
  UUID,
} from './shared.js';

// Auth types
export type { RegisterRequest, RegisterResponse } from './auth.js';

// Collection types
export type {
  CollectionCreate,
  CollectionUpdate,
  CollectionResponse,
  CollectionListResponse,
} from './collections.js';

// Document types
export type {
  ProcessingStatus,
  DocumentCreate,
  DocumentUpdate,
  DocumentResponse,
  DocumentListResponse,
  DocumentStatusResponse,
} from './documents.js';

// Retrieval types
export type {
  RetrievalMode,
  RetrievalRequest,
  DocumentInfo,
  ChunkResult,
  RetrievalResponse,
} from './retrievals.js';

// Chat types
export type {
  MessageRole,
  ChatPreset,
  ReasoningMode,
  Message,
  RetrievalConfig,
  GenerationConfig,
  ChatRequest,
  DocumentInfo as ChatDocumentInfo,
  MediaItem,
  FollowUpQuestion,
  SourceReference,
  Source,
  UsageStats,
  ChatMetadata,
  ChatCompletionResponse,
  StreamChunkType,
  StreamChunk,
  ChatSessionResponse,
  ChatMessageResponse,
  ChatResponse,
} from './chat.js';
