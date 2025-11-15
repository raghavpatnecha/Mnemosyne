-- Initialize PostgreSQL with pgvector extension
-- This script runs automatically on first container startup

-- Enable pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable full-text search (for hybrid search in Week 2)
-- pg_trgm for trigram-based text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Verify extensions are installed
SELECT
    extname AS extension_name,
    extversion AS version
FROM pg_extension
WHERE extname IN ('vector', 'uuid-ossp', 'pg_trgm')
ORDER BY extname;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Mnemosyne database initialized successfully';
    RAISE NOTICE 'Extensions: pgvector, uuid-ossp, pg_trgm';
END $$;
