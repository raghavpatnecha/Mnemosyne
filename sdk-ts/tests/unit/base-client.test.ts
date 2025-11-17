/**
 * Unit tests for BaseClient
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { BaseClient } from '../../src/base-client.js';
import {
  MnemosyneError,
  AuthenticationError,
  NotFoundError,
  RateLimitError,
  APIError,
} from '../../src/exceptions.js';
import { createMockResponse, createMockErrorResponse } from '../setup.js';

describe('BaseClient', () => {
  let client: BaseClient;

  beforeEach(() => {
    client = new BaseClient({
      apiKey: 'test_key',
      baseUrl: 'http://localhost:8000',
    });
  });

  describe('constructor', () => {
    it('should initialize with provided config', () => {
      expect(client.apiKey).toBe('test_key');
      expect(client.baseUrl).toBe('http://localhost:8000');
      expect(client.timeout).toBe(60000); // Default is 60s, not 30s
      expect(client.maxRetries).toBe(3);
    });

    it('should use environment variables as fallback', () => {
      process.env.MNEMOSYNE_API_KEY = 'env_key';
      process.env.MNEMOSYNE_BASE_URL = 'http://env:9000';

      const envClient = new BaseClient({});

      expect(envClient.apiKey).toBe('env_key');
      expect(envClient.baseUrl).toBe('http://env:9000');
    });

    it('should remove trailing slash from baseUrl', () => {
      const slashClient = new BaseClient({
        apiKey: 'key',
        baseUrl: 'http://localhost:8000/',
      });

      expect(slashClient.baseUrl).toBe('http://localhost:8000');
    });

    it('should throw if no API key provided', () => {
      delete process.env.MNEMOSYNE_API_KEY;

      expect(() => new BaseClient({})).toThrow(Error);
      expect(() => new BaseClient({})).toThrow('API key is required');
    });
  });

  describe('request', () => {
    it('should make successful GET request', async () => {
      const mockData = { id: '123', name: 'Test' };
      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockData));

      const result = await client.request('GET', '/test');

      expect(result).toEqual(mockData);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            Authorization: 'Bearer test_key',
          }),
        })
      );
    });

    it('should make successful POST request with JSON body', async () => {
      const mockData = { success: true };
      const requestBody = { name: 'New Item' };
      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockData));

      const result = await client.request('POST', '/test', { json: requestBody });

      expect(result).toEqual(mockData);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/test',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: JSON.stringify(requestBody),
        })
      );
    });

    it('should skip auth header when skipAuth is true', async () => {
      global.fetch = vi.fn().mockResolvedValue(createMockResponse({}));

      await client.request('POST', '/auth/register', {}, true);

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.not.objectContaining({
            Authorization: expect.any(String),
          }),
        })
      );
    });

    it('should throw AuthenticationError on 401', async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(createMockErrorResponse('Unauthorized', 401));

      await expect(client.request('GET', '/test')).rejects.toThrow(AuthenticationError);
    });

    it('should throw NotFoundError on 404', async () => {
      global.fetch = vi.fn().mockResolvedValue(createMockErrorResponse('Not found', 404));

      await expect(client.request('GET', '/test')).rejects.toThrow(NotFoundError);
    });

    it('should retry and eventually succeed on 429', async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValueOnce(createMockErrorResponse('Rate limit exceeded', 429))
        .mockResolvedValueOnce(createMockResponse({ success: true }));

      const result = await client.request('GET', '/test');

      expect(result).toEqual({ success: true });
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should throw APIError on 500', async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValue(createMockErrorResponse('Server error', 500));

      await expect(client.request('GET', '/test')).rejects.toThrow(APIError);
    });
  });

  describe('retry logic', () => {
    it('should retry on 5xx errors', async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValueOnce(createMockErrorResponse('Server error', 500))
        .mockResolvedValueOnce(createMockErrorResponse('Server error', 500))
        .mockResolvedValueOnce(createMockResponse({ success: true }));

      const result = await client.request('GET', '/test');

      expect(result).toEqual({ success: true });
      expect(global.fetch).toHaveBeenCalledTimes(3);
    });

    it('should retry on 429 rate limit', async () => {
      global.fetch = vi
        .fn()
        .mockResolvedValueOnce(createMockErrorResponse('Rate limit', 429))
        .mockResolvedValueOnce(createMockResponse({ success: true }));

      const result = await client.request('GET', '/test');

      expect(result).toEqual({ success: true });
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should not retry on 4xx errors (except 429)', async () => {
      global.fetch = vi.fn().mockResolvedValue(createMockErrorResponse('Not found', 404));

      await expect(client.request('GET', '/test')).rejects.toThrow(NotFoundError);
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });

    it('should throw after max retries', async () => {
      const errorClient = new BaseClient({
        apiKey: 'key',
        maxRetries: 2, // 2 total attempts: 1 initial + 1 retry
      });

      global.fetch = vi.fn().mockResolvedValue(createMockErrorResponse('Error', 500));

      await expect(errorClient.request('GET', '/test')).rejects.toThrow(APIError);
      expect(global.fetch).toHaveBeenCalledTimes(2); // 1 initial + 1 retry
    });
  });

  describe('exponential backoff', () => {
    it('should use exponential backoff delays', async () => {
      vi.useFakeTimers();

      global.fetch = vi
        .fn()
        .mockResolvedValueOnce(createMockErrorResponse('Error', 500))
        .mockResolvedValueOnce(createMockErrorResponse('Error', 500))
        .mockResolvedValueOnce(createMockResponse({ success: true }));

      const promise = client.request('GET', '/test');

      // First retry after 2s
      await vi.advanceTimersByTimeAsync(2000);

      // Second retry after 4s
      await vi.advanceTimersByTimeAsync(4000);

      const result = await promise;

      expect(result).toEqual({ success: true });
      vi.useRealTimers();
    });

    it('should cap backoff at 16 seconds', async () => {
      vi.useFakeTimers();

      const manyRetriesClient = new BaseClient({
        apiKey: 'key',
        maxRetries: 10,
      });

      global.fetch = vi
        .fn()
        .mockResolvedValueOnce(createMockErrorResponse('Error', 500))
        .mockResolvedValueOnce(createMockErrorResponse('Error', 500))
        .mockResolvedValueOnce(createMockErrorResponse('Error', 500))
        .mockResolvedValueOnce(createMockErrorResponse('Error', 500))
        .mockResolvedValueOnce(createMockErrorResponse('Error', 500))
        .mockResolvedValueOnce(createMockResponse({ success: true }));

      const promise = manyRetriesClient.request('GET', '/test');

      await vi.advanceTimersByTimeAsync(2000); // 2^1
      await vi.advanceTimersByTimeAsync(4000); // 2^2
      await vi.advanceTimersByTimeAsync(8000); // 2^3
      await vi.advanceTimersByTimeAsync(16000); // 2^4 = 16 (capped)
      await vi.advanceTimersByTimeAsync(16000); // Should still be 16

      await promise;

      vi.useRealTimers();
    });
  });
});
