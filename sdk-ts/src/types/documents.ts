/**
 * Type definitions for Documents API
 */

import { Pagination } from './common.js';

/**
 * Processing status for documents
 */
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';

/**
 * Schema for creating a document (used with multipart form data)
 */
export interface DocumentCreate {
  collection_id: string;
  title?: string;
  filename?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Schema for updating document metadata (all fields optional)
 */
export interface DocumentUpdate {
  title?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Schema for document responses
 */
export interface DocumentResponse {
  id: string;
  collection_id: string;
  user_id: string;
  title?: string;
  filename?: string;
  content_type?: string;
  size_bytes?: number;
  content_hash: string;
  unique_identifier_hash?: string;
  status: ProcessingStatus;
  metadata: Record<string, unknown>;
  processing_info?: Record<string, unknown>;
  created_at: string;
  updated_at?: string;
}

/**
 * Schema for paginated list of documents
 */
export interface DocumentListResponse {
  data: DocumentResponse[];
  pagination: Pagination;
}

/**
 * Schema for document processing status
 */
export interface DocumentStatusResponse {
  document_id: string;
  status: ProcessingStatus;
  chunk_count: number;
  total_tokens: number;
  error_message?: string;
  processing_info: Record<string, unknown>;
  created_at: string;
  processed_at?: string;
}
