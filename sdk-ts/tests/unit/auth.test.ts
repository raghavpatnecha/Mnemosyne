/**
 * Unit tests for AuthResource
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MnemosyneClient } from '../../src/client.js';
import { createMockResponse } from '../setup.js';

describe('AuthResource', () => {
  let client: MnemosyneClient;

  beforeEach(() => {
    client = new MnemosyneClient({
      apiKey: 'test_key',
      baseUrl: 'http://localhost:8000/api/v1',
    });
  });

  describe('register', () => {
    it('should register new user', async () => {
      const mockUser = {
        user_id: 'user_123',
        email: 'test@example.com',
        api_key: 'mn_test_key_123',
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockUser));

      const result = await client.auth.register('test@example.com', 'password123');

      expect(result).toEqual(mockUser);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/auth/register',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            email: 'test@example.com',
            password: 'password123',
          }),
        })
      );
    });

    it('should skip authentication for register endpoint', async () => {
      const mockUser = {
        user_id: 'user_123',
        email: 'test@example.com',
        api_key: 'mn_test_key',
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockUser));

      await client.auth.register('test@example.com', 'password');

      // Verify no Authorization header
      const callArgs = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      const headers = callArgs[1].headers as Record<string, string>;

      expect(headers['Authorization']).toBeUndefined();
    });
  });
});
