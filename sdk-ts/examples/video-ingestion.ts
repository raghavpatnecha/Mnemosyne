/**
 * Video ingestion example (YouTube + MP4)
 *
 * This example shows how to:
 * - Ingest YouTube videos
 * - Ingest local MP4 files
 * - Monitor video processing
 * - Search transcribed content
 */

import { MnemosyneClient } from '../src/index.js';

const client = new MnemosyneClient({
  apiKey: process.env.MNEMOSYNE_API_KEY || 'your_api_key_here',
  baseUrl: process.env.MNEMOSYNE_BASE_URL || 'http://localhost:8000/api/v1',
});

async function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForProcessing(documentId: string, maxWaitMs = 300000) {
  const startTime = Date.now();
  let status;

  while (Date.now() - startTime < maxWaitMs) {
    status = await client.documents.getStatus(documentId);

    console.log(`  Status: ${status.status} (${status.chunk_count} chunks processed)`);

    if (status.status === 'completed') {
      return status;
    }

    if (status.status === 'failed') {
      throw new Error(`Processing failed: ${status.error_message}`);
    }

    await sleep(5000); // Check every 5 seconds
  }

  throw new Error('Timeout waiting for processing');
}

async function main() {
  console.log('='.repeat(70));
  console.log('  Video Ingestion Example');
  console.log('='.repeat(70));

  try {
    // Create collection
    console.log('\nCreating video collection...');
    const collection = await client.collections.create({
      name: 'Video Library',
      description: 'Collection of video transcripts',
      metadata: { type: 'video' },
    });
    console.log(`✓ Collection created: ${collection.id}\n`);

    // Example 1: Ingest YouTube Video
    console.log('─'.repeat(70));
    console.log('Example 1: YouTube Video Ingestion');
    console.log('─'.repeat(70));

    const youtubeUrl = 'https://youtube.com/watch?v=example'; // Replace with actual URL
    console.log(`Uploading YouTube video: ${youtubeUrl}`);

    const youtubeDoc = await client.documents.create(collection.id, youtubeUrl, {
      title: 'AI Lecture Series - Episode 1',
      source: 'youtube',
      topic: 'machine-learning',
    });

    console.log(`✓ YouTube video queued: ${youtubeDoc.id}`);
    console.log('  Waiting for processing (this may take several minutes)...');

    const youtubeStatus = await waitForProcessing(youtubeDoc.id);
    console.log(`✓ Processing complete!`);
    console.log(`  Chunks created: ${youtubeStatus.chunk_count}`);
    console.log(`  Total tokens: ${youtubeStatus.total_tokens}\n`);

    // Example 2: Ingest Local MP4 File
    console.log('─'.repeat(70));
    console.log('Example 2: Local MP4 File Ingestion');
    console.log('─'.repeat(70));

    const mp4Path = './videos/meeting_recording.mp4';
    console.log(`Uploading MP4 file: ${mp4Path}`);

    const mp4Doc = await client.documents.create(collection.id, mp4Path, {
      title: 'Team Meeting - 2024-01-15',
      source: 'local',
      meeting_type: 'standup',
    });

    console.log(`✓ MP4 file queued: ${mp4Doc.id}`);
    console.log('  Waiting for processing...');

    const mp4Status = await waitForProcessing(mp4Doc.id);
    console.log(`✓ Processing complete!`);
    console.log(`  Chunks created: ${mp4Status.chunk_count}`);
    console.log(`  Total tokens: ${mp4Status.total_tokens}\n`);

    // Example 3: Search Video Transcripts
    console.log('─'.repeat(70));
    console.log('Example 3: Searching Video Transcripts');
    console.log('─'.repeat(70));

    const query = 'What were the key discussion points?';
    console.log(`Query: "${query}"\n`);

    const results = await client.retrievals.retrieve({
      query,
      mode: 'hybrid',
      top_k: 5,
      collection_id: collection.id,
    });

    console.log(`Found ${results.results.length} results:\n`);
    results.results.forEach((result, i) => {
      console.log(`${i + 1}. Score: ${result.score.toFixed(4)}`);
      console.log(`   Video: ${result.document.title}`);
      console.log(`   Segment: ${result.content.substring(0, 200)}...\n`);
    });

    // Example 4: Chat with Video Content
    console.log('─'.repeat(70));
    console.log('Example 4: Chat with Video Content');
    console.log('─'.repeat(70));

    console.log('Question: "Summarize the main topics discussed in the videos"\n');
    console.log('Answer: ');

    for await (const chunk of client.chat.chat({
      message: 'Summarize the main topics discussed in the videos',
      collection_id: collection.id,
      stream: true,
    })) {
      process.stdout.write(chunk);
    }

    console.log('\n\n' + '='.repeat(70));
    console.log('  Video ingestion examples completed!');
    console.log('='.repeat(70));
  } catch (error) {
    console.error('\n❌ Error:', error);
    process.exit(1);
  }
}

main();
