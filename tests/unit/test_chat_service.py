"""
Unit tests for ChatService

Tests:
- Chat session creation and retrieval
- Message saving
- RAG retrieval integration
- Streaming responses
- LiteLLM integration
- Error handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from uuid import uuid4

from backend.services.chat_service import ChatService
from backend.models.chat_session import ChatSession
from backend.models.chat_message import ChatMessage


@pytest.mark.unit
@pytest.mark.asyncio
class TestChatService:
    """Test suite for ChatService"""

    def test_init(self, db_session):
        """Test service initialization"""
        with patch('backend.services.chat_service.VectorSearchService'), \
             patch('backend.services.chat_service.OpenAIEmbedder'), \
             patch('backend.services.chat_service.RerankerService'), \
             patch('backend.services.chat_service.ChatLiteLLM'):

            service = ChatService(db_session)

            assert service.db == db_session
            assert service.search_service is not None
            assert service.embedder is not None
            assert service.reranker is not None
            assert service.llm is not None

    @patch('backend.services.chat_service.settings')
    @patch('backend.services.chat_service.ChatLiteLLM')
    def test_initialize_llm_with_model_string(self, mock_litellm_class, mock_settings, db_session):
        """Test LLM initialization with explicit model string"""
        mock_settings.LLM_MODEL_STRING = "openai/gpt-4o-mini"
        mock_settings.CHAT_TEMPERATURE = 0.7
        mock_settings.CHAT_MAX_TOKENS = 1000
        mock_settings.LLM_TIMEOUT = 60
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.OPENAI_API_KEY = "test_key"
        mock_settings.LLM_API_BASE = None

        with patch('backend.services.chat_service.VectorSearchService'), \
             patch('backend.services.chat_service.OpenAIEmbedder'), \
             patch('backend.services.chat_service.RerankerService'):

            service = ChatService(db_session)

            mock_litellm_class.assert_called_once()
            call_kwargs = mock_litellm_class.call_args[1]
            assert call_kwargs['model'] == "openai/gpt-4o-mini"
            assert call_kwargs['temperature'] == 0.7
            assert call_kwargs['max_tokens'] == 1000

    @patch('backend.services.chat_service.settings')
    @patch('backend.services.chat_service.ChatLiteLLM')
    def test_initialize_llm_build_from_provider(self, mock_litellm_class, mock_settings, db_session):
        """Test LLM initialization building from provider and model"""
        mock_settings.LLM_MODEL_STRING = ""
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.CHAT_MODEL = "gpt-4o-mini"
        mock_settings.CHAT_TEMPERATURE = 0.7
        mock_settings.CHAT_MAX_TOKENS = 1000
        mock_settings.LLM_TIMEOUT = 60
        mock_settings.OPENAI_API_KEY = "test_key"
        mock_settings.LLM_API_BASE = None

        with patch('backend.services.chat_service.VectorSearchService'), \
             patch('backend.services.chat_service.OpenAIEmbedder'), \
             patch('backend.services.chat_service.RerankerService'):

            service = ChatService(db_session)

            call_kwargs = mock_litellm_class.call_args[1]
            assert call_kwargs['model'] == "openai/gpt-4o-mini"

    async def test_chat_stream_new_session(self, db_session, test_user, test_collection):
        """Test chat streaming with new session"""
        session_id = uuid4()

        with patch('backend.services.chat_service.VectorSearchService') as mock_search, \
             patch('backend.services.chat_service.OpenAIEmbedder') as mock_embedder, \
             patch('backend.services.chat_service.RerankerService') as mock_reranker, \
             patch('backend.services.chat_service.ChatLiteLLM') as mock_llm:

            # Mock embedder
            embedder_instance = AsyncMock()
            embedder_instance.embed = AsyncMock(return_value=[0.1] * 1536)
            mock_embedder.return_value = embedder_instance

            # Mock search service
            search_instance = MagicMock()
            search_instance.hybrid_search.return_value = [
                {
                    'chunk_id': str(uuid4()),
                    'content': 'Test content',
                    'chunk_index': 0,
                    'score': 0.95,
                    'metadata': {},
                    'chunk_metadata': {},
                    'document': {
                        'id': str(uuid4()),
                        'title': 'Test Doc',
                        'filename': 'test.pdf'
                    },
                    'collection_id': str(test_collection.id)
                }
            ]
            mock_search.return_value = search_instance

            # Mock reranker
            reranker_instance = MagicMock()
            reranker_instance.is_available.return_value = False
            mock_reranker.return_value = reranker_instance

            # Mock LLM streaming
            async def mock_stream(messages):
                chunks = ["Hello", " world"]
                for text in chunks:
                    chunk = MagicMock()
                    chunk.content = text
                    yield chunk

            llm_instance = MagicMock()
            llm_instance.astream = mock_stream
            mock_llm.return_value = llm_instance

            service = ChatService(db_session)

            # Collect streamed events
            events = []
            async for event in service.chat_stream(
                session_id=session_id,
                user_message="Test message",
                user_id=test_user.id,
                collection_id=test_collection.id,
                top_k=5
            ):
                events.append(event)

            # Verify events
            delta_events = [e for e in events if e['type'] == 'delta']
            sources_events = [e for e in events if e['type'] == 'sources']
            done_events = [e for e in events if e['type'] == 'done']

            assert len(delta_events) == 2
            assert len(sources_events) == 1
            assert len(done_events) == 1

            # Verify session created
            session = db_session.query(ChatSession).filter(
                ChatSession.id == session_id
            ).first()
            assert session is not None

            # Verify messages saved
            messages = db_session.query(ChatMessage).filter(
                ChatMessage.session_id == session_id
            ).all()
            assert len(messages) == 2  # User + Assistant

    async def test_chat_stream_existing_session(self, db_session, test_chat_session, test_user):
        """Test chat streaming with existing session"""
        with patch('backend.services.chat_service.VectorSearchService') as mock_search, \
             patch('backend.services.chat_service.OpenAIEmbedder') as mock_embedder, \
             patch('backend.services.chat_service.RerankerService') as mock_reranker, \
             patch('backend.services.chat_service.ChatLiteLLM') as mock_llm:

            # Mock embedder
            embedder_instance = AsyncMock()
            embedder_instance.embed = AsyncMock(return_value=[0.1] * 1536)
            mock_embedder.return_value = embedder_instance

            # Mock search
            search_instance = MagicMock()
            search_instance.hybrid_search.return_value = []
            mock_search.return_value = search_instance

            # Mock reranker
            reranker_instance = MagicMock()
            reranker_instance.is_available.return_value = False
            mock_reranker.return_value = reranker_instance

            # Mock LLM
            async def mock_stream(messages):
                chunk = MagicMock()
                chunk.content = "Response"
                yield chunk

            llm_instance = MagicMock()
            llm_instance.astream = mock_stream
            mock_llm.return_value = llm_instance

            service = ChatService(db_session)

            events = []
            async for event in service.chat_stream(
                session_id=test_chat_session.id,
                user_message="Follow-up question",
                user_id=test_user.id,
                top_k=5
            ):
                events.append(event)

            # Verify session not duplicated
            sessions = db_session.query(ChatSession).filter(
                ChatSession.id == test_chat_session.id
            ).all()
            assert len(sessions) == 1

    def test_get_history(self, db_session, test_chat_session):
        """Test retrieving conversation history"""
        # Add test messages
        for i in range(5):
            msg = ChatMessage(
                session_id=test_chat_session.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}"
            )
            db_session.add(msg)
        db_session.commit()

        with patch('backend.services.chat_service.VectorSearchService'), \
             patch('backend.services.chat_service.OpenAIEmbedder'), \
             patch('backend.services.chat_service.RerankerService'), \
             patch('backend.services.chat_service.ChatLiteLLM'):

            service = ChatService(db_session)
            history = service._get_history(test_chat_session.id, limit=3)

            assert len(history) == 3
            # Should be in chronological order
            assert history[0].content == "Message 2"

    def test_build_context(self, db_session):
        """Test building context from search results"""
        with patch('backend.services.chat_service.VectorSearchService'), \
             patch('backend.services.chat_service.OpenAIEmbedder'), \
             patch('backend.services.chat_service.RerankerService'), \
             patch('backend.services.chat_service.ChatLiteLLM'):

            service = ChatService(db_session)

            results = [
                {
                    'content': 'First chunk content',
                    'document': {'filename': 'doc1.pdf'}
                },
                {
                    'content': 'Second chunk content',
                    'document': {'filename': 'doc2.pdf'}
                }
            ]

            context = service._build_context(results)

            assert 'First chunk content' in context
            assert 'Second chunk content' in context
            assert 'doc1.pdf' in context
            assert 'doc2.pdf' in context
            assert '[1]' in context
            assert '[2]' in context

    def test_build_context_empty(self, db_session):
        """Test building context with empty results"""
        with patch('backend.services.chat_service.VectorSearchService'), \
             patch('backend.services.chat_service.OpenAIEmbedder'), \
             patch('backend.services.chat_service.RerankerService'), \
             patch('backend.services.chat_service.ChatLiteLLM'):

            service = ChatService(db_session)
            context = service._build_context([])

            assert context == ""

    def test_build_langchain_messages(self, db_session, test_chat_session):
        """Test building LangChain message format"""
        # Add history
        msg1 = ChatMessage(
            session_id=test_chat_session.id,
            role="user",
            content="What is RAG?"
        )
        msg2 = ChatMessage(
            session_id=test_chat_session.id,
            role="assistant",
            content="RAG is Retrieval Augmented Generation"
        )
        db_session.add_all([msg1, msg2])
        db_session.commit()

        with patch('backend.services.chat_service.VectorSearchService'), \
             patch('backend.services.chat_service.OpenAIEmbedder'), \
             patch('backend.services.chat_service.RerankerService'), \
             patch('backend.services.chat_service.ChatLiteLLM'):

            service = ChatService(db_session)
            history = [msg1, msg2]

            messages = service._build_langchain_messages(
                history,
                "How does it work?",
                "Context: RAG combines retrieval and generation"
            )

            # Should have system + history + current message
            assert len(messages) >= 3
            assert messages[0].content.startswith("You are a helpful AI assistant")

    def test_build_langchain_messages_no_context(self, db_session):
        """Test building messages without context"""
        with patch('backend.services.chat_service.VectorSearchService'), \
             patch('backend.services.chat_service.OpenAIEmbedder'), \
             patch('backend.services.chat_service.RerankerService'), \
             patch('backend.services.chat_service.ChatLiteLLM'):

            service = ChatService(db_session)

            messages = service._build_langchain_messages(
                [],
                "Test question",
                ""
            )

            # System + user message
            assert len(messages) == 2
            assert "Test question" in messages[-1].content
