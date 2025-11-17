/**
 * Type definitions for Retrievals API
 */

/**
 * Retrieval modes supported by the API
 */
export type RetrievalMode = 'semantic' | 'keyword' | 'hybrid' | 'hierarchical' | 'graph';

/**
 * Request schema for retrieval endpoint
 */
export interface RetrievalRequest {
  query: string;
  mode?: RetrievalMode;
  top_k?: number;
  collection_id?: string;
  rerank?: boolean;
  enable_graph?: boolean;
  metadata_filter?: Record<string, unknown>;
}

/**
 * Document information in chunk result
 */
export interface DocumentInfo {
  id: string;
  title?: string;
  filename?: string;
  metadata: Record<string, unknown>;
}

/**
 * Individual chunk result from retrieval
 */
export interface ChunkResult {
  chunk_id: string;
  content: string;
  chunk_index: number;
  score: number;
  metadata: Record<string, unknown>;
  chunk_metadata: Record<string, unknown>;
  document: DocumentInfo;
  collection_id: string;
}

/**
 * Response schema for retrieval endpoint
 */
export interface RetrievalResponse {
  query: string;
  mode: string;
  results: ChunkResult[];
  total_results: number;
  processing_time_ms: number;
  graph_enhanced: boolean;
  graph_context?: string;
}
