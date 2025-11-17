/**
 * Main Mnemosyne SDK client
 */

import { BaseClient, BaseClientConfig } from './base-client.js';
import {
  AuthResource,
  CollectionsResource,
  DocumentsResource,
  RetrievalsResource,
  ChatResource,
} from './resources/index.js';

/**
 * Mnemosyne SDK client for interacting with the RAG API.
 *
 * Provides access to all Mnemosyne API resources with automatic
 * retry logic, error handling, and streaming support.
 *
 * @example
 * ```typescript
 * // Initialize client
 * const client = new MnemosyneClient({
 *   apiKey: 'mn_...',
 *   baseUrl: 'http://localhost:8000/api/v1'  // Must include /api/v1
 * });
 *
 * // Create collection
 * const collection = await client.collections.create({
 *   name: 'Research Papers'
 * });
 *
 * // Upload document
 * const doc = await client.documents.create(
 *   collection.id,
 *   './paper.pdf',
 *   { topic: 'AI' }
 * );
 *
 * // Search with hybrid mode
 * const results = await client.retrievals.retrieve({
 *   query: 'What are transformers?',
 *   mode: 'hybrid',
 *   top_k: 10
 * });
 *
 * // Stream chat response
 * for await (const chunk of client.chat.chat({
 *   message: 'Explain transformers',
 *   stream: true
 * })) {
 *   process.stdout.write(chunk);
 * }
 * ```
 */
export class MnemosyneClient extends BaseClient {
  /** Auth resource for user registration */
  public readonly auth: AuthResource;

  /** Collections resource for managing document collections */
  public readonly collections: CollectionsResource;

  /** Documents resource for uploading and managing documents */
  public readonly documents: DocumentsResource;

  /** Retrievals resource for searching across documents (5 modes) */
  public readonly retrievals: RetrievalsResource;

  /** Chat resource for conversational AI with RAG */
  public readonly chat: ChatResource;

  /**
   * Create a new Mnemosyne client
   *
   * @param config - Client configuration
   *
   * @example
   * ```typescript
   * const client = new MnemosyneClient({
   *   apiKey: 'mn_...',
   *   baseUrl: 'http://localhost:8000/api/v1',  // Must include /api/v1
   *   timeout: 120000,  // 120 seconds in milliseconds
   *   maxRetries: 5
   * });
   * ```
   */
  constructor(config: BaseClientConfig = {}) {
    super(config);

    // Initialize all resource instances
    this.auth = new AuthResource(this);
    this.collections = new CollectionsResource(this);
    this.documents = new DocumentsResource(this);
    this.retrievals = new RetrievalsResource(this);
    this.chat = new ChatResource(this);
  }
}

// Export as default
export default MnemosyneClient;
