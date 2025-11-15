# Mnemosyne Test Suite

Comprehensive testing infrastructure for the Mnemosyne RAG API.

## Overview

This test suite provides comprehensive coverage for Mnemosyne's services and API endpoints:

- **Unit Tests**: Test individual components in isolation with mocked dependencies
- **Integration Tests**: Test API endpoints with request/response flows
- **Fixtures**: Reusable test data and mocked services

## Test Structure

```
tests/
├── conftest.py                          # Shared fixtures and configuration
├── unit/                                # Unit tests
│   ├── test_reranker_service.py        # Reranker service tests
│   ├── test_chat_service.py            # Chat service tests
│   ├── test_cache_service.py           # Cache service tests
│   ├── test_embedder.py                # Embedder tests
│   ├── test_vector_search.py           # Vector search tests
│   └── test_query_reformulation.py     # Query reformulation tests
├── integration/                         # Integration tests
│   ├── test_retrieval_api.py           # Retrieval API endpoint tests
│   └── test_chat_api.py                # Chat API endpoint tests
└── README.md                            # This file
```

## Installation

Tests are included in the dev dependencies. Install with:

```bash
poetry install --with dev
```

Dependencies installed:
- `pytest` - Test framework
- `pytest-asyncio` - Async test support
- `httpx` - HTTP client for FastAPI testing

## Running Tests

### Run All Tests

```bash
pytest
```

### Run Unit Tests Only

```bash
pytest tests/unit/
```

### Run Integration Tests Only

```bash
pytest tests/integration/
```

### Run Specific Test File

```bash
pytest tests/unit/test_reranker_service.py
```

### Run Specific Test

```bash
pytest tests/unit/test_cache_service.py::TestCacheService::test_get_embedding_cache_hit
```

### Run Tests by Marker

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only async tests
pytest -m asyncio
```

### Verbose Output

```bash
pytest -v
```

### Show Print Statements

```bash
pytest -s
```

### Stop on First Failure

```bash
pytest -x
```

### Run Last Failed Tests

```bash
pytest --lf
```

## Test Coverage

### Generate Coverage Report

```bash
# Install coverage plugin
poetry add --group dev pytest-cov

# Run with coverage
pytest --cov=backend --cov-report=html --cov-report=term-missing
```

View HTML report:
```bash
open htmlcov/index.html
```

### Expected Coverage

The test suite aims for:
- **Services**: 80%+ coverage
- **API Endpoints**: 70%+ coverage
- **Critical Paths**: 90%+ coverage

## Test Organization

### Unit Tests

Unit tests focus on individual components with mocked external dependencies:

- **Mocked Dependencies**:
  - OpenAI API calls
  - Redis connections
  - Database queries (where appropriate)
  - External reranker libraries

- **What's Tested**:
  - Business logic correctness
  - Error handling
  - Edge cases
  - Return value structures

### Integration Tests

Integration tests verify API endpoints with real request/response flows:

- **Mocked Dependencies**:
  - External API calls (OpenAI, etc.)
  - Time-consuming operations

- **Real Components**:
  - FastAPI routing
  - Request validation
  - Response formatting
  - Database sessions (in-memory)

## Available Fixtures

### Database Fixtures

- `test_db_engine`: In-memory SQLite database
- `db_session`: Database session for each test
- `test_user`: Sample user account
- `test_collection`: Sample collection
- `test_document`: Sample document
- `test_chunks`: Sample document chunks with embeddings
- `test_chat_session`: Sample chat session

### Mock Fixtures

- `mock_redis`: Mocked Redis connection
- `mock_openai_client`: Mocked OpenAI AsyncClient
- `mock_litellm_stream`: Mocked LiteLLM streaming
- `mock_reranker`: Mocked reranker instance
- `mock_reranker_document`: Mocked reranker Document class

### Sample Data Fixtures

- `sample_embedding`: Sample 1536-dim embedding vector
- `sample_search_results`: Sample search result data

## Writing New Tests

### Unit Test Template

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch

@pytest.mark.unit
class TestYourService:
    """Test suite for YourService"""

    def test_basic_functionality(self):
        """Test description"""
        # Arrange
        service = YourService()

        # Act
        result = service.method()

        # Assert
        assert result == expected_value

    @pytest.mark.asyncio
    async def test_async_method(self):
        """Test async method"""
        service = YourService()
        result = await service.async_method()
        assert result is not None
```

### Integration Test Template

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
class TestYourAPI:
    """Integration tests for Your API"""

    def test_endpoint(self, client, test_user):
        """Test API endpoint"""
        response = client.post(
            "/api/v1/endpoint",
            json={"key": "value"}
        )

        assert response.status_code == 200
        assert "expected_field" in response.json()
```

## Continuous Integration

### GitHub Actions

Example workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install --with dev
      - name: Run tests
        run: poetry run pytest --cov=backend
```

## Troubleshooting

### Import Errors

If you get import errors, ensure Python path is set:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

Or use pytest's pythonpath:
```bash
pytest --pythonpath=.
```

### Database Errors

Tests use in-memory SQLite, which doesn't support all PostgreSQL features (like pgvector).
Some tests mock database queries to work around this.

### Async Test Warnings

If you see warnings about async tests, ensure you have:
```bash
poetry add --group dev pytest-asyncio
```

And that `pytest.ini` has:
```ini
asyncio_mode = auto
```

### Fixture Not Found

If pytest can't find a fixture, ensure:
1. Fixture is defined in `conftest.py` or test file
2. Scope is appropriate (function, class, module, session)
3. Name is spelled correctly

## Best Practices

### 1. Keep Tests Independent

Each test should be able to run independently:
```python
# Good
def test_feature(db_session):
    user = User(email="test@example.com")
    db_session.add(user)
    db_session.commit()

# Bad - depends on previous test
def test_feature():
    user = User.query.first()  # Assumes user exists
```

### 2. Use Descriptive Names

```python
# Good
def test_cache_returns_none_when_key_not_found()

# Bad
def test_cache_1()
```

### 3. Mock External Services

Always mock:
- API calls (OpenAI, etc.)
- Redis connections
- File I/O
- Time-dependent functions

### 4. Test Error Cases

```python
def test_service_handles_api_error(mock_openai):
    mock_openai.side_effect = Exception("API Error")

    service = YourService()
    result = service.call_api()

    # Should handle gracefully
    assert result is None
```

### 5. Use Markers

Organize tests with markers:
```python
@pytest.mark.unit
@pytest.mark.slow
def test_expensive_operation():
    ...
```

## Performance

### Fast Tests

Most unit tests should run in < 100ms each.

### Parallel Execution

For faster execution, install pytest-xdist:
```bash
poetry add --group dev pytest-xdist
pytest -n auto  # Use all CPU cores
```

### Skip Slow Tests

Mark slow tests and skip them during development:
```python
@pytest.mark.slow
def test_long_running_task():
    ...
```

Run without slow tests:
```bash
pytest -m "not slow"
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Mnemosyne Documentation](../README.md)

## Contributing

When adding new features to Mnemosyne:

1. Write unit tests for new services/functions
2. Write integration tests for new API endpoints
3. Ensure tests pass: `pytest`
4. Check coverage: `pytest --cov=backend`
5. Follow existing patterns in test files

## Support

For issues or questions about testing:
1. Check this README
2. Review existing test files for examples
3. Consult pytest documentation
4. Open an issue in the repository
