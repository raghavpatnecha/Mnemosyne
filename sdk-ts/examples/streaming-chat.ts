/**
 * Streaming chat example
 *
 * This example demonstrates:
 * - Real-time SSE streaming chat
 * - Multi-turn conversations
 * - Session management
 * - Streaming vs non-streaming modes
 */

import { MnemosyneClient } from '../src/index.js';

const client = new MnemosyneClient({
  apiKey: process.env.MNEMOSYNE_API_KEY || 'your_api_key_here',
  baseUrl: process.env.MNEMOSYNE_BASE_URL || 'http://localhost:8000/api/v1',
});

const COLLECTION_ID = process.env.COLLECTION_ID || 'your-collection-id-here';

async function streamingChatExample() {
  console.log('='.repeat(70));
  console.log('  Streaming Chat Example');
  console.log('='.repeat(70));

  console.log('\nExample 1: Basic Streaming Chat');
  console.log('─'.repeat(70));
  console.log('Question: "What is Retrieval-Augmented Generation?"\n');
  console.log('Answer: ');

  for await (const chunk of client.chat.chat({
    message: 'What is Retrieval-Augmented Generation?',
    collection_id: COLLECTION_ID,
    stream: true,
    top_k: 5,
  })) {
    process.stdout.write(chunk);
  }

  console.log('\n');
}

async function multiTurnConversation() {
  console.log('\nExample 2: Multi-Turn Conversation');
  console.log('─'.repeat(70));

  const questions = [
    'What are the main components of a RAG system?',
    'How does the retrieval process work?',
    'What are the benefits of using RAG?',
  ];

  let sessionId: string | undefined;

  for (const question of questions) {
    console.log(`\nQ: ${question}`);
    console.log('A: ');

    const chunks: string[] = [];

    for await (const chunk of client.chat.chat({
      message: question,
      collection_id: COLLECTION_ID,
      session_id: sessionId,
      stream: true,
    })) {
      process.stdout.write(chunk);
      chunks.push(chunk);
    }

    // Extract session ID from response metadata (if available)
    // Note: In actual implementation, you'd need to handle session ID extraction
    console.log('\n');
  }
}

async function sessionManagement() {
  console.log('\nExample 3: Session Management');
  console.log('─'.repeat(70));

  // List existing sessions
  console.log('\nListing chat sessions...');
  const sessions = await client.chat.listSessions({ limit: 10 });
  console.log(`Found ${sessions.length} sessions\n`);

  if (sessions.length > 0) {
    const latestSession = sessions[0];
    console.log(`Latest session: ${latestSession.id}`);
    console.log(`  Created: ${latestSession.created_at}`);
    console.log(`  Messages: ${latestSession.message_count}`);

    // Get session messages
    console.log('\nRetrieving session messages...');
    const messages = await client.chat.getSessionMessages(latestSession.id);

    messages.forEach((msg, i) => {
      console.log(`\n${i + 1}. ${msg.role.toUpperCase()}:`);
      console.log(`   ${msg.content.substring(0, 200)}${msg.content.length > 200 ? '...' : ''}`);
    });

    // Delete session
    console.log('\n\nDeleting session...');
    await client.chat.deleteSession(latestSession.id);
    console.log('✓ Session deleted');
  }
}

async function streamingVsNonStreaming() {
  console.log('\nExample 4: Streaming vs Non-Streaming');
  console.log('─'.repeat(70));

  const question = 'Explain transformers in 2 sentences';

  // Streaming mode
  console.log('\nStreaming Mode:');
  console.log('A: ');
  const streamStart = Date.now();

  for await (const chunk of client.chat.chat({
    message: question,
    stream: true,
  })) {
    process.stdout.write(chunk);
  }

  const streamTime = Date.now() - streamStart;
  console.log(`\n(Time to first token: ~instant, Total: ${streamTime}ms)`);

  // Non-streaming mode
  console.log('\nNon-Streaming Mode:');
  console.log('A: ');
  const nonStreamStart = Date.now();

  for await (const response of client.chat.chat({
    message: question,
    stream: false,
  })) {
    console.log(response);
  }

  const nonStreamTime = Date.now() - nonStreamStart;
  console.log(`(Time: ${nonStreamTime}ms)`);

  console.log('\n📊 Streaming provides better UX with instant feedback!');
}

async function main() {
  try {
    await streamingChatExample();
    await multiTurnConversation();
    await sessionManagement();
    await streamingVsNonStreaming();

    console.log('\n' + '='.repeat(70));
    console.log('  All streaming examples completed!');
    console.log('='.repeat(70));
  } catch (error) {
    console.error('\n❌ Error:', error);
    process.exit(1);
  }
}

main();
