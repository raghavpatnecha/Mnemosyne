/**
 * Unit tests for SSE streaming
 */

import { describe, it, expect } from 'vitest';
import { parseSSEStream, SSEEvent } from '../../src/streaming.js';
import { createMockSSEResponse } from '../setup.js';

describe('parseSSEStream', () => {
  it('should parse SSE chunks', async () => {
    const chunks = ['chunk1', 'chunk2', 'chunk3'];
    const response = createMockSSEResponse(chunks);

    const receivedEvents: SSEEvent[] = [];

    for await (const event of parseSSEStream(response)) {
      receivedEvents.push(event);
    }

    // Should receive delta events for each chunk + done event
    const deltaEvents = receivedEvents.filter(e => e.type === 'delta');
    expect(deltaEvents).toHaveLength(3);
    expect(deltaEvents.map(e => e.delta)).toEqual(chunks);

    // Should also receive the done event
    const doneEvent = receivedEvents.find(e => e.type === 'done');
    expect(doneEvent).toBeDefined();
  });

  it('should stop after done event', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'delta', delta: 'chunk1' })}\n\n`));
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'delta', delta: 'chunk2' })}\n\n`));
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done', done: true })}\n\n`));
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'delta', delta: 'chunk3' })}\n\n`)); // Should not be processed
        controller.close();
      },
    });

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
    });

    const receivedEvents: SSEEvent[] = [];

    for await (const event of parseSSEStream(response)) {
      receivedEvents.push(event);
    }

    // Should receive 2 delta events + done event, but NOT chunk3
    const deltaEvents = receivedEvents.filter(e => e.type === 'delta');
    expect(deltaEvents).toHaveLength(2);
    expect(deltaEvents.map(e => e.delta)).toEqual(['chunk1', 'chunk2']);
  });

  it('should skip empty lines', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'delta', delta: 'chunk1' })}\n\n`));
        controller.enqueue(encoder.encode('\n\n')); // Empty line
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'delta', delta: 'chunk2' })}\n\n`));
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done', done: true })}\n\n`));
        controller.close();
      },
    });

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
    });

    const receivedEvents: SSEEvent[] = [];

    for await (const event of parseSSEStream(response)) {
      receivedEvents.push(event);
    }

    const deltaEvents = receivedEvents.filter(e => e.type === 'delta');
    expect(deltaEvents).toHaveLength(2);
    expect(deltaEvents.map(e => e.delta)).toEqual(['chunk1', 'chunk2']);
  });

  it('should skip non-data lines', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode(': comment\n\n'));
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'delta', delta: 'chunk1' })}\n\n`));
        controller.enqueue(encoder.encode('event: message\n\n'));
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'delta', delta: 'chunk2' })}\n\n`));
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done', done: true })}\n\n`));
        controller.close();
      },
    });

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
    });

    const receivedEvents: SSEEvent[] = [];

    for await (const event of parseSSEStream(response)) {
      receivedEvents.push(event);
    }

    const deltaEvents = receivedEvents.filter(e => e.type === 'delta');
    expect(deltaEvents).toHaveLength(2);
    expect(deltaEvents.map(e => e.delta)).toEqual(['chunk1', 'chunk2']);
  });

  it('should handle multi-line data', async () => {
    const encoder = new TextEncoder();
    const stream = new ReadableStream({
      start(controller) {
        controller.enqueue(encoder.encode('data: {"type":"delta","delta":"Hello '));
        controller.enqueue(encoder.encode('world"}\n\n'));
        controller.enqueue(encoder.encode(`data: ${JSON.stringify({ type: 'done', done: true })}\n\n`));
        controller.close();
      },
    });

    const response = new Response(stream, {
      headers: { 'Content-Type': 'text/event-stream' },
    });

    const receivedEvents: SSEEvent[] = [];

    for await (const event of parseSSEStream(response)) {
      receivedEvents.push(event);
    }

    const deltaEvents = receivedEvents.filter(e => e.type === 'delta');
    expect(deltaEvents).toHaveLength(1);
    expect(deltaEvents[0].delta).toBe('Hello world');
  });

  it('should handle rapid chunks', async () => {
    const chunks = Array.from({ length: 100 }, (_, i) => `chunk${i}`);
    const response = createMockSSEResponse(chunks);

    const receivedEvents: SSEEvent[] = [];

    for await (const event of parseSSEStream(response)) {
      receivedEvents.push(event);
    }

    const deltaEvents = receivedEvents.filter(e => e.type === 'delta');
    expect(deltaEvents).toHaveLength(100);
    expect(deltaEvents.map(e => e.delta)).toEqual(chunks);
  });

  it('should throw on null response body', async () => {
    const response = new Response(null, { status: 200 });

    await expect(async () => {
      for await (const _ of parseSSEStream(response)) {
        // Should throw before reaching here
      }
    }).rejects.toThrow('Response body is null');
  });
});
