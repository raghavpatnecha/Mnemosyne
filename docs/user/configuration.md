# Configuration Guide

Complete guide to configuring Mnemosyne for development and production.

## Environment Variables

Mnemosyne uses environment variables for configuration. All variables are defined in `.env.example` at the project root.

### Quick Setup

```bash
# Copy the example file
cp .env.example .env

# Edit with your values
nano .env
```

## Core Configuration

### Application Settings

```bash
APP_NAME=Mnemosyne
APP_VERSION=0.1.0
ENVIRONMENT=development  # or production
DEBUG=true              # Set false in production
API_RELOAD=true         # Set false in production
```

### Security

**CRITICAL**: Change these before deploying!

```bash
# Generate a secure secret key:
# openssl rand -hex 32
SECRET_KEY=your-secret-key-here

# API key prefix (for identifying keys)
API_KEY_PREFIX=mn_dev_
```

## Database Configuration

### PostgreSQL

```bash
POSTGRES_USER=mnemosyne
POSTGRES_PASSWORD=your-strong-password
POSTGRES_DB=mnemosyne

# Connection string
DATABASE_URL=postgresql://mnemosyne:password@localhost:5432/mnemosyne
```

**Production**: Use strong passwords (20+ characters, random)

```bash
# Generate strong password:
openssl rand -base64 32
```

### Redis

```bash
REDIS_PASSWORD=your-redis-password
REDIS_URL=redis://:password@localhost:6379/0
```

**Note**: Redis is used for:
- Embedding cache (24h TTL)
- Search results cache (1h TTL)
- Celery task queue
- Rate limiting counters

## API Server

```bash
API_HOST=0.0.0.0
API_PORT=8000

# CORS - Comma-separated origins
CORS_ORIGINS=["http://localhost:3000","http://localhost:8080"]
```

**Production**: Restrict CORS to your domains only

```bash
CORS_ORIGINS=["https://yourdomain.com","https://app.yourdomain.com"]
```

## LLM Configuration

### OpenAI

```bash
OPENAI_API_KEY=sk-your-openai-api-key-here

# Model configuration
EMBEDDING_MODEL=text-embedding-3-large  # 1536 dimensions
CHAT_MODEL=gpt-4o-mini                   # Default chat model
```

**Supported models**:
- Embeddings: `text-embedding-3-large`, `text-embedding-3-small`
- Chat: `gpt-4o-mini`, `gpt-4o`, `gpt-4`, `gpt-3.5-turbo`

### Alternative LLM Providers

Mnemosyne uses LiteLLM, supporting 150+ models:

```bash
# Anthropic
CHAT_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-...

# Ollama (local)
CHAT_MODEL=ollama/llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

See [LiteLLM docs](https://docs.litellm.ai/docs/providers) for all providers.

## LightRAG (Knowledge Graph)

**CRITICAL**: LightRAG is core to Mnemosyne's architecture!

```bash
LIGHTRAG_ENABLED=true
LIGHTRAG_WORKING_DIR=/app/data/lightrag

# Chunking
LIGHTRAG_CHUNK_SIZE=512
LIGHTRAG_CHUNK_OVERLAP=128

# Retrieval
LIGHTRAG_TOP_K=20           # Results to return
LIGHTRAG_CHUNK_TOP_K=10     # Chunks per result

# Token limits
LIGHTRAG_MAX_ENTITY_TOKENS=6000
LIGHTRAG_MAX_RELATION_TOKENS=8000
LIGHTRAG_MAX_TOKENS=30000

# Default mode: local, global, or hybrid
LIGHTRAG_DEFAULT_MODE=hybrid
```

**What is LightRAG?**
- Graph-based RAG with entity extraction
- 99% token reduction vs traditional RAG
- Best for reasoning and relationship queries

## Document Processing

### Upload & Storage

```bash
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE=104857600  # 100MB in bytes
```

### Chunking

```bash
CHUNK_SIZE=512
CHUNK_OVERLAP=128
```

**Notes**:
- Smaller chunks: Better precision, more chunks
- Larger chunks: Better context, fewer chunks
- Overlap: Ensures continuity across boundaries

### Video Processing

```bash
VIDEO_FFMPEG_PATH=ffmpeg
VIDEO_FFPROBE_PATH=ffprobe
VIDEO_TEMP_DIR=/tmp/mnemosyne_video
VIDEO_MAX_DURATION=3600  # 1 hour max
```

**Requirements**:
- FFmpeg installed (`apt-get install ffmpeg`)
- Sufficient disk space in temp directory

### Speech-to-Text

```bash
# OpenAI Whisper (default)
STT_SERVICE=whisper-1
STT_SERVICE_API_KEY=  # Uses OPENAI_API_KEY

