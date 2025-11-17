/**
 * Unit tests for CollectionsResource
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MnemosyneClient } from '../../src/client.js';
import { createMockResponse } from '../setup.js';
import type { Collection } from '../../src/types/collections.js';

describe('CollectionsResource', () => {
  let client: MnemosyneClient;

  beforeEach(() => {
    client = new MnemosyneClient({
      apiKey: 'test_key',
      baseUrl: 'http://localhost:8000/api/v1',
    });
  });

  describe('create', () => {
    it('should create collection with required fields only', async () => {
      const mockCollection: Collection = {
        id: 'coll_123',
        user_id: 'user_123',
        name: 'Test Collection',
        description: null,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
        metadata: {},
        document_count: 0,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockCollection));

      const result = await client.collections.create({
        name: 'Test Collection',
      });

      expect(result).toEqual(mockCollection);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/collections',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ name: 'Test Collection' }),
        })
      );
    });

    it('should create collection with all fields', async () => {
      const mockCollection: Collection = {
        id: 'coll_123',
        user_id: 'user_123',
        name: 'Research Papers',
        description: 'AI/ML research papers',
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
        metadata: { domain: 'ai', year: 2024 },
        document_count: 0,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockCollection));

      const result = await client.collections.create({
        name: 'Research Papers',
        description: 'AI/ML research papers',
        metadata: { domain: 'ai', year: 2024 },
      });

      expect(result).toEqual(mockCollection);
    });
  });

  describe('list', () => {
    it('should list collections with default pagination', async () => {
      const mockResponse = {
        data: [
          {
            id: 'coll_1',
            user_id: 'user_123',
            name: 'Collection 1',
            description: null,
            created_at: '2024-01-15T10:00:00Z',
            updated_at: '2024-01-15T10:00:00Z',
            metadata: {},
            document_count: 5,
          },
        ],
        total: 1,
        page: 1,
        page_size: 10,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResponse));

      const result = await client.collections.list();

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/collections?page=1&page_size=10',
        expect.any(Object)
      );
    });

    it('should list collections with custom pagination', async () => {
      global.fetch = vi.fn().mockResolvedValue(createMockResponse({ data: [], total: 0 }));

      await client.collections.list({ page: 2, page_size: 20 });

      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/collections?page=2&page_size=20',
        expect.any(Object)
      );
    });
  });

  describe('get', () => {
    it('should get collection by ID', async () => {
      const mockCollection: Collection = {
        id: 'coll_123',
        user_id: 'user_123',
        name: 'Test Collection',
        description: 'Test description',
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
        metadata: {},
        document_count: 10,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockCollection));

      const result = await client.collections.get('coll_123');

      expect(result).toEqual(mockCollection);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/collections/coll_123',
        expect.objectContaining({
          method: 'GET',
        })
      );
    });
  });

  describe('update', () => {
    it('should update collection name', async () => {
      const mockUpdated: Collection = {
        id: 'coll_123',
        user_id: 'user_123',
        name: 'Updated Name',
        description: null,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T11:00:00Z',
        metadata: {},
        document_count: 0,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockUpdated));

      const result = await client.collections.update('coll_123', {
        name: 'Updated Name',
      });

      expect(result).toEqual(mockUpdated);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/collections/coll_123',
        expect.objectContaining({
          method: 'PATCH',
          body: JSON.stringify({ name: 'Updated Name' }),
        })
      );
    });

    it('should update collection metadata', async () => {
      const mockUpdated: Collection = {
        id: 'coll_123',
        user_id: 'user_123',
        name: 'Test',
        description: null,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T11:00:00Z',
        metadata: { updated: true, count: 42 },
        document_count: 0,
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockUpdated));

      const result = await client.collections.update('coll_123', {
        metadata: { updated: true, count: 42 },
      });

      expect(result.metadata).toEqual({ updated: true, count: 42 });
    });
  });

  describe('delete', () => {
    it('should delete collection', async () => {
      const mockResponse = { success: true };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResponse));

      const result = await client.collections.delete('coll_123');

      expect(result).toEqual(mockResponse);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/collections/coll_123',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });
});
