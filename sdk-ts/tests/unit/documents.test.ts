/**
 * Unit tests for DocumentsResource
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MnemosyneClient } from '../../src/client.js';
import { createMockResponse } from '../setup.js';
import type { Document } from '../../src/types/documents.js';

describe('DocumentsResource', () => {
  let client: MnemosyneClient;

  beforeEach(() => {
    client = new MnemosyneClient({
      apiKey: 'test_key',
      baseUrl: 'http://localhost:8000/api/v1',
    });
  });

  describe('create', () => {
    it('should upload file with File object', async () => {
      const mockDocument: Document = {
        id: 'doc_123',
        collection_id: 'coll_123',
        user_id: 'user_123',
        title: 'test.pdf',
        content_hash: 'hash_abc',
        unique_identifier_hash: 'unique_hash',
        content_type: 'application/pdf',
        size_bytes: 1024,
        metadata: {},
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
        processing_info: {
          status: 'pending',
          chunk_count: 0,
          total_tokens: 0,
        },
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockDocument));

      const file = new File(['test content'], 'test.pdf', { type: 'application/pdf' });
      const result = await client.documents.create('coll_123', file);

      expect(result).toEqual(mockDocument);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            Authorization: 'Bearer test_key',
          }),
        })
      );

      // Verify FormData was created
      const callArgs = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(callArgs[1].body).toBeInstanceOf(FormData);
    });

    // Skipping file path test due to fs mocking complexity in Vitest

    it('should upload file with metadata', async () => {
      const mockDocument: Document = {
        id: 'doc_123',
        collection_id: 'coll_123',
        user_id: 'user_123',
        title: 'paper.pdf',
        content_hash: 'hash_ghi',
        unique_identifier_hash: 'unique_hash_3',
        content_type: 'application/pdf',
        size_bytes: 3072,
        metadata: { author: 'John Doe', year: 2024 },
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
        processing_info: {
          status: 'pending',
          chunk_count: 0,
          total_tokens: 0,
        },
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockDocument));

      const file = new File(['test'], 'paper.pdf');
      const result = await client.documents.create('coll_123', file, {
        author: 'John Doe',
        year: 2024,
      });

      expect(result.metadata).toEqual({ author: 'John Doe', year: 2024 });
    });
  });

  describe('list', () => {
    it('should list documents with collection_id filter', async () => {
      const mockResponse = {
        data: [
          {
            id: 'doc_1',
            collection_id: 'coll_123',
            user_id: 'user_123',
            title: 'Doc 1',
            content_hash: 'hash_1',
            unique_identifier_hash: 'unique_1',
            content_type: 'application/pdf',
            size_bytes: 1024,
            metadata: {},
            created_at: '2024-01-15T10:00:00Z',
            updated_at: '2024-01-15T10:00:00Z',
            processing_info: {
              status: 'completed' as const,
              chunk_count: 5,
              total_tokens: 1000,
            },
          },
        ],
        total: 1,
        page: 1,
        page_size: 10,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResponse));

      const result = await client.documents.list({
        collection_id: 'coll_123',
      });

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('collection_id=coll_123'),
        expect.any(Object)
      );
    });

    it('should list documents with status filter', async () => {
      global.fetch = vi.fn().mockResolvedValue(createMockResponse({ data: [], total: 0 }));

      await client.documents.list({
        status_filter: 'completed',
      });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('status_filter=completed'),
        expect.any(Object)
      );
    });

    it('should list documents with pagination', async () => {
      global.fetch = vi.fn().mockResolvedValue(createMockResponse({ data: [], total: 0 }));

      await client.documents.list({
        page: 2,
        page_size: 20,
      });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('page=2'),
        expect.any(Object)
      );
      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('page_size=20'),
        expect.any(Object)
      );
    });
  });

  describe('get', () => {
    it('should get document by ID', async () => {
      const mockDocument: Document = {
        id: 'doc_123',
        collection_id: 'coll_123',
        user_id: 'user_123',
        title: 'Test Document',
        content_hash: 'hash_abc',
        unique_identifier_hash: 'unique_hash',
        content_type: 'application/pdf',
        size_bytes: 1024,
        metadata: { author: 'Test' },
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
        processing_info: {
          status: 'completed',
          chunk_count: 10,
          total_tokens: 2000,
        },
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockDocument));

      const result = await client.documents.get('doc_123');

      expect(result).toEqual(mockDocument);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/doc_123',
        expect.any(Object)
      );
    });
  });

  describe('getStatus', () => {
    it('should get processing status', async () => {
      const mockStatus = {
        document_id: 'doc_123',
        status: 'completed' as const,
        chunk_count: 15,
        total_tokens: 3000,
        error_message: null,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockStatus));

      const result = await client.documents.getStatus('doc_123');

      expect(result).toEqual(mockStatus);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/doc_123/status',
        expect.any(Object)
      );
    });

    it('should get failed status with error message', async () => {
      const mockStatus = {
        document_id: 'doc_456',
        status: 'failed' as const,
        chunk_count: 0,
        total_tokens: 0,
        error_message: 'Failed to parse PDF',
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockStatus));

      const result = await client.documents.getStatus('doc_456');

      expect(result.status).toBe('failed');
      expect(result.error_message).toBe('Failed to parse PDF');
    });
  });

  describe('delete', () => {
    it('should delete document', async () => {
      const mockResponse = { success: true };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResponse));

      const result = await client.documents.delete('doc_123');

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/documents/doc_123',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });
});
