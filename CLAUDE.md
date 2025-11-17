# Mnemosyne - Development Guidelines

## Overview

Mnemosyne is an open-source RAG-as-a-Service platform providing a clean API and Python SDK for building AI-powered search and chat applications. Built with FastAPI, PostgreSQL + pgvector, LightRAG, and Celery. This document defines core development principles and workflows for all contributors.

---

## 🚀 SuperClaude Framework Integration

**CRITICAL RULE: Use SuperClaude commands when applicable**

Mnemosyne integrates [SuperClaude Framework](https://github.com/SuperClaude-Org/SuperClaude_Framework) - a meta-programming framework with 30+ specialized slash commands for structured development workflows.

**Available Commands:**
- `/research` - Deep web research with Tavily integration
- `/brainstorm` - Structured brainstorming sessions
- `/design` - System design and architecture
- `/implement` - Code implementation workflows
- `/test` - Testing strategies and execution
- `/pm` - Project management and planning
- `/document` - Documentation generation
- `/analyze` - Code analysis and review
- `/troubleshoot` - Debugging workflows
- `/git` - Git operations and workflows
- ...and 20+ more (use `/sc` to see all)

**When to Use SuperClaude Commands:**
1. **Research tasks**: Use `/research` instead of manual web searching
2. **Planning**: Use `/brainstorm` or `/pm` for feature planning
3. **Design**: Use `/design` for architecture decisions
4. **Implementation**: Use `/implement` for structured coding
5. **Testing**: Use `/test` for test generation and execution
6. **Documentation**: Use `/document` for auto-documentation

**Installation:**
```bash
pipx install superclaude
superclaude install
```

**Reference:** https://github.com/SuperClaude-Org/SuperClaude_Framework

---

## Critical Workflows

### Before Making ANY Changes

**ALWAYS use the memory skill first:**
```bash
# Use the memory skill to query project history and patterns
# Check git history for related changes
# Search for similar implementations
# Review CLAUDE.md guidelines
```

**ALWAYS use swarm orchestration for tasks:**
- Identify all independent operations
- Execute them concurrently in a single message
- Use parallel tool calls for maximum efficiency
- Never execute sequentially what can run in parallel

### Standard Task Workflow

1. **Query Memory**: Use memory skill to understand context
2. **Plan with Swarm**: Identify parallel vs sequential operations
3. **Execute Concurrently**: Batch all independent operations
4. **Run Quality Checks**: Lint, test, and build (in parallel when possible)
5. **Commit Changes**: Clear, descriptive commit messages

---

## Core Principles

### Concurrent Execution Mandate

**ALL operations MUST be concurrent/parallel in a single message when independent.**

Examples:
- Reading multiple files: Use multiple Read calls in one message
- Editing independent files: Use multiple Edit calls in one message
- Running checks: Execute lint + test + build in parallel

### File Size Limit

**NO file should exceed 300 lines.**

If a file approaches 300 lines:
- Split into logical modules
- Extract utilities to separate files
- Create focused, single-responsibility components
- Use service/utility pattern for separation

### No Backward Compatibility

**Do NOT add fallbacks or backward compatibility code.**

- Focus on current implementation
- Remove deprecated code paths
- Keep codebase clean and forward-looking
- Document breaking changes in commits

### No Code Emojis

**NEVER use emojis in code, comments, or docstrings.**

- Use clear, professional language
- Write descriptive variable/function names
- Use proper documentation instead of emoji shortcuts
- Emojis allowed only in README.md and user-facing markdown

### Always Run Quality Checks

**After EVERY task completion:**

1. **Lint the code**: Ensure code quality and style compliance
2. **Run tests**: Verify functionality remains intact
3. **Build the app**: Confirm application compiles/runs successfully

Execute these in parallel when possible:
```bash
# Parallel execution example
pytest tests/ && python -m pylint backend/ && python -m black backend --check
```

---

## Project Architecture

### Directory Structure

```
mnemosyne/
├── backend/           # FastAPI RAG-as-a-Service API
│   ├── api/           # API endpoints (auth, collections, documents, retrievals, chat)
│   ├── models/        # SQLAlchemy database models
│   ├── schemas/       # Pydantic request/response schemas
│   ├── services/      # Business logic (LightRAG, embeddings, search)
│   ├── tasks/         # Celery background tasks
│   ├── core/          # Core utilities (security, exceptions)
│   ├── middleware/    # Custom middleware (rate limiting)
│   └── main.py        # FastAPI application entry
├── sdk/               # Python SDK for Mnemosyne API
│   ├── mnemosyne/     # SDK source code
│   └── examples/      # Usage examples
├── docs/              # Documentation
│   ├── user/          # User-facing documentation
│   ├── developer/     # Developer documentation
│   └── archive/       # Historical docs
├── src/               # [DEPRECATED] Legacy Medium search (kept for reference)
├── tests/             # Test suites
├── .claude/           # Claude Code configuration
│   └── skills/        # Custom skills (memory, swarm)
└── CLAUDE.md          # This file
```

### Service Layer Architecture

**Multi-Layer Architecture:**
1. **API Layer**: FastAPI endpoints (authentication, validation, routing)
2. **Service Layer**: Business logic (document processing, search, chat)
3. **Task Layer**: Celery async tasks (parsing, chunking, embedding, indexing)
4. **Data Layer**: PostgreSQL + pgvector + Redis (storage, vectors, cache)

### Code Organization Rules

**Python Files:**
- `snake_case` for filenames
- `PascalCase` for classes
- `snake_case` for functions/variables
- `SCREAMING_SNAKE_CASE` for constants
- Maximum 300 lines per file

**Service Pattern:**
- One service class per file
- Utility functions in `*_utils.py`
- Clear separation of concerns
- Strategy pattern for extensibility

**Import Organization:**
```python
# Standard library
import json
import asyncio

# External packages
from langchain import ...
from pymongo import ...

# Internal modules
from backend.config import settings
from backend.services import ...
from backend.models import ...
```

---

## Technical Standards

### Database Operations

**PostgreSQL + pgvector:**
- Use SQLAlchemy ORM for all database operations
- Store vector embeddings with pgvector extension (1536 dimensions)
- Implement vector similarity search with cosine distance
- Use Alembic for database migrations

**Models:**
- User, APIKey, Collection, Document (core models)
- DocumentChunk (with vector embeddings)
- ChatSession, ChatMessage (chat history)
- All use UUID primary keys

### LLM Integration

**Supported Models:**
- LiteLLM supports 150+ models (OpenAI, Anthropic, Ollama, etc.)
- Default: OpenAI gpt-4o-mini
- Embeddings: OpenAI text-embedding-3-large (1536d)

**Streaming:**
- Server-Sent Events (SSE) for real-time streaming
- AsyncIteratorCallbackHandler for async streaming
- Streaming endpoints return EventSourceResponse

### Search Modes

**Five Search Modes:**
1. **Semantic**: Vector similarity with pgvector
2. **Keyword**: PostgreSQL full-text search (BM25)
3. **Hybrid**: RRF fusion of semantic + keyword
4. **Hierarchical**: Two-tier document → chunk retrieval
5. **Graph**: LightRAG knowledge graph traversal

### API Design

**Endpoint Pattern:**
```
POST /api/v1/{resource}
GET  /api/v1/{resource}
GET  /api/v1/{resource}/{id}
PATCH /api/v1/{resource}/{id}
DELETE /api/v1/{resource}/{id}
```

**Authentication:**
- Bearer token with API keys (format: `mn_...`)
- SHA-256 hashed keys in database
- Dependency injection for auth verification

**Response Format:**
- JSON for structured data
- SSE for streaming responses
- Pydantic schemas for validation
- Include metadata and pagination

**Error Handling:**
- FastAPI exception handlers
- Structured error responses
- Logging with context
- User-friendly error messages

---

## Development Workflows

### Adding New Features

1. **Query memory skill**: Understand existing patterns
2. **Plan with swarm**: Identify parallel operations
3. **Create service layer**: Add to appropriate service
4. **Implement API endpoint**: Follow RESTful patterns
5. **Add tests**: Unit and integration tests
6. **Run quality checks**: Lint + test + build
7. **Commit**: Clear message describing the feature

### Refactoring Code

1. **Check file size**: Is it approaching 300 lines?
2. **Identify boundaries**: Logical separation points
3. **Extract utilities**: Move to `*_utils.py`
4. **Update imports**: Fix all references
5. **Parallel edit**: Use swarm to edit multiple files
6. **Run tests**: Ensure nothing breaks
7. **Lint**: Verify code quality

### Fixing Bugs

1. **Query memory**: Check related changes in git history
2. **Add test**: Reproduce the bug in a test
3. **Fix issue**: Minimal change to resolve
4. **Verify test passes**: Confirm fix works
5. **Run full suite**: Ensure no regression
6. **Commit**: Reference issue/bug in message

### Adding Dependencies

1. **Verify necessity**: Is this dependency essential?
2. **Update requirements.txt**: Add with version pin
3. **Document usage**: Update relevant docstrings
4. **Test integration**: Ensure it works with existing code
5. **Commit**: Note the new dependency

---

## Quality Standards

### Testing Requirements

**Test Coverage:**
- Unit tests for all services
- Integration tests for API endpoints
- Test both sync and async modes
- Mock external dependencies (OpenAI, Ollama, MongoDB)

**Test Organization:**
```
tests/
├── unit/
│   ├── test_llm_service.py
│   ├── test_mongo_service.py
│   └── test_mnemosyne_service.py
├── integration/
│   └── test_api.py
└── conftest.py
```

### Linting Standards

**Tools:**
- `pylint` for code quality
- `black` for formatting (optional)
- `mypy` for type checking (optional)

**Run before every commit:**
```bash
python -m pylint src/
```

### Code Review Checklist

- [ ] File size under 300 lines
- [ ] No emojis in code
- [ ] No backward compatibility code
- [ ] Proper error handling
- [ ] Tests added/updated
- [ ] Linting passes
- [ ] Documentation updated
- [ ] Imports organized correctly

---

## Configuration Management

### Environment Variables

**Required:**
- `MONGODB_USERNAME`: MongoDB username
- `MONGODB_PASSWORD`: MongoDB password
- `OPENAI_API_KEY`: OpenAI API key
- `FIRECRAWL_API_KEY`: Firecrawl API key

**Configuration File:**
- Location: `src/config.py`
- Use dataclass structure
- Group related settings (MONGO, OPENAI, LLM, FIRECRAWL)

### Model Configuration

**Default Settings:**
```python
MODEL_NAME: str = "llama3.2"
TOKEN_LIMIT: int = 125000
TEMPERATURE: float = 0.1
OPENAI_TIMEOUT: int = 20
```

**Switching Models:**
- OpenAI: Set MODEL_NAME to "gpt-4o-mini", "gpt-4", etc.
- Ollama: Set MODEL_NAME to "llama3.2", "mistral", etc.
- Factory pattern automatically selects correct strategy

---

## Common Patterns

### Async Streaming Pattern

```python
async def stream_response(query: str) -> AsyncGenerator[str, None]:
    retrieved_info = service.retrieve_knowledge(query, mode)
    async for chunk in retrieved_info:
        if isinstance(chunk, str):
            yield f'data: {chunk}\n\n'
```

### Strategy Pattern (LLM)

```python
strategy = LLMStrategyFactory.create_strategy(model_name, config)
async for chunk in strategy.stream_answer_async(query, context):
    yield chunk
```

### Service Coordination

```python
class MnemsoyneService:
    def __init__(self, config: Config):
        self.llm_service = LLMService(config)
        self.mongo_service = MongoService(config)

    def retrieve_knowledge(self, query: str, mode: LLMMode):
        data = self.mongo_service.retrieve_data(query)
        return self.llm_service.query_knowledge(data, query, mode=mode)
```

---

## Git Workflow

### Commit Messages

**Format:**
```
[type]: brief description (max 72 chars)

- Detailed point 1
- Detailed point 2
- Detailed point 3
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring
- `test`: Adding tests
- `docs`: Documentation updates
- `chore`: Maintenance tasks

### Branch Strategy

- `main`: Production-ready code
- `claude/*`: Feature branches created by Claude Code
- Feature branches: Short-lived, focused changes

---

## Skill Integration

### Memory Skill

**Use before every task:**
- Query git history
- Search for patterns
- Review existing implementations
- Check documentation

**Command:**
```
Use the memory skill to understand [context]
```

### Swarm Skill

**Use for all multi-step tasks:**
- Identify independent operations
- Plan parallel execution
- Batch tool calls
- Maximize efficiency

**Command:**
```
Use swarm orchestration to [list of tasks]
```

---

## Examples

### Example 1: Adding New LLM Provider

1. **Memory**: Check how OpenAI and Ollama strategies are implemented
2. **Create Strategy**: Add new class extending `LLMStrategy`
3. **Update Factory**: Modify `LLMStrategyFactory.create_strategy()`
4. **Add Tests**: Test new strategy with mocks
5. **Parallel Execution**: Edit strategy file + factory + tests concurrently
6. **Quality Check**: Lint + test + build in parallel
7. **Commit**: `feat: add [provider] LLM strategy`

### Example 2: Refactoring Large File

1. **Memory**: Check why file is large, what it contains
2. **Identify Split**: Separate concerns (e.g., utils vs core logic)
3. **Swarm Execute**: Create utils file + edit main file + update imports (parallel)
4. **Test**: Run test suite to verify
5. **Lint**: Check code quality
6. **Commit**: `refactor: extract utilities from [filename]`

### Example 3: Bug Fix

1. **Memory**: Query git for recent changes to affected component
2. **Write Test**: Add test reproducing bug
3. **Fix Bug**: Minimal change to resolve issue
4. **Parallel Check**: Run test + lint + build
5. **Commit**: `fix: resolve [issue] in [component]`

---

## Resources

- **Documentation**: See README.md for setup and usage
- **Architecture**: Review service layer in `src/service/`
- **Examples**: Check existing implementations for patterns
- **Skills**: Use `.claude/skills/` for memory and swarm

---

**Remember:**
- Query memory BEFORE changes
- Use swarm orchestration ALWAYS
- Keep files under 300 lines
- No backward compatibility
- No emojis in code
- Lint + test + build after every task
