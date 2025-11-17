/**
 * Type definitions for Chat API
 */

/**
 * Request schema for chat endpoint
 */
export interface ChatRequest {
  session_id?: string;
  message: string;
  collection_id?: string;
  top_k?: number;
  stream?: boolean;
}

/**
 * Source chunk information
 */
export interface Source {
  chunk_id: string;
  content: string;
  document: Record<string, unknown>;
  score: number;
}

/**
 * Response schema for chat endpoint (non-streaming)
 */
export interface ChatResponse {
  session_id: string;
  message: string;
  sources: Source[];
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
