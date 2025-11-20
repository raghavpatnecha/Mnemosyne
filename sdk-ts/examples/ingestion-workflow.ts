/**
 * Complete document ingestion workflow
 *
 * This example demonstrates:
 * 1. Creating a collection
 * 2. Batch uploading documents
 * 3. Monitoring processing status
 * 4. Verifying ingestion
 * 5. Updating metadata
 */

import { MnemosyneClient } from '../src/index.js';
import { readdir } from 'fs/promises';
import { join } from 'path';

const client = new MnemosyneClient({
  apiKey: process.env.MNEMOSYNE_API_KEY || 'your_api_key_here',
  baseUrl: process.env.MNEMOSYNE_BASE_URL || 'http://localhost:8000/api/v1',
});

// Directory containing documents to upload
const DOCS_DIR = process.env.DOCS_DIR || './demo_docs';

async function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function main() {
  console.log('='.repeat(70));
  console.log('  Mnemosyne Ingestion Workflow');
  console.log('='.repeat(70));

  try {
    // Step 1: Create Collection
    console.log('\n' + '─'.repeat(70));
    console.log('STEP 1: Creating collection');
    console.log('─'.repeat(70));

    const collection = await client.collections.create({
      name: 'Research Papers',
      description: 'AI/ML research papers collection',
      metadata: {
        domain: 'artificial-intelligence',
        created_by: 'ingestion-workflow',
      },
    });

    console.log(`✓ Collection created: ${collection.name}`);
    console.log(`  ID: ${collection.id}`);
    console.log(`  Created at: ${collection.created_at}`);

    // Step 2: Batch Upload Documents
    console.log('\n' + '─'.repeat(70));
    console.log('STEP 2: Uploading documents');
    console.log('─'.repeat(70));

    const files = await readdir(DOCS_DIR);
    const pdfFiles = files.filter((f) => f.endsWith('.pdf'));

    console.log(`Found ${pdfFiles.length} PDF files to upload`);

    const uploadedDocs = [];
    for (const file of pdfFiles) {
      const filePath = join(DOCS_DIR, file);
      console.log(`Uploading: ${file}...`);

      const doc = await client.documents.create(collection.id, filePath, {
        filename: file,
        uploaded_at: new Date().toISOString(),
      });

      uploadedDocs.push(doc);
      console.log(`  ✓ Uploaded: ${doc.id}`);
    }

    // Step 3: Monitor Processing Status
    console.log('\n' + '─'.repeat(70));
    console.log('STEP 3: Monitoring processing status');
    console.log('─'.repeat(70));

    let allCompleted = false;
    let attempts = 0;
    const maxAttempts = 30; // 30 * 2s = 60s max wait

    while (!allCompleted && attempts < maxAttempts) {
      const statuses = await Promise.all(
        uploadedDocs.map((doc) => client.documents.getStatus(doc.id))
      );

      const completed = statuses.filter((s) => s.status === 'completed').length;
      const processing = statuses.filter((s) => s.status === 'processing').length;
      const failed = statuses.filter((s) => s.status === 'failed').length;

      console.log(
        `Status: ${completed} completed, ${processing} processing, ${failed} failed`
      );

      allCompleted = completed === uploadedDocs.length;

      if (failed > 0) {
        console.error('⚠️  Some documents failed to process');
        statuses.filter((s) => s.status === 'failed').forEach((s) => {
          console.error(`  Failed: ${s.document_id} - ${s.error_message}`);
        });
      }

      if (!allCompleted) {
        await sleep(2000); // Wait 2 seconds
        attempts++;
      }
    }

    if (allCompleted) {
      console.log('✓ All documents processed successfully!');
    } else {
      console.log('⚠️  Timeout waiting for processing to complete');
    }

    // Step 4: Verify Ingestion
    console.log('\n' + '─'.repeat(70));
    console.log('STEP 4: Verifying ingestion');
    console.log('─'.repeat(70));

    const docs = await client.documents.list(collection.id, {
      status_filter: 'completed',
    });

    console.log(`✓ Total documents in collection: ${docs.data.length}`);

    // Calculate statistics
    const totalChunks = docs.data.reduce((sum, doc) => {
      const status = doc.processing_info as any;
      return sum + (status?.chunk_count || 0);
    }, 0);

    const totalTokens = docs.data.reduce((sum, doc) => {
      const status = doc.processing_info as any;
      return sum + (status?.total_tokens || 0);
    }, 0);

    console.log(`  Total chunks: ${totalChunks}`);
    console.log(`  Total tokens: ${totalTokens}`);

    // Step 5: Update Metadata
    console.log('\n' + '─'.repeat(70));
    console.log('STEP 5: Updating metadata');
    console.log('─'.repeat(70));

    await client.collections.update(collection.id, {
      metadata: {
        ...collection.metadata,
        ingestion_completed: new Date().toISOString(),
        document_count: docs.data.length,
        total_chunks: totalChunks,
      },
    });

    console.log('✓ Metadata updated successfully');

    console.log('\n' + '='.repeat(70));
    console.log('  Ingestion workflow completed!');
    console.log('='.repeat(70));
    console.log(`\nCollection ID: ${collection.id}`);
    console.log('Use this ID for retrieval and chat operations.\n');
  } catch (error) {
    console.error('\n❌ Error during ingestion:', error);
    process.exit(1);
  }
}

main();
