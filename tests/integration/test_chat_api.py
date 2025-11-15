"""
Integration tests for Chat API endpoints

Tests:
- /api/v1/chat endpoint with SSE streaming
- /api/v1/chat/sessions list endpoint
- /api/v1/chat/sessions/{id}/messages endpoint
- /api/v1/chat/sessions/{id} delete endpoint
- Authentication
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from uuid import uuid4
from fastapi.testclient import TestClient
import json

from backend.main import app
from backend.api.deps import get_current_user, get_db
from backend.models.chat_session import ChatSession
from backend.models.chat_message import ChatMessage


@pytest.mark.integration
class TestChatAPI:
    """Integration tests for Chat API"""

    @pytest.fixture
    def client(self, db_session, test_user):
        """Create test client with mocked dependencies"""

        def override_get_db():
            try:
                yield db_session
            finally:
                pass

        def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user

        client = TestClient(app)
        yield client

        app.dependency_overrides.clear()

    @patch('backend.services.chat_service.VectorSearchService')
    @patch('backend.services.chat_service.OpenAIEmbedder')
    @patch('backend.services.chat_service.RerankerService')
    @patch('backend.services.chat_service.ChatLiteLLM')
    def test_chat_streaming(
        self,
        mock_llm,
        mock_reranker,
        mock_embedder,
        mock_search,
        client,
        test_user,
        test_collection
    ):
        """Test chat endpoint with streaming"""
        # Mock embedder
        embedder_instance = AsyncMock()
        embedder_instance.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embedder.return_value = embedder_instance

        # Mock search
        search_instance = Mock()
        search_instance.hybrid_search.return_value = [
            {
                'chunk_id': str(uuid4()),
                'content': 'RAG is Retrieval Augmented Generation',
                'chunk_index': 0,
                'score': 0.95,
                'metadata': {},
                'chunk_metadata': {},
                'document': {
                    'id': str(uuid4()),
                    'title': 'RAG Guide',
                    'filename': 'rag.pdf'
                },
                'collection_id': str(test_collection.id)
            }
        ]
        mock_search.return_value = search_instance

        # Mock reranker
        reranker_instance = Mock()
        reranker_instance.is_available.return_value = False
        mock_reranker.return_value = reranker_instance

        # Mock LLM streaming
        async def mock_stream(messages):
            chunks = ["RAG ", "is ", "a ", "technique"]
            for text in chunks:
                chunk = MagicMock()
                chunk.content = text
                yield chunk

        llm_instance = MagicMock()
        llm_instance.astream = mock_stream
        mock_llm.return_value = llm_instance

        response = client.post(
            "/api/v1/chat",
            json={
                "message": "What is RAG?",
                "session_id": None,
                "collection_id": str(test_collection.id),
                "top_k": 5,
                "stream": True
            },
            headers={"Accept": "text/event-stream"}
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        # Parse SSE events
        events = []
        for line in response.text.split('\n\n'):
            if line.startswith('data: '):
                try:
                    event_data = json.loads(line[6:])
                    events.append(event_data)
                except json.JSONDecodeError:
                    pass

        # Should have delta, sources, and done events
        delta_events = [e for e in events if e.get('type') == 'delta']
        sources_events = [e for e in events if e.get('type') == 'sources']
        done_events = [e for e in events if e.get('type') == 'done']

        assert len(delta_events) > 0
        assert len(sources_events) == 1
        assert len(done_events) == 1

    def test_list_sessions(self, client, test_user, db_session):
        """Test listing chat sessions"""
        # Create test sessions
        for i in range(3):
            session = ChatSession(
                id=uuid4(),
                user_id=test_user.id,
                title=f"Session {i}"
            )
            db_session.add(session)
        db_session.commit()

        response = client.get("/api/v1/chat/sessions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_list_sessions_pagination(self, client, test_user, db_session):
        """Test session list pagination"""
        # Create 10 sessions
        for i in range(10):
            session = ChatSession(
                id=uuid4(),
                user_id=test_user.id,
                title=f"Session {i}"
            )
            db_session.add(session)
        db_session.commit()

        # Test limit
        response = client.get("/api/v1/chat/sessions?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

        # Test offset
        response = client.get("/api/v1/chat/sessions?limit=5&offset=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5

    def test_list_sessions_empty(self, client):
        """Test listing sessions when none exist"""
        response = client.get("/api/v1/chat/sessions")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_session_messages(self, client, test_user, db_session):
        """Test getting messages for a session"""
        # Create session with messages
        session = ChatSession(
            id=uuid4(),
            user_id=test_user.id,
            title="Test Session"
        )
        db_session.add(session)
        db_session.commit()

        messages_data = [
            ("user", "Hello"),
            ("assistant", "Hi there!"),
            ("user", "How are you?"),
            ("assistant", "I'm doing well!")
        ]

        for role, content in messages_data:
            msg = ChatMessage(
                session_id=session.id,
                role=role,
                content=content
            )
            db_session.add(msg)
        db_session.commit()

        response = client.get(f"/api/v1/chat/sessions/{session.id}/messages")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4
        assert data[0]["role"] == "user"
        assert data[0]["content"] == "Hello"

    def test_get_session_messages_not_found(self, client):
        """Test getting messages for non-existent session"""
        random_id = uuid4()
        response = client.get(f"/api/v1/chat/sessions/{random_id}/messages")

        assert response.status_code == 404

    def test_get_session_messages_unauthorized(self, client, db_session):
        """Test getting messages for session owned by another user"""
        # Create session for different user
        other_user_id = uuid4()
        session = ChatSession(
            id=uuid4(),
            user_id=other_user_id,
            title="Other User Session"
        )
        db_session.add(session)
        db_session.commit()

        response = client.get(f"/api/v1/chat/sessions/{session.id}/messages")

        assert response.status_code == 404  # Not found (access denied)

    def test_delete_session(self, client, test_user, db_session):
        """Test deleting a chat session"""
        # Create session
        session = ChatSession(
            id=uuid4(),
            user_id=test_user.id,
            title="Session to Delete"
        )
        db_session.add(session)
        db_session.commit()

        session_id = session.id

        response = client.delete(f"/api/v1/chat/sessions/{session_id}")

        assert response.status_code == 204

        # Verify session deleted
        deleted_session = db_session.query(ChatSession).filter(
            ChatSession.id == session_id
        ).first()
        assert deleted_session is None

    def test_delete_session_with_messages(self, client, test_user, db_session):
        """Test deleting session cascades to messages"""
        # Create session with messages
        session = ChatSession(
            id=uuid4(),
            user_id=test_user.id,
            title="Session with Messages"
        )
        db_session.add(session)
        db_session.commit()

        msg = ChatMessage(
            session_id=session.id,
            role="user",
            content="Test message"
        )
        db_session.add(msg)
        db_session.commit()

        session_id = session.id

        response = client.delete(f"/api/v1/chat/sessions/{session_id}")

        assert response.status_code == 204

        # Verify messages also deleted
        messages = db_session.query(ChatMessage).filter(
            ChatMessage.session_id == session_id
        ).all()
        assert len(messages) == 0

    def test_delete_session_not_found(self, client):
        """Test deleting non-existent session"""
        random_id = uuid4()
        response = client.delete(f"/api/v1/chat/sessions/{random_id}")

        assert response.status_code == 404

    def test_delete_session_unauthorized(self, client, db_session):
        """Test deleting session owned by another user"""
        other_user_id = uuid4()
        session = ChatSession(
            id=uuid4(),
            user_id=other_user_id,
            title="Other User Session"
        )
        db_session.add(session)
        db_session.commit()

        response = client.delete(f"/api/v1/chat/sessions/{session.id}")

        assert response.status_code == 404

    def test_chat_without_authentication(self):
        """Test chat without authentication"""
        client = TestClient(app)

        response = client.post(
            "/api/v1/chat",
            json={
                "message": "test",
                "stream": True
            }
        )

        assert response.status_code in [401, 403]

    @patch('backend.services.chat_service.VectorSearchService')
    @patch('backend.services.chat_service.OpenAIEmbedder')
    @patch('backend.services.chat_service.RerankerService')
    @patch('backend.services.chat_service.ChatLiteLLM')
    def test_chat_creates_new_session(
        self,
        mock_llm,
        mock_reranker,
        mock_embedder,
        mock_search,
        client,
        test_user,
        db_session
    ):
        """Test chat creates new session when session_id is null"""
        # Setup mocks
        embedder_instance = AsyncMock()
        embedder_instance.embed = AsyncMock(return_value=[0.1] * 1536)
        mock_embedder.return_value = embedder_instance

        search_instance = Mock()
        search_instance.hybrid_search.return_value = []
        mock_search.return_value = search_instance

        reranker_instance = Mock()
        reranker_instance.is_available.return_value = False
        mock_reranker.return_value = reranker_instance

        async def mock_stream(messages):
            chunk = MagicMock()
            chunk.content = "Response"
            yield chunk

        llm_instance = MagicMock()
        llm_instance.astream = mock_stream
        mock_llm.return_value = llm_instance

        initial_session_count = db_session.query(ChatSession).count()

        response = client.post(
            "/api/v1/chat",
            json={
                "message": "New conversation",
                "session_id": None,
                "stream": True
            }
        )

        assert response.status_code == 200

        # Verify new session created
        final_session_count = db_session.query(ChatSession).count()
        assert final_session_count == initial_session_count + 1

    def test_chat_request_validation(self, client):
        """Test chat request validation"""
        # Missing message
        response = client.post(
            "/api/v1/chat",
            json={
                "stream": True
            }
        )
        assert response.status_code == 422

    def test_session_response_structure(self, client, test_user, db_session):
        """Test session response has correct structure"""
        session = ChatSession(
            id=uuid4(),
            user_id=test_user.id,
            title="Test Session"
        )
        db_session.add(session)
        db_session.commit()

        response = client.get("/api/v1/chat/sessions")

        assert response.status_code == 200
        data = response.json()

        if data:
            session_data = data[0]
            assert "id" in session_data
            assert "user_id" in session_data
            assert "title" in session_data
            assert "created_at" in session_data
            assert "message_count" in session_data
