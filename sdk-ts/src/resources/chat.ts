/**
 * Chat resource implementation
 */

import { BaseClient } from '../base-client.js';
import { parseSSEStream, SSEEvent } from '../streaming.js';
import type {
  ChatRequest,
  ChatCompletionResponse,
  ChatSessionResponse,
  ChatMessageResponse,
  RetrievalConfig,
  GenerationConfig,
  StreamChunk,
  ChatPreset,
  ReasoningMode,
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
   * @yields SSE events (delta, sources, usage, done, error, reasoning_step, sub_query)
   * @throws {ValidationError} Invalid message or parameters
   * @throws {APIError} Chat failed
   *
   * @example
   * ```typescript
   * // Streaming chat with preset
   * for await (const event of client.chat.chat({
   *   message: 'What are transformers?',
   *   preset: 'research',
   *   stream: true
   * })) {
   *   if (event.type === 'delta') {
   *     process.stdout.write(event.content);
   *   } else if (event.type === 'sources') {
   *     console.log('Sources:', event.sources);
   *   }
   * }
   *
   * // Deep reasoning mode
   * for await (const event of client.chat.chat({
   *   message: 'Compare RAG architectures',
   *   reasoning_mode: 'deep',
   *   model: 'gpt-4o'
   * })) {
   *   if (event.type === 'reasoning_step') {
   *     console.log(`Step ${event.step}: ${event.description}`);
   *   } else if (event.type === 'sub_query') {
   *     console.log(`  Searching: ${event.query}`);
   *   } else if (event.type === 'delta') {
   *     process.stdout.write(event.content);
   *   }
   * }
   * ```
   */
  async *chat(params: {
    message?: string;
    messages?: Array<{ role: string; content: string }>;
    session_id?: string;
    collection_id?: string;
    retrieval?: RetrievalConfig;
    generation?: GenerationConfig;
    stream?: boolean;
    /** LLM model override (e.g., 'gpt-4o', 'claude-3-opus') */
    model?: string;
    /** Answer style preset */
    preset?: ChatPreset;
    /** Reasoning mode: 'standard' (single-pass) or 'deep' (multi-step iterative) */
    reasoning_mode?: ReasoningMode;
    /** Temperature override (0.0-2.0) */
    temperature?: number;
    /** Max tokens override */
    max_tokens?: number;
    /** Custom instruction to append to the prompt (e.g., 'focus on security aspects', 'generate 10 MCQs') */
    custom_instruction?: string;
    /** Whether this is a follow-up to a previous question. When true, previous context is preserved. */
    is_follow_up?: boolean;
  }): AsyncGenerator<SSEEvent | StreamChunk, void, unknown> {
    const request: ChatRequest = {
      message: params.message,
      messages: params.messages?.map(m => ({ role: m.role as 'system' | 'user' | 'assistant', content: m.content })),
      session_id: params.session_id,
      collection_id: params.collection_id,
      retrieval: params.retrieval,
      generation: params.generation,
      stream: params.stream !== false, // Default to true
      model: params.model,
      preset: params.preset ?? 'detailed',
      reasoning_mode: params.reasoning_mode ?? 'standard',
      temperature: params.temperature,
      max_tokens: params.max_tokens,
      custom_instruction: params.custom_instruction,
      is_follow_up: params.is_follow_up ?? false,
    };

    if (request.stream) {
      // Stream response using SSE
      const response = await this.client.requestStream('POST', '/chat', { json: request });

      for await (const event of parseSSEStream(response)) {
        yield event;
      }
    } else {
      // Non-streaming response - use chatComplete instead
      const response = await this.client.request<ChatCompletionResponse>('POST', '/chat', { json: request });
      yield { type: 'done', metadata: response.metadata } as StreamChunk;
    }
  }

  /**
   * Send a chat message and get complete response (non-streaming)
   *
   * @param params - Chat parameters
   * @returns Complete chat response with sources and metadata
   *
   * @example
   * ```typescript
   * const response = await client.chat.chatComplete({
   *   message: 'What are transformers?',
   *   preset: 'research',
   *   model: 'gpt-4o'
   * });
   * console.log(response.response);
   * console.log('Sources:', response.sources);
   * ```
   */
  async chatComplete(params: {
    message?: string;
    messages?: Array<{ role: string; content: string }>;
    session_id?: string;
    collection_id?: string;
    retrieval?: RetrievalConfig;
    generation?: GenerationConfig;
    /** LLM model override (e.g., 'gpt-4o', 'claude-3-opus') */
    model?: string;
    /** Answer style preset */
    preset?: ChatPreset;
    /** Reasoning mode: 'standard' (single-pass) or 'deep' (multi-step iterative) */
    reasoning_mode?: ReasoningMode;
    /** Temperature override (0.0-2.0) */
    temperature?: number;
    /** Max tokens override */
    max_tokens?: number;
    /** Custom instruction to append to the prompt (e.g., 'focus on security aspects', 'generate 10 MCQs') */
    custom_instruction?: string;
    /** Whether this is a follow-up to a previous question. When true, previous context is preserved. */
    is_follow_up?: boolean;
  }): Promise<ChatCompletionResponse> {
    const request: ChatRequest = {
      message: params.message,
      messages: params.messages?.map(m => ({ role: m.role as 'system' | 'user' | 'assistant', content: m.content })),
      session_id: params.session_id,
      collection_id: params.collection_id,
      retrieval: params.retrieval,
      generation: params.generation,
      stream: false,
      model: params.model,
      preset: params.preset ?? 'detailed',
      reasoning_mode: params.reasoning_mode ?? 'standard',
      temperature: params.temperature,
      max_tokens: params.max_tokens,
      custom_instruction: params.custom_instruction,
      is_follow_up: params.is_follow_up ?? false,
    };

    return this.client.request<ChatCompletionResponse>('POST', '/chat', { json: request });
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
