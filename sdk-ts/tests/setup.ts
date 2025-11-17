/**
 * Test setup and utilities for Vitest
 */

import { beforeAll, afterAll, afterEach } from 'vitest';

// Mock fetch globally
global.fetch = async () => {
  throw new Error('Unmocked fetch call - use vi.mock() in your test');
};

// Setup before all tests
beforeAll(() => {
  // Set test environment variables
  process.env.MNEMOSYNE_API_KEY = 'test_api_key';
  process.env.MNEMOSYNE_BASE_URL = 'http://localhost:8000';
});

// Cleanup after each test
afterEach(() => {
  // Clear all mocks
  vi.clearAllMocks();
});

// Cleanup after all tests
afterAll(() => {
  // Clean up environment
  delete process.env.MNEMOSYNE_API_KEY;
  delete process.env.MNEMOSYNE_BASE_URL;
});

/**
 * Create a mock Response object
 */
export function createMockResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Create a mock SSE Response
 */
export function createMockSSEResponse(chunks: string[]): Response {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    start(controller) {
      chunks.forEach((chunk) => {
        controller.enqueue(encoder.encode(`data: ${chunk}\n\n`));
      });
      controller.enqueue(encoder.encode('data: [DONE]\n\n'));
      controller.close();
    },
  });

  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  });
}

/**
 * Create mock error response
 */
export function createMockErrorResponse(message: string, status: number): Response {
  return new Response(JSON.stringify({ detail: message }), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

/**
 * Sleep helper for testing delays
 */
export function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