# Local Whisper (optional)
STT_LOCAL_ENABLED=false
```

**Cost**: OpenAI Whisper costs $0.006/minute of audio.

## Rate Limiting

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_CHAT=10/minute       # Chat requests
RATE_LIMIT_RETRIEVAL=100/minute # Search requests
RATE_LIMIT_UPLOAD=20/hour       # Document uploads
```

**Format**: `{count}/{period}`
- Periods: `second`, `minute`, `hour`, `day`

**Production**: Adjust based on your user base and API costs.

## Monitoring (Production)

### Grafana

```bash
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=your-strong-password
```

Access: http://localhost:3000

### Prometheus

Automatically configured. Access: http://localhost:9090

## Backups (Production)

```bash
BACKUP_RETENTION_DAYS=7
```

**Backup strategy**:
- Daily automated backups at 2 AM
- Stored in Docker volume: `postgres_backups`
- Old backups auto-deleted after retention period

## Environment-Specific Configuration

### Development

```bash
cp .env.example .env

# Minimal required:
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://mnemosyne:dev@localhost:5432/mnemosyne
REDIS_URL=redis://:dev@localhost:6379/0
```

### Production

```bash
cp .env.example .env.production

# Generate all secrets:
openssl rand -hex 32  # SECRET_KEY
openssl rand -hex 32  # POSTGRES_PASSWORD
openssl rand -hex 32  # REDIS_PASSWORD

# Set:
DEBUG=false
API_RELOAD=false
ENVIRONMENT=production
CORS_ORIGINS=["https://yourdomain.com"]
```

## Validation

Check your configuration:

```bash
# Test database connection
docker-compose exec api python -c "from backend.database import engine; engine.connect(); print('✓ Database OK')"

# Test Redis connection
docker-compose exec api python -c "import redis; r=redis.from_url('redis://...'); r.ping(); print('✓ Redis OK')"

# Test OpenAI API key
docker-compose exec api python -c "from openai import OpenAI; c=OpenAI(); c.models.list(); print('✓ OpenAI OK')"
```

## Troubleshooting

### Database connection fails

```bash
# Check DATABASE_URL format
# postgresql://USER:PASSWORD@HOST:PORT/DATABASE

# Verify PostgreSQL is running
docker-compose ps postgres
```

### Redis connection fails

```bash
# Check REDIS_URL format
# redis://:PASSWORD@HOST:PORT/DB

# Verify Redis is running
docker-compose ps redis
```

### OpenAI API errors

```bash
# Check API key starts with "sk-"
echo $OPENAI_API_KEY | cut -c1-3  # Should show "sk-"

# Test with curl
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### LightRAG not working

```bash
# Ensure enabled
LIGHTRAG_ENABLED=true

# Check working directory exists and is writable
ls -la $LIGHTRAG_WORKING_DIR
```

## Security Best Practices

### DO

✅ Use strong, random passwords (20+ characters)
✅ Generate unique SECRET_KEY per environment
✅ Restrict CORS to your domains only
✅ Use HTTPS in production (SSL/TLS)
✅ Keep .env files out of git (.gitignore)
✅ Rotate API keys regularly
✅ Enable rate limiting in production

### DON'T

❌ Use default passwords
❌ Commit .env files to git
❌ Share SECRET_KEY across environments
❌ Use DEBUG=true in production
❌ Allow CORS from all origins (*)
❌ Store secrets in code

## Complete .env.example

See [.env.example](../../.env.example) for the complete, commented configuration file with all variables.

## Quick Start Checklist

For new deployments:

- [ ] Copy `.env.example` to `.env`
- [ ] Generate `SECRET_KEY` (openssl rand -hex 32)
- [ ] Set `OPENAI_API_KEY`
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Set strong `REDIS_PASSWORD`
- [ ] Configure `CORS_ORIGINS` for your domain
- [ ] Set `DEBUG=false` for production
- [ ] Set `ENVIRONMENT=production`
- [ ] Test database connection
- [ ] Test Redis connection
- [ ] Test OpenAI API key
- [ ] Verify LightRAG working directory

## Need Help?

- **Configuration issues**: Check [deployment guide](deployment.md)
- **Environment setup**: See [getting started](getting-started.md)
- **Production deployment**: See [deployment options](deployment-options.md)
- **API questions**: See [API reference](api-reference.md)
