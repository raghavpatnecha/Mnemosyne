/**
 * Async operations example
 *
 * This example demonstrates:
 * - Concurrent document uploads
 * - Parallel search operations
 * - Efficient batch processing
 * - Promise.all for performance
 */

import { MnemosyneClient } from '../src/index.js';

const client = new MnemosyneClient({
  apiKey: process.env.MNEMOSYNE_API_KEY || 'your_api_key_here',
  baseUrl: process.env.MNEMOSYNE_BASE_URL || 'http://localhost:8000/api/v1',
});

async function concurrentUploads() {
  console.log('='.repeat(70));
  console.log('  Example 1: Concurrent Document Uploads');
  console.log('='.repeat(70));

  // Create collection
  const collection = await client.collections.create({
    name: 'Async Demo Collection',
    description: 'Demonstrating concurrent operations',
  });

  console.log(`✓ Collection created: ${collection.id}\n`);

  // Upload multiple documents concurrently
  const files = ['doc1.pdf', 'doc2.pdf', 'doc3.pdf', 'doc4.pdf', 'doc5.pdf'];

  console.log(`Uploading ${files.length} documents concurrently...`);
  const uploadStart = Date.now();

  const uploadPromises = files.map((file) =>
    client.documents.create(collection.id, `./docs/${file}`, {
      filename: file,
      batch: 'concurrent-upload',
    })
  );

  const uploadedDocs = await Promise.all(uploadPromises);
  const uploadTime = Date.now() - uploadStart;

  console.log(`✓ Uploaded ${uploadedDocs.length} documents in ${uploadTime}ms`);
  console.log(`  Average: ${(uploadTime / uploadedDocs.length).toFixed(2)}ms per document\n`);

  return { collection, documents: uploadedDocs };
}

async function parallelSearches() {
  console.log('='.repeat(70));
  console.log('  Example 2: Parallel Search Operations');
  console.log('='.repeat(70));

  const queries = [
    'What is machine learning?',
    'Explain neural networks',
    'What are transformers?',
    'How does backpropagation work?',
  ];

  console.log(`Running ${queries.length} searches in parallel...\n`);
  const searchStart = Date.now();

  const searchPromises = queries.map((query) =>
    client.retrievals.retrieve({
      query,
      mode: 'hybrid',
      top_k: 3,
    })
  );

  const results = await Promise.all(searchPromises);
  const searchTime = Date.now() - searchStart;

  console.log(`✓ Completed ${results.length} searches in ${searchTime}ms`);
  console.log(`  Average: ${(searchTime / results.length).toFixed(2)}ms per search\n`);

  results.forEach((result, i) => {
    console.log(`Query ${i + 1}: "${queries[i]}"`);
    console.log(`  Results: ${result.results.length}`);
    console.log(`  Total available: ${result.total_results}`);
  });
}

async function batchStatusCheck(documentIds: string[]) {
  console.log('\n' + '='.repeat(70));
  console.log('  Example 3: Batch Status Checking');
  console.log('='.repeat(70));

  console.log(`\nChecking status for ${documentIds.length} documents...`);

  const statusPromises = documentIds.map((id) => client.documents.getStatus(id));
  const statuses = await Promise.all(statusPromises);

  const statusCounts = {
    pending: 0,
    processing: 0,
    completed: 0,
    failed: 0,
  };

  statuses.forEach((status) => {
    statusCounts[status.status as keyof typeof statusCounts]++;
  });

  console.log('\nStatus Summary:');
  console.log(`  ✓ Completed: ${statusCounts.completed}`);
  console.log(`  ⏳ Processing: ${statusCounts.processing}`);
  console.log(`  ⏸️  Pending: ${statusCounts.pending}`);
  console.log(`  ❌ Failed: ${statusCounts.failed}`);

  return statuses;
}

async function parallelCollectionOperations() {
  console.log('\n' + '='.repeat(70));
  console.log('  Example 4: Parallel Collection Operations');
  console.log('='.repeat(70));

  console.log('\nCreating 3 collections concurrently...');

  const createPromises = [
    client.collections.create({ name: 'Collection 1', metadata: { type: 'research' } }),
    client.collections.create({ name: 'Collection 2', metadata: { type: 'docs' } }),
    client.collections.create({ name: 'Collection 3', metadata: { type: 'papers' } }),
  ];

  const collections = await Promise.all(createPromises);
  console.log(`✓ Created ${collections.length} collections`);

  // List and update concurrently
  console.log('\nFetching and updating collections concurrently...');

  const operations = collections.map(async (collection) => {
    const updated = await client.collections.update(collection.id, {
      metadata: {
        ...(collection.metadata as object),
        updated_at: new Date().toISOString(),
        status: 'active',
      },
    });
    return updated;
  });

  const updated = await Promise.all(operations);
  console.log(`✓ Updated ${updated.length} collections`);

  // Clean up - delete concurrently
  console.log('\nCleaning up...');
  await Promise.all(collections.map((c) => client.collections.delete(c.id)));
  console.log('✓ Deleted all test collections');
}

async function efficientPipeline() {
  console.log('\n' + '='.repeat(70));
  console.log('  Example 5: Efficient Processing Pipeline');
  console.log('='.repeat(70));

  const pipelineStart = Date.now();

  // Step 1: Create collection
  const collection = await client.collections.create({
    name: 'Pipeline Demo',
  });

  // Step 2: Upload documents in batches (concurrent within batch)
  const fileBatches = [
    ['file1.pdf', 'file2.pdf', 'file3.pdf'],
    ['file4.pdf', 'file5.pdf', 'file6.pdf'],
  ];

  const allDocs = [];

  for (const batch of fileBatches) {
    console.log(`\nUploading batch of ${batch.length} files...`);
    const batchDocs = await Promise.all(
      batch.map((file) =>
        client.documents.create(collection.id, `./docs/${file}`, { filename: file })
      )
    );
    allDocs.push(...batchDocs);
    console.log('✓ Batch complete');
  }

  // Step 3: Monitor processing (concurrent status checks)
  console.log('\nMonitoring processing...');
  let allComplete = false;
  let attempts = 0;

  while (!allComplete && attempts < 10) {
    const statuses = await Promise.all(allDocs.map((doc) => client.documents.getStatus(doc.id)));

    const completed = statuses.filter((s) => s.status === 'completed').length;
    console.log(`  Progress: ${completed}/${allDocs.length} complete`);

    allComplete = completed === allDocs.length;

    if (!allComplete) {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      attempts++;
    }
  }

  const pipelineTime = Date.now() - pipelineStart;
  console.log(`\n✓ Pipeline complete in ${(pipelineTime / 1000).toFixed(2)}s`);

  // Cleanup
  await client.collections.delete(collection.id);
}

async function main() {
  try {
    const { collection, documents } = await concurrentUploads();
    await parallelSearches();
    await batchStatusCheck(documents.map((d) => d.id));
    await parallelCollectionOperations();
    await efficientPipeline();

    // Cleanup
    await client.collections.delete(collection.id);

    console.log('\n' + '='.repeat(70));
    console.log('  All async examples completed!');
    console.log('='.repeat(70));
    console.log('\n💡 Key Takeaway: Use Promise.all() for concurrent operations');
    console.log('   to maximize throughput and minimize latency!\n');
  } catch (error) {
    console.error('\n❌ Error:', error);
    process.exit(1);
  }
}

main();
