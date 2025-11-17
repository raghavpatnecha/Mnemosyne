/**
 * Basic retrieval example demonstrating all 5 search modes
 *
 * This example shows how to:
 * - Perform semantic search (embeddings)
 * - Perform keyword search (BM25)
 * - Perform hybrid search (combining both)
 * - Perform hierarchical search (multi-level)
 * - Perform graph search (LightRAG)
 */

import { MnemosyneClient } from '../src/index.js';

// Initialize client
const client = new MnemosyneClient({
  apiKey: process.env.MNEMOSYNE_API_KEY || 'your_api_key_here',
  baseUrl: process.env.MNEMOSYNE_BASE_URL || 'http://localhost:8000/api/v1',
});

// Your collection ID (from ingestion)
const COLLECTION_ID = process.env.COLLECTION_ID || 'your-collection-id-here';

async function printResults(results: any, mode: string) {
  console.log('\n' + '='.repeat(60));
  console.log(`MODE: ${mode.toUpperCase()}`);
  console.log('='.repeat(60));
  console.log(`Found ${results.results.length} results in ${results.processing_time_ms.toFixed(2)}ms\n`);

  for (let i = 0; i < results.results.length; i++) {
    const result = results.results[i];
    console.log(`${i + 1}. Score: ${result.score.toFixed(4)}`);
    console.log(`   Document: ${result.document.title || result.document.filename}`);
    console.log(`   Chunk ${result.chunk_index}: ${result.content.substring(0, 150)}...`);
    console.log();
  }
}

async function main() {
  const query = 'What are the key innovations in transformer architecture?';

  try {
    // 1. Semantic Search (Default)
    console.log('1. SEMANTIC SEARCH (Embedding-based)');
    console.log('   Best for: Conceptual similarity, meaning-based retrieval');
    const semanticResults = await client.retrievals.retrieve({
      query,
      mode: 'semantic',
      top_k: 5,
      collection_id: COLLECTION_ID,
    });
    await printResults(semanticResults, 'semantic');

    // 2. Keyword Search (BM25)
    console.log('\n2. KEYWORD SEARCH (BM25)');
    console.log('   Best for: Exact term matching, technical jargon');
    const keywordResults = await client.retrievals.retrieve({
      query,
      mode: 'keyword',
      top_k: 5,
      collection_id: COLLECTION_ID,
    });
    await printResults(keywordResults, 'keyword');

    // 3. Hybrid Search (Recommended)
    console.log('\n3. HYBRID SEARCH (Recommended)');
    console.log('   Best for: Balanced results combining semantic + keyword');
    const hybridResults = await client.retrievals.retrieve({
      query,
      mode: 'hybrid',
      top_k: 5,
      collection_id: COLLECTION_ID,
    });
    await printResults(hybridResults, 'hybrid');

    // 4. Hierarchical Search
    console.log('\n4. HIERARCHICAL SEARCH');
    console.log('   Best for: Long documents, structured content');
    const hierarchicalResults = await client.retrievals.retrieve({
      query,
      mode: 'hierarchical',
      top_k: 5,
      collection_id: COLLECTION_ID,
    });
    await printResults(hierarchicalResults, 'hierarchical');

    // 5. Graph Search (LightRAG)
    console.log('\n5. GRAPH SEARCH (LightRAG)');
    console.log('   Best for: Complex reasoning, entity relationships');
    const graphResults = await client.retrievals.retrieve({
      query: 'how do transformers relate to BERT?',
      mode: 'graph',
      top_k: 5,
      collection_id: COLLECTION_ID,
    });
    await printResults(graphResults, 'graph');

    // 6. HybridRAG: Combine search with knowledge graph
    console.log('\n6. HYBRIDRAG (Search + Knowledge Graph)');
    console.log('   Best for: Enhanced accuracy with graph context');
    const hybridRAGResults = await client.retrievals.retrieve({
      query,
      mode: 'semantic',
      top_k: 5,
      collection_id: COLLECTION_ID,
      enable_graph: true,
    });
    await printResults(hybridRAGResults, 'hybridRAG');
    if (hybridRAGResults.graph_context) {
      console.log('\nGraph Context:');
      console.log(hybridRAGResults.graph_context);
    }
  } catch (error) {
    console.error('Error during retrieval:', error);
    process.exit(1);
  }
}

main();
