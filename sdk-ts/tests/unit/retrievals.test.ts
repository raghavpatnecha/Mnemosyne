/**
 * Unit tests for RetrievalsResource
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MnemosyneClient } from '../../src/client.js';
import { createMockResponse } from '../setup.js';
import type { RetrievalResult } from '../../src/types/retrievals.js';

describe('RetrievalsResource', () => {
  let client: MnemosyneClient;

  beforeEach(() => {
    client = new MnemosyneClient({
      apiKey: 'test_key',
      baseUrl: 'http://localhost:8000/api/v1',
    });
  });

  describe('retrieve', () => {
    it('should perform semantic search', async () => {
      const mockResult: RetrievalResult = {
        results: [
          {
            chunk_id: 'chunk_1',
            document_id: 'doc_123',
            content: 'Test content about machine learning',
            score: 0.95,
            document: {
              id: 'doc_123',
              title: 'ML Paper',
              metadata: { year: 2024 },
            },
          },
        ],
        mode: 'semantic',
        processing_time_ms: 42.5,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResult));

      const result = await client.retrievals.retrieve({
        query: 'What is machine learning?',
        mode: 'semantic',
        top_k: 5,
      });

      expect(result).toEqual(mockResult);
      expect(result.mode).toBe('semantic');
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/retrievals',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('should perform keyword search', async () => {
      const mockResult: RetrievalResult = {
        results: [],
        mode: 'keyword',
        processing_time_ms: 15.3,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResult));

      const result = await client.retrievals.retrieve({
        query: 'neural networks',
        mode: 'keyword',
      });

      expect(result.mode).toBe('keyword');
    });

    it('should perform hybrid search', async () => {
      const mockResult: RetrievalResult = {
        results: [],
        mode: 'hybrid',
        processing_time_ms: 58.7,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResult));

      const result = await client.retrievals.retrieve({
        query: 'transformers',
        mode: 'hybrid',
        top_k: 10,
      });

      expect(result.mode).toBe('hybrid');
    });

    it('should perform hierarchical search', async () => {
      const mockResult: RetrievalResult = {
        results: [],
        mode: 'hierarchical',
        processing_time_ms: 102.1,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResult));

      const result = await client.retrievals.retrieve({
        query: 'deep learning',
        mode: 'hierarchical',
      });

      expect(result.mode).toBe('hierarchical');
    });

    it('should perform graph search', async () => {
      const mockResult: RetrievalResult = {
        results: [],
        mode: 'graph',
        processing_time_ms: 205.8,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResult));

      const result = await client.retrievals.retrieve({
        query: 'AI concepts',
        mode: 'graph',
      });

      expect(result.mode).toBe('graph');
    });

    it('should filter by collection_id', async () => {
      const mockResult: RetrievalResult = {
        results: [],
        mode: 'semantic',
        processing_time_ms: 30.0,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResult));

      await client.retrievals.retrieve({
        query: 'test',
        collection_id: 'coll_123',
      });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('coll_123'),
        })
      );
    });

    it('should enable reranking', async () => {
      const mockResult: RetrievalResult = {
        results: [],
        mode: 'hybrid',
        processing_time_ms: 85.2,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResult));

      await client.retrievals.retrieve({
        query: 'test',
        mode: 'hybrid',
        rerank: true,
      });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"rerank":true'),
        })
      );
    });

    it('should enable graph enhancement (HybridRAG)', async () => {
      const mockResult: RetrievalResult = {
        results: [],
        mode: 'hybrid',
        processing_time_ms: 150.0,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResult));

      await client.retrievals.retrieve({
        query: 'test',
        mode: 'hybrid',
        enable_graph: true,
      });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"enable_graph":true'),
        })
      );
    });

    it('should include processing time in results', async () => {
      const mockResult: RetrievalResult = {
        results: [
          {
            chunk_id: 'chunk_1',
            document_id: 'doc_123',
            content: 'Test',
            score: 0.9,
            document: {
              id: 'doc_123',
              title: 'Test Doc',
              metadata: {},
            },
          },
        ],
        mode: 'semantic',
        processing_time_ms: 123.45,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResult));

      const result = await client.retrievals.retrieve({
        query: 'test',
      });

      expect(result.processing_time_ms).toBe(123.45);
      expect(typeof result.processing_time_ms).toBe('number');
    });
  });
});
