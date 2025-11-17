/**
 * Retrievals resource implementation
 */

import { BaseClient } from '../base-client.js';
import type { RetrievalMode, RetrievalRequest, RetrievalResponse } from '../types/retrievals.js';

/**
 * Retrievals resource for searching across documents
 */
export class RetrievalsResource {
  constructor(private client: BaseClient) {}

  /**
   * Retrieve relevant chunks using various search modes
   *
   * @param params - Retrieval parameters
   * @returns Search results with chunks, scores, and optional graph context
   * @throws {ValidationError} Invalid query or parameters
   * @throws {APIError} Search failed
   *
   * @example
   * ```typescript
   * // Standard hybrid search
   * const results = await client.retrievals.retrieve({
   *   query: 'What is RAG?',
   *   mode: 'hybrid',
   *   top_k: 10
   * });
   *
   * // HybridRAG: Combine semantic search with knowledge graph
   * const results = await client.retrievals.retrieve({
   *   query: 'How do proteins interact with diseases?',
   *   mode: 'semantic',
   *   enable_graph: true,
   *   top_k: 5
   * });
   * console.log(results.graph_context);
   * ```
   */
  async retrieve(params: {
    query: string;
    mode?: RetrievalMode;
    top_k?: number;
    collection_id?: string;
    rerank?: boolean;
    enable_graph?: boolean;
    metadata_filter?: Record<string, unknown>;
  }): Promise<RetrievalResponse> {
    const request: RetrievalRequest = {
      query: params.query,
      mode: params.mode || 'hybrid',
      top_k: params.top_k || 10,
      collection_id: params.collection_id,
      rerank: params.rerank || false,
      enable_graph: params.enable_graph || false,
      metadata_filter: params.metadata_filter,
    };

    return this.client.request<RetrievalResponse>('POST', 'retrievals', { json: request });
  }
}
