"""
Pytest configuration and shared fixtures for Mnemosyne tests

Provides:
- Mock database sessions
- Mock Redis connections
- Mock OpenAI/LiteLLM API calls
- Test users, collections, documents, and chunks
- Sample data for testing
"""

import pytest
from typing import Generator, List, Dict
from unittest.mock import Mock, MagicMock, AsyncMock, patch
from uuid import uuid4, UUID
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.database import Base
from backend.models.user import User
from backend.models.collection import Collection
from backend.models.document import Document
from backend.models.chunk import DocumentChunk
from backend.models.chat_session import ChatSession
from backend.models.chat_message import ChatMessage


@pytest.fixture(scope="session")
def test_db_engine_sqlite():
    """Create in-memory SQLite database for unit tests (fast, isolated)"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="session")
def test_db_engine_postgres():
    """
    Create PostgreSQL test database for integration tests (real database).
    Requires PostgreSQL running (via docker-compose).
    Uses test database: mnemosyne_test
    """
    from backend.config import settings
    from sqlalchemy.engine.url import make_url

    # Parse the database URL and change only the database name
    url = make_url(settings.DATABASE_URL)
    url = url.set(database="mnemosyne_test")

    engine = create_engine(url)

    # Create all tables
    Base.metadata.create_all(bind=engine)

    yield engine

    # Cleanup: Drop all tables after session
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_session(request) -> Generator[Session, None, None]:
    """
    Create a database session for each test with transaction isolation.
    ALL tests now use real PostgreSQL (both unit and integration).
    Requires PostgreSQL running via docker-compose.

    Uses nested transactions (SAVEPOINT) to ensure complete rollback
    after each test, providing proper test isolation.
    """
    from sqlalchemy import event

    # All tests use PostgreSQL
    engine = request.getfixturevalue('test_db_engine_postgres')

    # Create connection and begin outer transaction
    connection = engine.connect()
    transaction = connection.begin()

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection
    )
    session = TestingSessionLocal()

    # Begin nested transaction (SAVEPOINT) for the test
    session.begin_nested()

    # Each time the SAVEPOINT is committed, restart it
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if transaction.nested and not transaction._parent.nested:
            session.begin_nested()

    try:
        yield session
    finally:
        # Always rollback the nested transaction (test data)
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def test_user(db_session) -> User:
    """Create a test user"""
    user = User(
        id=uuid4(),
        email="test@example.com",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyWuL7l2JhSa",
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_collection(db_session, test_user) -> Collection:
    """Create a test collection"""
    collection = Collection(
        id=uuid4(),
        name="Test Collection",
        description="A test collection for unit tests",
        user_id=test_user.id
    )
    db_session.add(collection)
    db_session.commit()
    db_session.refresh(collection)
    return collection


@pytest.fixture
def test_document(db_session, test_user, test_collection) -> Document:
    """Create a test document"""
    import hashlib
    document = Document(
        id=uuid4(),
        title="Test Document",
        filename="test_doc.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        user_id=test_user.id,
        collection_id=test_collection.id,
        status="completed",
        content_hash=hashlib.sha256(b"test content").hexdigest(),
        metadata_={"source": "test"}
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


@pytest.fixture
def test_chunks(db_session, test_user, test_collection, test_document) -> List[DocumentChunk]:
    """Create test document chunks with embeddings"""
    chunks = []
    for i in range(5):
        chunk = DocumentChunk(
            id=uuid4(),
            document_id=test_document.id,
            collection_id=test_collection.id,
            user_id=test_user.id,
            content=f"This is test chunk {i} with some sample content for testing.",
            chunk_index=i,
            embedding=[0.1] * 1536,  # Mock embedding vector
            metadata={"page": i + 1},
            chunk_metadata={"tokens": 10}
        )
        db_session.add(chunk)
        chunks.append(chunk)

    db_session.commit()
    for chunk in chunks:
        db_session.refresh(chunk)
    return chunks


@pytest.fixture
def test_chat_session(db_session, test_user, test_collection) -> ChatSession:
    """Create a test chat session"""
    session = ChatSession(
        id=uuid4(),
        user_id=test_user.id,
        collection_id=test_collection.id,
        title="Test Chat Session"
    )
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)
    return session


@pytest.fixture
def sample_embedding() -> List[float]:
    """Sample embedding vector (1536 dimensions)"""
    return [0.1] * 1536


@pytest.fixture
def sample_search_results() -> List[Dict]:
    """Sample search results"""
    return [
        {
            'chunk_id': str(uuid4()),
            'content': 'Machine learning is a subset of artificial intelligence.',
            'chunk_index': 0,
            'score': 0.95,
            'metadata': {'page': 1},
            'chunk_metadata': {'tokens': 10},
            'document': {
                'id': str(uuid4()),
                'title': 'AI Basics',
                'filename': 'ai_basics.pdf'
            },
            'collection_id': str(uuid4())
        },
        {
            'chunk_id': str(uuid4()),
            'content': 'Deep learning uses neural networks with multiple layers.',
            'chunk_index': 1,
            'score': 0.87,
            'metadata': {'page': 2},
            'chunk_metadata': {'tokens': 9},
            'document': {
                'id': str(uuid4()),
                'title': 'AI Basics',
                'filename': 'ai_basics.pdf'
            },
            'collection_id': str(uuid4())
        }
    ]


@pytest.fixture
def mock_redis():
    """Mock Redis connection for unit tests"""
    mock = MagicMock()
    mock.ping.return_value = True
    mock.get.return_value = None
    mock.setex.return_value = True
    mock.delete.return_value = 1
    mock.keys.return_value = []
    mock.flushdb.return_value = True
    mock.info.return_value = {
        'db0': {'keys': 0},
        'used_memory_human': '1M',
        'keyspace_hits': 10,
        'keyspace_misses': 5
    }
    return mock


@pytest.fixture
def real_redis(request):
    """
    Real Redis connection for integration tests.
    Uses test database (db index 1) to avoid conflicts with dev data.
    """
    is_integration = request.node.get_closest_marker('integration') is not None

    if not is_integration:
        # Unit tests should use mock_redis, not this fixture
        pytest.skip("real_redis fixture only for integration tests")

    import redis
    from backend.config import settings

    # Connect to Redis test database (db=1, not db=0)
    redis_url = settings.REDIS_URL.replace('/0', '/1')
    client = redis.from_url(redis_url, decode_responses=True)

    # Test connection
    try:
        client.ping()
    except redis.ConnectionError:
        pytest.skip("Redis not available for integration tests")

    # Cleanup before test
    client.flushdb()

    yield client

    # Cleanup after test
    client.flushdb()
    client.close()


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI AsyncClient"""
    mock_client = AsyncMock()

    # Mock embeddings.create
    mock_embedding_response = MagicMock()
    mock_embedding_response.data = [
        MagicMock(embedding=[0.1] * 1536)
    ]
    mock_client.embeddings.create = AsyncMock(return_value=mock_embedding_response)

    # Mock chat.completions.create
    mock_chat_response = MagicMock()
    mock_chat_response.choices = [
        MagicMock(message=MagicMock(content="This is a test response"))
    ]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

    return mock_client


