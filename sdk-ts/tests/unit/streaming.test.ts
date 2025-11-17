/**
 * Unit tests for SSE streaming
 */

import { describe, it, expect } from 'vitest';
import { parseSSEStream } from '../../src/streaming.js';
import { createMockSSEResponse } from '../setup.js';

describe('parseSSEStream', () => {
  it('should parse SSE chunks', async () => {
    const chunks = ['chunk1', 'chunk2', 'chunk3'];
    const response = createMockSSEResponse(chunks);

    const receivedChunks: string[] = [];

    for await (const chunk of parseSSEStream(response)) {
      receivedChunks.push(chunk);
    }

    expect(receivedChunks).toEqual(chunks);
  });

  it('should stop on [DONE] sentinel', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: chunk1\n\n'));
        controller.enqueue(encoder.encode('data: chunk2\n\n'));
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.enqueue(encoder.encode('data: chunk3\n\n')); // Should not be processed
        controller.close();
      },
    });

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
    });

    const receivedChunks: string[] = [];

    for await (const chunk of parseSSEStream(response)) {
      receivedChunks.push(chunk);
    }

    expect(receivedChunks).toEqual(['chunk1', 'chunk2']);
  });

  it('should skip empty lines', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: chunk1\n\n'));
        controller.enqueue(encoder.encode('\n\n')); // Empty line
        controller.enqueue(encoder.encode('data: chunk2\n\n'));
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
      },
    });

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
    });

    const receivedChunks: string[] = [];

    for await (const chunk of parseSSEStream(response)) {
      receivedChunks.push(chunk);
    }

    expect(receivedChunks).toEqual(['chunk1', 'chunk2']);
  });

  it('should skip non-data lines', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(': comment\n\n'));
        controller.enqueue(encoder.encode('data: chunk1\n\n'));
        controller.enqueue(encoder.encode('event: message\n\n'));
        controller.enqueue(encoder.encode('data: chunk2\n\n'));
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
      },
    });

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
    });

    const receivedChunks: string[] = [];

    for await (const chunk of parseSSEStream(response)) {
      receivedChunks.push(chunk);
    }

    expect(receivedChunks).toEqual(['chunk1', 'chunk2']);
  });

  it('should handle multi-line data', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"text":"Hello '));
        controller.enqueue(encoder.encode('world"}\n\n'));
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        controller.close();
      },
    });

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
    });

    const receivedChunks: string[] = [];

    for await (const chunk of parseSSEStream(response)) {
      receivedChunks.push(chunk);
    }

    expect(receivedChunks).toEqual(['{"text":"Hello world"}']);
  });

  it('should handle rapid chunks', async () => {
    const chunks = Array.from({ length: 100 }, (_, i) => `chunk${i}`);
    const response = createMockSSEResponse(chunks);

    const receivedChunks: string[] = [];

    for await (const chunk of parseSSEStream(response)) {
      receivedChunks.push(chunk);
    }

    expect(receivedChunks).toEqual(chunks);
  });

  it('should throw on non-ok response', async () => {
    const response = new Response(null, { status: 500 });

    await expect(async () => {
      for await (const _ of parseSSEStream(response)) {
        // Should throw before reaching here
      }
    }).rejects.toThrow();
  });
});
