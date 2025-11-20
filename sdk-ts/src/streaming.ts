/**
 * Server-Sent Events (SSE) streaming utilities
 */

/**
 * SSE event types from the backend
 */
export interface SSEEvent {
  type: 'delta' | 'sources' | 'done' | 'error';
  delta?: string;
  sources?: Array<Record<string, unknown>>;
  done?: boolean;
  session_id?: string;
  error?: string;
}

/**
 * Parse Server-Sent Events from a streaming response.
 *
 * Automatically parses JSON events and yields structured objects.
 * Event types: delta, sources, done, error
 *
 * @param response - Fetch Response object with streaming body
 * @yields Parsed SSE event objects
 *
 * @example
 * ```typescript
 * const response = await fetch('/chat', { ... });
 * for await (const event of parseSSEStream(response)) {
 *   if (event.type === 'delta') {
 *     console.log(event.delta);
 *   } else if (event.type === 'sources') {
 *     console.log('Sources:', event.sources);
 *   } else if (event.type === 'done') {
 *     console.log('Session ID:', event.session_id);
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