@pytest.fixture
def mock_litellm_stream():
    """Mock LiteLLM streaming response"""
    async def mock_stream():
        chunks = ["This ", "is ", "a ", "test ", "response."]
        for chunk_text in chunks:
            chunk = MagicMock()
            chunk.content = chunk_text
            yield chunk

    return mock_stream


@pytest.fixture
def mock_reranker():
    """Mock reranker from rerankers library"""
    mock = MagicMock()

    # Mock rank method
    def mock_rank(query, docs):
        result = MagicMock()
        result.results = []
        for i, doc in enumerate(docs):
            rank_result = MagicMock()
            rank_result.document = doc
            rank_result.score = 1.0 - (i * 0.1)  # Descending scores
            rank_result.rank = i + 1
            result.results.append(rank_result)
        return result

    mock.rank = mock_rank
    return mock


@pytest.fixture
def mock_reranker_document():
    """Mock Document class from rerankers library"""
    def create_document(text, doc_id, metadata):
        doc = MagicMock()
        doc.text = text
        doc.doc_id = doc_id
        doc.metadata = metadata
        return doc

    return create_document


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers", "unit: Unit tests for individual components"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests for API endpoints"
    )
    config.addinivalue_line(
        "markers", "asyncio: Async tests requiring asyncio event loop"
    )
