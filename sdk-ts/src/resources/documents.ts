/**
 * Documents resource implementation
 */

import { BaseClient } from '../base-client.js';
import type {
  DocumentResponse,
  DocumentListResponse,
  DocumentStatusResponse,
  DocumentUpdate,
  ProcessingStatus,
} from '../types/documents.js';
import { readFile } from 'fs/promises';
import { basename } from 'path';

/**
 * Documents resource for managing documents in collections
 */
export class DocumentsResource {
  constructor(private client: BaseClient) {}

  /**
   * Upload a document to a collection.
   *
   * Supports file paths (Node.js) or File/Blob objects (browser).
   *
   * @param collectionId - Collection UUID
   * @param file - File path (string) or File/Blob object
   * @param metadata - Optional metadata dictionary
   * @returns Created document with processing status
   * @throws {NotFoundError} Collection not found
   * @throws {ValidationError} Invalid file or metadata
   * @throws {APIError} Upload failed
   *
   * @example
   * ```typescript
   * // Upload from file path
   * const doc = await client.documents.create(
   *   'collection-uuid',
   *   './paper.pdf',
   *   { topic: 'transformers' }
   * );
   *
   * // Upload from File object (browser)
   * const doc = await client.documents.create(
   *   'collection-uuid',
   *   fileInput.files[0],
   *   { topic: 'transformers' }
   * );
   * ```
   */
  async create(
    collectionId: string,
    file: string | File | Blob,
    metadata?: Record<string, unknown>
  ): Promise<DocumentResponse> {
    const formData = new FormData();

    // Handle file input
    if (typeof file === 'string') {
      // File path (Node.js)
      const fileBuffer = await readFile(file);
      const filename = basename(file);
      const blob = new Blob([fileBuffer]);
      formData.append('file', blob, filename);
    } else {
      // File or Blob object
      const filename = file instanceof File ? file.name : 'file';
      formData.append('file', file, filename);
    }

    // Add collection_id and metadata
    formData.append('collection_id', collectionId);
    formData.append('metadata', JSON.stringify(metadata || {}));

    // Make request with multipart/form-data
    // Note: We bypass the normal request() method because multipart/form-data
    // requires special handling (FormData body, no Content-Type header)
    const urlString = this.client.baseUrl + '/documents';
    const url = new URL(urlString);

    const headers = {
      Authorization: `Bearer ${this.client.apiKey}`,
    };

    const response = await fetch(url.toString(), {
      method: 'POST',
      headers,
      body: formData,
    });

    // Handle errors
    await this.client.handleErrorAsync(response);

    return (await response.json()) as DocumentResponse;
  }

  /**
   * List documents with pagination and filtering
   *
   * @param params - Query parameters
   * @returns List of documents with pagination info
   *
   * @example
   * ```typescript
   * const docs = await client.documents.list({
   *   collection_id: 'collection-uuid',
   *   status_filter: 'completed',
   *   limit: 20
   * });
   * ```
   */
  async list(params?: {
    collection_id?: string;
    limit?: number;
    offset?: number;
    status_filter?: ProcessingStatus;
  }): Promise<DocumentListResponse> {
    const queryParams: Record<string, string | number> = {
      limit: params?.limit || 20,
      offset: params?.offset || 0,
    };

    if (params?.collection_id) {
      queryParams.collection_id = params.collection_id;
    }

    if (params?.status_filter) {
      queryParams.status = params.status_filter;
    }

    return this.client.request<DocumentListResponse>('GET', '/documents', {
      params: queryParams,
    });
  }

  /**
   * Get a document by ID
   *
   * @param documentId - Document UUID
   * @returns Document details
   * @throws {NotFoundError} Document not found
   *
   * @example
   * ```typescript
   * const doc = await client.documents.get('document-uuid');
   * ```
   */
  async get(documentId: string): Promise<DocumentResponse> {
    return this.client.request<DocumentResponse>('GET', `/documents/${documentId}`);
  }

  /**
   * Get document processing status
   *
   * @param documentId - Document UUID
   * @returns Processing status with chunk/token counts
   * @throws {NotFoundError} Document not found
   *
   * @example
   * ```typescript
   * const status = await client.documents.getStatus('document-uuid');
   * console.log(`Status: ${status.status}`);
   * console.log(`Chunks: ${status.chunk_count}`);
   * ```
   */
  async getStatus(documentId: string): Promise<DocumentStatusResponse> {
    return this.client.request<DocumentStatusResponse>('GET', `/documents/${documentId}/status`);
  }

  /**
   * Update document metadata
   *
   * @param documentId - Document UUID
   * @param params - Fields to update
   * @returns Updated document
   * @throws {NotFoundError} Document not found
   * @throws {ValidationError} Invalid parameters
   *
   * @example
   * ```typescript
   * const updated = await client.documents.update('document-uuid', {
   *   title: 'New Title',
   *   metadata: { updated: true }
   * });
   * ```
   */
  async update(documentId: string, params: DocumentUpdate): Promise<DocumentResponse> {
    return this.client.request<DocumentResponse>('PATCH', `/documents/${documentId}`, {
      json: params,
    });
  }

  /**
   * Delete a document
   *
   * @param documentId - Document UUID
   * @throws {NotFoundError} Document not found
   *
   * @example
   * ```typescript
   * await client.documents.delete('document-uuid');
   * ```
   */
  async delete(documentId: string): Promise<void> {
    await this.client.request<void>('DELETE', `/documents/${documentId}`);
  }
}
