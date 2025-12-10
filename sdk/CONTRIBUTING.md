# Contributing to Mnemosyne Python SDK

Thank you for your interest in contributing to the Mnemosyne Python SDK.

## Development Setup

### Prerequisites

- Python 3.9 or higher
- Poetry (for dependency management)

### Getting Started

```bash
# Clone the repository
git clone https://github.com/raghavpatnecha/Mnemosyne.git
cd Mnemosyne/sdk

# Install dependencies with Poetry
poetry install

# Activate the virtual environment
poetry shell
```

## Development Workflow

### Code Style

This project uses Black, Ruff, and MyPy for code quality:

```bash
# Format code with Black
poetry run black mnemosyne tests

# Check linting with Ruff
poetry run ruff check mnemosyne tests

# Fix auto-fixable issues
poetry run ruff check --fix mnemosyne tests

# Type check with MyPy
poetry run mypy mnemosyne
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=mnemosyne --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_client.py

# Run tests matching pattern
poetry run pytest -k "test_collections"
```

### Building

```bash
# Build the package
poetry build

# Check package is valid
pip install twine
twine check dist/*
```

## Project Structure

```
sdk/
├── mnemosyne/              # Source code
│   ├── __init__.py         # Main exports
│   ├── client.py           # Synchronous client
│   ├── async_client.py     # Asynchronous client
│   ├── _base_client.py     # Base HTTP client
│   ├── _streaming.py       # SSE streaming utilities
│   ├── exceptions.py       # Custom exceptions
│   ├── version.py          # SDK version
│   ├── resources/          # API resource classes
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── collections.py
│   │   ├── documents.py
│   │   └── retrievals.py
│   └── types/              # Pydantic models
│       ├── auth.py
│       ├── chat.py
│       ├── collections.py
│       ├── documents.py
│       └── retrievals.py
├── tests/                  # Test files
│   ├── conftest.py         # Pytest fixtures
│   └── unit/               # Unit tests
├── examples/               # Usage examples
├── pyproject.toml          # Project configuration
└── README.md
```

## Making Changes

### Adding a New Feature

1. Create a feature branch from `main`
2. Implement your changes with tests
3. Ensure all tests pass: `poetry run pytest`
4. Format code: `poetry run black mnemosyne tests`
5. Check linting: `poetry run ruff check mnemosyne tests`
6. Check types: `poetry run mypy mnemosyne`
7. Update CHANGELOG.md
8. Submit a pull request

### Writing Tests

Tests use pytest and pytest-httpx for mocking HTTP requests:

```python
import pytest
from mnemosyne import Client

def test_my_feature(mock_client):
    """Test description."""
    # Arrange
    expected = {"key": "value"}

    # Act
    result = mock_client.some_method()

    # Assert
    assert result == expected
```

For async tests:

```python
import pytest
from mnemosyne import AsyncClient

@pytest.mark.asyncio
async def test_async_feature(mock_async_client):
    """Test async feature."""
    result = await mock_async_client.some_method()
    assert result is not None
```

### Type Annotations

All code should be fully typed:

```python
from typing import Optional, List
from pydantic import BaseModel

def my_function(
    param1: str,
    param2: Optional[int] = None,
) -> List[str]:
    """Function with proper type annotations."""
    ...
```

## Pull Request Guidelines

1. **Title**: Use a clear, descriptive title
2. **Description**: Explain what and why, not just how
3. **Tests**: Include tests for new functionality
4. **Types**: Ensure full type coverage
5. **Docs**: Update README and docstrings as needed
6. **Changelog**: Add entry to CHANGELOG.md

## Version Bumping

Version is managed in `mnemosyne/version.py` and `pyproject.toml`. When releasing:

1. Update version in both files
2. Update CHANGELOG.md with release date
3. Tag the release: `git tag v0.x.x`

## Code of Conduct

Please be respectful and inclusive in all interactions.

## Questions?

- Open a [GitHub Issue](https://github.com/raghavpatnecha/Mnemosyne/issues)
- Join our [Discussions](https://github.com/raghavpatnecha/Mnemosyne/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
