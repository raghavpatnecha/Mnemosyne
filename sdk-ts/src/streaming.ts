/**
 * Server-Sent Events (SSE) streaming utilities
 */

import type { SourceReference, MediaItem, FollowUpQuestion, UsageStats, ChatMetadata } from './types/chat.js';

/**
 * SSE event type union
 */
export type SSEEventType =
  | 'delta'
  | 'sources'
  | 'media'
  | 'follow_up'
  | 'usage'
  | 'done'
  | 'error'
  | 'reasoning_step'
  | 'sub_query';

/**
 * SSE event types from the backend
 */
export interface SSEEvent {
  type: SSEEventType;
  /** Text content for delta events */
  delta?: string;
  /** Retrieved sources for sources events */
  sources?: SourceReference[];
  /** Media items (images, tables, figures) for media events */
  media?: MediaItem[];
  /** Suggested follow-up questions for follow_up events */
  follow_up_questions?: FollowUpQuestion[];
  /** Token usage statistics for usage events */
  usage?: UsageStats;
  /** Response metadata for done events */
  metadata?: ChatMetadata;
  /** Stream completion flag for done events */
  done?: boolean;
  /** Session ID for done events */
  session_id?: string;
  /** Error message for error events */
  error?: string;
  /** Reasoning step number (1-3) for reasoning_step events in deep mode */
  step?: number;
  /** Reasoning step description for reasoning_step events */
  description?: string;
  /** Sub-query text for sub_query events in deep mode */
  query?: string;
}

/**
 * Parse Server-Sent Events from a streaming response.
 *
 * Automatically parses JSON events and yields structured objects.
 * Event types: delta, sources, media, follow_up, usage, done, error, reasoning_step, sub_query
 *
 * @param response - Fetch Response object with streaming body
 * @yields Parsed SSE event objects
 *
 * @example
 * ```typescript
 * const response = await fetch('/chat', { ... });
 * for await (const event of parseSSEStream(response)) {
 *   switch (event.type) {
 *     case 'delta':
 *       process.stdout.write(event.delta);
 *       break;
 *     case 'sources':
 *       console.log('Sources:', event.sources);
 *       break;
 *     case 'reasoning_step':
 *       console.log(`Step ${event.step}: ${event.description}`);
 *       break;
 *     case 'sub_query':
 *       console.log(`  Searching: ${event.query}`);
 *       break;
 *     case 'done':
 *       console.log('Session ID:', event.session_id);
 *       break;
 *   }
 * }
 * ```
 */
export async function* parseSSEStream(response: Response): AsyncGenerator<SSEEvent, void, unknown> {
  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
      const result = await reader.read();

      // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access
      if (result.done) {
        break;
      }

      // Decode chunk and add to buffer
      // eslint-disable-next-line @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-unsafe-argument
      buffer += decoder.decode(result.value, { stream: true });

      // Process complete lines
      const lines = buffer.split('\n');
      // Keep incomplete line in buffer
      const lastLine = lines.pop();
      buffer = lastLine !== undefined ? lastLine : '';

      for (const line of lines) {
        const trimmedLine = line.trim();

        // Parse SSE format: "data: <content>"
        if (trimmedLine.startsWith('data: ')) {
          const data = trimmedLine.slice(6); // Remove "data: " prefix

          try {
            const event = JSON.parse(data) as SSEEvent;
            yield event;

            // Stop on done event
            if (event.type === 'done') {
              return;
            }
          } catch {
            // Ignore malformed JSON
            continue;
          }
        }
      }
    }

    // Process any remaining data in buffer
    if (buffer.trim()) {
      const trimmedLine = buffer.trim();
      if (trimmedLine.startsWith('data: ')) {
        const data = trimmedLine.slice(6);
        try {
          const event = JSON.parse(data) as SSEEvent;
          if (event.type !== 'done') {
            yield event;
          }
        } catch {
          // Ignore malformed JSON
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
