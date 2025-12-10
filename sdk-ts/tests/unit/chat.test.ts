/**
 * Unit tests for ChatResource
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MnemosyneClient } from '../../src/client.js';
import { createMockSSEResponse, createMockResponse } from '../setup.js';
import type { SSEEvent } from '../../src/streaming.js';

describe('ChatResource', () => {
  let client: MnemosyneClient;

  beforeEach(() => {
    client = new MnemosyneClient({
      apiKey: 'test_key',
      baseUrl: 'http://localhost:8000/api/v1',
    });
  });

  describe('chat', () => {
    it('should stream chat response', async () => {
      const chunks = ['Hello', ' world', '!'];
      global.fetch = vi.fn().mockResolvedValue(createMockSSEResponse(chunks));

      const receivedEvents: SSEEvent[] = [];

      for await (const event of client.chat.chat({
        message: 'Hi',
        stream: true,
      })) {
        receivedEvents.push(event as SSEEvent);
      }

      // Should receive delta events for each chunk + done event
      const deltaEvents = receivedEvents.filter(e => e.type === 'delta');
      expect(deltaEvents).toHaveLength(3);
      expect(deltaEvents.map(e => e.delta)).toEqual(chunks);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/chat',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('should handle non-streaming chat', async () => {
      const mockResponse = {
        query: 'Hi',
        response: 'Hello! How can I help you?',
        sources: [
          {
            chunk_id: 'chunk_1',
            document_id: 'doc_123',
            content: 'Source content',
            score: 0.95,
          },
        ],
        metadata: { model: 'gpt-4o-mini' },
      };

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockResponse));

      const responses: unknown[] = [];

      for await (const response of client.chat.chat({
        message: 'Hi',
        stream: false,
      })) {
        responses.push(response);
      }

      // Non-streaming returns done event with metadata
      expect(responses.length).toBe(1);
      expect(responses[0]).toHaveProperty('type', 'done');
    });

    it('should include collection_id in request', async () => {
      global.fetch = vi.fn().mockResolvedValue(createMockSSEResponse(['test']));

      for await (const _ of client.chat.chat({
        message: 'test',
        collection_id: 'coll_123',
        stream: true,
      })) {
        // Consume stream
      }

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('coll_123'),
        })
      );
    });

    it('should include session_id for multi-turn conversations', async () => {
      global.fetch = vi.fn().mockResolvedValue(createMockSSEResponse(['response']));

      for await (const _ of client.chat.chat({
        message: 'follow up question',
        session_id: 'session_123',
        stream: true,
      })) {
        // Consume stream
      }

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('session_123'),
        })
      );
    });

    it('should support preset configuration', async () => {
      global.fetch = vi.fn().mockResolvedValue(createMockSSEResponse(['test']));

      for await (const _ of client.chat.chat({
        message: 'test',
        preset: 'research',
        stream: true,
      })) {
        // Consume stream
      }

      expect(global.fetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          body: expect.stringContaining('"preset":"research"'),
        })
      );
    });
  });

  describe('listSessions', () => {
    it('should list chat sessions', async () => {
      const mockSessions = [
        {
          id: 'session_1',
          user_id: 'user_123',
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-01-15T10:30:00Z',
          message_count: 5,
        },
        {
          id: 'session_2',
          user_id: 'user_123',
          created_at: '2024-01-16T10:00:00Z',
          updated_at: '2024-01-16T10:15:00Z',
          message_count: 3,
        },
      ];

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockSessions));

      const result = await client.chat.listSessions();

      expect(result).toEqual(mockSessions);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/chat/sessions?limit=20&offset=0',
        expect.any(Object)
      );
    });

    it('should list sessions with custom limit', async () => {
      global.fetch = vi.fn().mockResolvedValue(createMockResponse([]));

      await client.chat.listSessions({ limit: 20 });

      expect(global.fetch).toHaveBeenCalledWith(
        expect.stringContaining('limit=20'),
        expect.any(Object)
      );
    });
  });

  describe('getSessionMessages', () => {
    it('should get messages for a session', async () => {
      const mockMessages = [
        {
          id: 'msg_1',
          session_id: 'session_123',
          role: 'user' as const,
          content: 'What is RAG?',
          created_at: '2024-01-15T10:00:00Z',
        },
        {
          id: 'msg_2',
          session_id: 'session_123',
          role: 'assistant' as const,
          content: 'RAG stands for Retrieval-Augmented Generation...',
          created_at: '2024-01-15T10:00:05Z',
        },
      ];

      global.fetch = vi.fn().mockResolvedValue(createMockResponse(mockMessages));

      const result = await client.chat.getSessionMessages('session_123');

      expect(result).toEqual(mockMessages);
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/chat/sessions/session_123/messages',
        expect.any(Object)
      );
    });
  });

  describe('deleteSession', () => {
    it('should delete a session', async () => {
      // Delete returns 204 No Content (void)
      global.fetch = vi.fn().mockResolvedValue(createMockResponse(null));

      const result = await client.chat.deleteSession('session_123');

      expect(result).toBeUndefined();
      expect(global.fetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1/chat/sessions/session_123',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });
  });
});
