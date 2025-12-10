/**
 * Mnemosyne SDK - TypeScript client for Mnemosyne RAG API
 *
 * @packageDocumentation
 */

// Main client
export { MnemosyneClient } from './client.js';
export { MnemosyneClient as default } from './client.js';

// Base client and config
export type { BaseClientConfig } from './base-client.js';

// Exceptions
export {
  MnemosyneError,
  AuthenticationError,
  PermissionError,
  NotFoundError,
  ValidationError,
  RateLimitError,
  APIError,
} from './exceptions.js';

// Streaming utilities and types
export { parseSSEStream } from './streaming.js';
export type { SSEEvent, SSEEventType } from './streaming.js';

// All type definitions
export type {
  // Common
  Pagination,
  PaginatedResponse,
  // Auth
  RegisterRequest,
  RegisterResponse,
  // Collections
  CollectionCreate,
  CollectionUpdate,
  CollectionResponse,
  CollectionListResponse,
  // Documents
  ProcessingStatus,
  DocumentCreate,
  DocumentUpdate,
  DocumentResponse,
  DocumentListResponse,
  DocumentStatusResponse,
  // Retrievals
  RetrievalMode,
  RetrievalRequest,
  DocumentInfo,
  ChunkResult,
  RetrievalResponse,
  // Chat
  ChatPreset,
  ReasoningMode,
  ChatRequest,
  MediaItem,
  FollowUpQuestion,
  Source,
  SourceReference,
  UsageStats,
  ChatMetadata,
  ChatCompletionResponse,
  StreamChunkType,
  StreamChunk,
  ChatResponse,
  ChatSessionResponse,
  ChatMessageResponse,
} from './types/index.js';

// Version
export { VERSION } from './version.js';
