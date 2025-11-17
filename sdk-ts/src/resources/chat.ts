/**
 * Chat resource implementation
 */

import { BaseClient } from '../base-client.js';
import { parseSSEStream } from '../streaming.js';
import type {
  ChatRequest,
  ChatResponse,
  ChatSessionResponse,
  ChatMessageResponse,
} from '../types/chat.js';

/**
 * Chat resource for conversational AI with RAG
 */
export class ChatResource {
  constructor(private client: BaseClient) {}

  /**
   * Send a chat message and stream the response
   *
   * @param params - Chat parameters
   * @yields Response chunks from the assistant
   * @throws {ValidationError} Invalid message or parameters
   * @throws {APIError} Chat failed
   *
   * @example
   * ```typescript
   * // Streaming chat
   * for await (const chunk of client.chat.chat({
   *   message: 'What are transformers?',
   *   stream: true
   * })) {
   *   process.stdout.write(chunk);
   * }
   *
   * // Non-streaming
   * for await (const message of client.chat.chat({
   *   message: 'What are transformers?',
   *   stream: false
   * })) {
   *   console.log(message);
   * }
   * ```
   */
  async *chat(params: {
    message: string;
    session_id?: string;
    collection_id?: string;
    top_k?: number;
    stream?: boolean;
  }): AsyncGenerator<string, void, unknown> {
    const request: ChatRequest = {
      message: params.message,
      session_id: params.session_id,
      collection_id: params.collection_id,
      top_k: params.top_k || 5,
      stream: params.stream !== false, // Default to true
    };

    if (request.stream) {
      // Stream response using SSE
      const response = await this.client.requestStream('POST', '/chat', { json: request });

      for await (const chunk of parseSSEStream(response)) {
        yield chunk;
      }
    } else {
      // Non-streaming response
      const response = await this.client.request<ChatResponse>('POST', '/chat', { json: request });
      yield response.message;
    }
  }

  /**
   * List chat sessions with pagination
   *
   * @param params - Pagination parameters
   * @returns List of chat sessions
   *
   * @example
   * ```typescript
   * const sessions = await client.chat.listSessions({ limit: 20 });
   * ```
   */
  async listSessions(params?: { limit?: number; offset?: number }): Promise<ChatSessionResponse[]> {
    const queryParams = {
      limit: params?.limit || 20,
      offset: params?.offset || 0,
    };

    return this.client.request<ChatSessionResponse[]>('GET', '/chat/sessions', {
      params: queryParams,
    });
  }

  /**
   * Get all messages in a chat session
   *
   * @param sessionId - Session UUID
   * @returns List of messages in chronological order
   * @throws {NotFoundError} Session not found
   *
   * @example
   * ```typescript
   * const messages = await client.chat.getSessionMessages('session-uuid');
   * ```
   */
  async getSessionMessages(sessionId: string): Promise<ChatMessageResponse[]> {
    return this.client.request<ChatMessageResponse[]>(
      'GET',
      `/chat/sessions/${sessionId}/messages`
    );
  }

  /**
   * Delete a chat session and all its messages
   *
   * @param sessionId - Session UUID
   * @throws {NotFoundError} Session not found
   *
   * @example
   * ```typescript
   * await client.chat.deleteSession('session-uuid');
   * ```
   */
  async deleteSession(sessionId: string): Promise<void> {
    await this.client.request<void>('DELETE', `/chat/sessions/${sessionId}`);
  }
}
