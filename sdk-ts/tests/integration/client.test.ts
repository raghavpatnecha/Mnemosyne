/**
 * Integration tests for MnemosyneClient
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MnemosyneClient } from '../../src/client.js';
import { createMockResponse, createMockSSEResponse } from '../setup.js';

describe('MnemosyneClient Integration', () => {
  let client: MnemosyneClient;

  beforeEach(() => {
    client = new MnemosyneClient({
      apiKey: 'test_key',
      baseUrl: 'http://localhost:8000/api/v1',
    });
  });

  describe('full workflow', () => {
    it('should complete full ingestion and retrieval workflow', async () => {
      // Step 1: Create collection
      const mockCollection = {
        id: 'coll_test',
        user_id: 'user_test',
        name: 'Test Collection',
        description: null,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
        metadata: {},
        document_count: 0,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockCollection));

      const collection = await client.collections.create({
        name: 'Test Collection',
      });

      expect(collection.id).toBe('coll_test');

      // Step 2: Upload document
      const mockDocument = {
        id: 'doc_test',
        collection_id: 'coll_test',
        user_id: 'user_test',
        title: 'test.pdf',
        content_hash: 'hash',
        unique_identifier_hash: 'unique',
        content_type: 'application/pdf',
        size_bytes: 1024,
        metadata: {},
        created_at: '2024-01-15T10:01:00Z',
        updated_at: '2024-01-15T10:01:00Z',
        processing_info: {
          status: 'pending' as const,
          chunk_count: 0,
          total_tokens: 0,
        },
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockDocument));

      const file = new File(['test content'], 'test.pdf');
      const document = await client.documents.create('coll_test', file);

      expect(document.id).toBe('doc_test');

      // Step 3: Check processing status
      const mockStatus = {
        document_id: 'doc_test',
        status: 'completed' as const,
        chunk_count: 10,
        total_tokens: 2000,
        error_message: null,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockStatus));

      const status = await client.documents.getStatus('doc_test');

      expect(status.status).toBe('completed');
      expect(status.chunk_count).toBe(10);

      // Step 4: Perform retrieval
      const mockRetrieval = {
        results: [
          {
            chunk_id: 'chunk_1',
            document_id: 'doc_test',
            content: 'Test content',
            score: 0.95,
            document: {
              id: 'doc_test',
              title: 'test.pdf',
              metadata: {},
            },
          },
        ],
        mode: 'hybrid' as const,
        processing_time_ms: 45.2,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockRetrieval));

      const results = await client.retrievals.retrieve({
        query: 'test query',
        mode: 'hybrid',
        collection_id: 'coll_test',
      });

      expect(results.results).toHaveLength(1);
      expect(results.mode).toBe('hybrid');

      // Step 5: Chat with streaming
      global.fetch = vi
        .fn()
        .mockResolvedValue(createMockSSEResponse(['Based', ' on', ' the', ' documents']));

      const events: unknown[] = [];

      for await (const event of client.chat.chat({
        message: 'What does this document say?',
        collection_id: 'coll_test',
        stream: true,
      })) {
        events.push(event);
      }

      // Filter delta events and extract content
      const deltaEvents = events.filter((e: unknown) => (e as { type: string }).type === 'delta');
      const deltas = deltaEvents.map((e: unknown) => (e as { delta: string }).delta);
      expect(deltas).toEqual(['Based', ' on', ' the', ' documents']);

      // Step 6: Clean up (create new mocks for each call to avoid body reuse)
      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ success: true }));
      await client.documents.delete('doc_test');

      global.fetch = vi.fn().mockResolvedValueOnce(createMockResponse({ success: true }));
      await client.collections.delete('coll_test');
    });
  });

  describe('error handling', () => {
    it('should handle authentication errors gracefully', async () => {
      global.fetch = vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ detail: 'Invalid API key' }), {
          status: 401,
        })
      );

      await expect(client.collections.list()).rejects.toThrow('Invalid API key');
    });

    it('should handle network errors', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(client.collections.list()).rejects.toThrow('Network error');
    });

    // Timeout test is complex to mock properly with AbortController, skipping for now
  });

  describe('resource initialization', () => {
    it('should initialize all resources', () => {
      expect(client.auth).toBeDefined();
      expect(client.collections).toBeDefined();
      expect(client.documents).toBeDefined();
      expect(client.retrievals).toBeDefined();
      expect(client.chat).toBeDefined();
    });

    it('should share client configuration across resources', () => {
      expect(client.collections['client'].apiKey).toBe('test_key');
      expect(client.documents['client'].baseUrl).toBe('http://localhost:8000/api/v1');
      expect(client.chat['client'].timeout).toBe(60000); // Default is 60s
    });
  });
});
