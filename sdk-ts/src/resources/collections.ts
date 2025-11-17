/**
 * Collections resource implementation
 */

import { BaseClient } from '../base-client.js';
import type {
  CollectionCreate,
  CollectionUpdate,
  CollectionResponse,
  CollectionListResponse,
} from '../types/collections.js';

/**
 * Collections resource for managing document collections
 */
export class CollectionsResource {
  constructor(private client: BaseClient) {}

  /**
   * Create a new collection
   *
   * @param params - Collection creation parameters
   * @returns Created collection with ID and timestamps
   * @throws {AuthenticationError} Invalid API key
   * @throws {ValidationError} Invalid parameters
   * @throws {APIError} Server error
   *
   * @example
   * ```typescript
   * const collection = await client.collections.create({
   *   name: 'Research Papers',
   *   description: 'AI/ML research papers',
   *   metadata: { domain: 'AI' }
   * });
   * ```
   */
  async create(params: CollectionCreate): Promise<CollectionResponse> {
    return this.client.request<CollectionResponse>('POST', 'collections', { json: params });
  }

  /**
   * List collections with pagination
   *
   * @param limit - Number of results per page (1-100, default: 20)
   * @param offset - Number of results to skip (default: 0)
   * @returns List of collections with pagination info
   *
   * @example
   * ```typescript
   * const response = await client.collections.list({ limit: 20, offset: 0 });
   * console.log(`Total: ${response.pagination.total}`);
   * ```
   */
  async list(params?: { limit?: number; offset?: number }): Promise<CollectionListResponse> {
    const queryParams = {
      limit: params?.limit || 20,
      offset: params?.offset || 0,
    };

    return this.client.request<CollectionListResponse>('GET', 'collections', {
      params: queryParams,
    });
  }

  /**
   * Get a collection by ID
   *
   * @param collectionId - Collection UUID
   * @returns Collection details
   * @throws {NotFoundError} Collection not found
   *
   * @example
   * ```typescript
   * const collection = await client.collections.get('collection-uuid');
   * ```
   */
  async get(collectionId: string): Promise<CollectionResponse> {
    return this.client.request<CollectionResponse>('GET', `/collections/${collectionId}`);
  }

  /**
   * Update a collection
   *
   * @param collectionId - Collection UUID
   * @param params - Fields to update
   * @returns Updated collection
   * @throws {NotFoundError} Collection not found
   * @throws {ValidationError} Invalid parameters
   *
   * @example
   * ```typescript
   * const updated = await client.collections.update('collection-uuid', {
   *   name: 'Updated Name',
   *   metadata: { new: 'data' }
   * });
   * ```
   */
  async update(collectionId: string, params: CollectionUpdate): Promise<CollectionResponse> {
    return this.client.request<CollectionResponse>('PATCH', `/collections/${collectionId}`, {
      json: params,
    });
  }

  /**
   * Delete a collection
   *
   * @param collectionId - Collection UUID
   * @throws {NotFoundError} Collection not found
   *
   * @example
   * ```typescript
   * await client.collections.delete('collection-uuid');
   * ```
   */
  async delete(collectionId: string): Promise<void> {
    await this.client.request<void>('DELETE', `/collections/${collectionId}`);
  }
}
