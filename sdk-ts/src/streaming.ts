/**
 * Server-Sent Events (SSE) streaming utilities
 */

/**
 * Parse Server-Sent Events from a streaming response.
 *
 * @param response - Fetch Response object with streaming body
 * @yields Event data from each SSE message
 *
 * @example
 * ```typescript
 * const response = await fetch('/chat', { ... });
 * for await (const chunk of parseSSEStream(response)) {
 *   console.log(chunk);
 * }
 * ```
 */
export async function* parseSSEStream(response: Response): AsyncGenerator<string, void, unknown> {
  if (!response.body) {
    throw new Error('Response body is null');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      // Decode chunk and add to buffer
      buffer += decoder.decode(value, { stream: true });

      // Process complete lines
      const lines = buffer.split('\n');
      // Keep incomplete line in buffer
      buffer = lines.pop() || '';

      for (const line of lines) {
        const trimmedLine = line.trim();

        // Parse SSE format: "data: <content>"
        if (trimmedLine.startsWith('data: ')) {
          const data = trimmedLine.slice(6); // Remove "data: " prefix

          // Stop on [DONE] sentinel
          if (data === '[DONE]') {
            return;
          }

          yield data;
        }
      }
    }

    // Process any remaining data in buffer
    if (buffer.trim()) {
      const trimmedLine = buffer.trim();
      if (trimmedLine.startsWith('data: ')) {
        const data = trimmedLine.slice(6);
        if (data !== '[DONE]') {
          yield data;
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
