"""
Unit tests for ChatService

Tests:
- Chat service initialization
- LLM configuration with model strings
- Context building
- Message building for LangChain
- Session management
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
        with patch('backend.services.chat_service.ChatLiteLLM') as mock_llm, \
             patch('backend.services.chat_service.PromptBuilder') as mock_builder, \
             patch('backend.services.chat_service.DeepReasoningService') as mock_reasoning, \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            assert service.db == db_session
            assert service.llm is not None
            assert service.prompt_builder is not None
            assert service.reasoning_service is not None

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

        with patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

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

        with patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            call_kwargs = mock_litellm_class.call_args[1]
            assert call_kwargs['model'] == "openai/gpt-4o-mini"

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

        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)
            history = service._get_history(test_chat_session.id, limit=3)

            assert len(history) == 3
            # Should be in chronological order
            assert history[0].content == "Message 2"

    def test_build_context_with_sources(self, db_session):
        """Test building context from sources"""
        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            # Create mock Source objects
            source1 = MagicMock()
            source1.content = 'First chunk content'
            source1.expanded_content = None
            source1.document = MagicMock()
            source1.document.title = 'doc1.pdf'
            source1.document.filename = 'doc1.pdf'

            source2 = MagicMock()
            source2.content = 'Second chunk content'
            source2.expanded_content = None
            source2.document = MagicMock()
            source2.document.title = 'doc2.pdf'
            source2.document.filename = 'doc2.pdf'

            context = service._build_context([source1, source2])

            assert 'First chunk content' in context
            assert 'Second chunk content' in context
            assert 'doc1.pdf' in context
            assert 'doc2.pdf' in context
            assert '[1]' in context
            assert '[2]' in context

    def test_build_context_empty(self, db_session):
        """Test building context with empty results"""
        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)
            context = service._build_context([])

            assert context == ""

    def test_build_context_with_graph_context(self, db_session):
        """Test building context with graph context included"""
        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            source1 = MagicMock()
            source1.content = 'Document content'
            source1.expanded_content = None
            source1.document = MagicMock()
            source1.document.title = 'test.pdf'
            source1.document.filename = 'test.pdf'

            graph_context = "Entity: Apple Inc. -> Relationship: founded_by -> Entity: Steve Jobs"

            context = service._build_context([source1], graph_context=graph_context)

            assert 'KNOWLEDGE GRAPH CONTEXT' in context
            assert 'Apple Inc' in context
            assert 'Steve Jobs' in context
            assert 'Document content' in context

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

        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)
            history = [msg1, msg2]

            messages = service._build_langchain_messages(
                history,
                "How does it work?",
                "Context: RAG combines retrieval and generation"
            )

            # Should have system + history + current message
            assert len(messages) >= 3
            # First message should be system message
            assert messages[0].content.startswith("You are a RAG agent")

    def test_build_langchain_messages_no_context(self, db_session):
        """Test building messages without context"""
        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            messages = service._build_langchain_messages(
                [],
                "Test question",
                ""
            )

            # System + user message
            assert len(messages) == 2
            assert "Test question" in messages[-1].content

    def test_get_or_create_session_new(self, db_session, test_user):
        """Test creating a new chat session"""
        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            session_id = uuid4()
            session = service._get_or_create_session(
                session_id=session_id,
                user_id=test_user.id,
                collection_id=None,
                title_hint="Test conversation"
            )

            assert session is not None
            assert session.id == session_id
            assert session.user_id == test_user.id
            assert session.title == "Test conversation"

    def test_get_or_create_session_existing(self, db_session, test_chat_session, test_user):
        """Test retrieving an existing chat session"""
        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            session = service._get_or_create_session(
                session_id=test_chat_session.id,
                user_id=test_user.id,
                collection_id=None,
                title_hint="New title"
            )

            # Should return existing session, not create new
            assert session.id == test_chat_session.id
            # Title should NOT be overwritten
            assert session.title == test_chat_session.title

    def test_save_message(self, db_session, test_chat_session):
        """Test saving a chat message"""
        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            msg = service._save_message(
                session_id=test_chat_session.id,
                role="user",
                content="Test message content"
            )

            assert msg is not None
            assert msg.session_id == test_chat_session.id
            assert msg.role == "user"
            assert msg.content == "Test message content"

            # Verify it's in the database
            saved = db_session.query(ChatMessage).filter(
                ChatMessage.id == msg.id
            ).first()
            assert saved is not None

    def test_save_message_with_metadata(self, db_session, test_chat_session):
        """Test saving a message with chunk IDs and metadata"""
        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            chunk_ids = [str(uuid4()), str(uuid4())]
            metadata = {
                "model": "gpt-4o-mini",
                "preset": "detailed",
                "graph_enhanced": True
            }

            msg = service._save_message(
                session_id=test_chat_session.id,
                role="assistant",
                content="Response with sources",
                chunk_ids=chunk_ids,
                metadata=metadata
            )

            assert msg.chunk_ids == chunk_ids
            assert msg.metadata == metadata

    def test_count_tokens(self, db_session):
        """Test token counting"""
        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            # Test with a simple string
            count = service._count_tokens("Hello world, this is a test.")
            assert count > 0
            assert isinstance(count, int)

    def test_to_source_references(self, db_session):
        """Test converting Source objects to SourceReference"""
        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            # Create mock Source objects
            source = MagicMock()
            source.document = MagicMock()
            source.document.id = str(uuid4())
            source.document.title = "Test Document"
            source.document.filename = "test.pdf"
            source.chunk_index = 0
            source.score = 0.95
            source.rerank_score = 0.98

            refs = service._to_source_references([source])

            assert len(refs) == 1
            assert refs[0].document_id == source.document.id
            assert refs[0].title == "Test Document"
            assert refs[0].filename == "test.pdf"
            assert refs[0].score == 0.98  # Should use rerank_score when available

    def test_deduplicate_sources(self, db_session):
        """Test source deduplication"""
        with patch('backend.services.chat_service.ChatLiteLLM'), \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            from backend.schemas.chat import SourceReference

            doc_id = str(uuid4())

            # Chunk sources
            chunk_sources = [
                SourceReference(
                    document_id=doc_id,
                    title="Doc 1",
                    filename="doc1.pdf",
                    chunk_index=0,
                    score=0.9
                ),
                SourceReference(
                    document_id=doc_id,
                    title="Doc 1",
                    filename="doc1.pdf",
                    chunk_index=1,
                    score=0.85
                ),
            ]

            # Graph sources (may have same document)
            graph_sources = [
                SourceReference(
                    document_id=str(uuid4()),
                    title="Doc 1",
                    filename="doc1.pdf",
                    chunk_index=0,
                    score=1.0  # Higher score but same file
                ),
            ]

            deduplicated = service._deduplicate_sources(chunk_sources, graph_sources)

            # Should have 2 unique entries (different chunk indices)
            assert len(deduplicated) == 2
            # Sorted by score descending
            assert deduplicated[0].score >= deduplicated[1].score

    @patch('backend.services.chat_service.settings')
    @patch('backend.services.chat_service.CHAT_PRESETS')
    def test_create_llm_for_request_with_preset(self, mock_presets, mock_settings, db_session):
        """Test creating LLM with preset configuration"""
        mock_settings.LLM_MODEL_STRING = "openai/gpt-4o-mini"
        mock_settings.CHAT_TEMPERATURE = 0.7
        mock_settings.CHAT_MAX_TOKENS = 1000
        mock_settings.LLM_TIMEOUT = 60
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.OPENAI_API_KEY = "test_key"
        mock_settings.LLM_API_BASE = None

        mock_presets.__getitem__ = Mock(return_value={
            "temperature": 0.3,
            "max_tokens": 500,
            "system_prompt_style": "brief"
        })
        mock_presets.get = Mock(return_value={
            "temperature": 0.3,
            "max_tokens": 500,
            "system_prompt_style": "brief"
        })

        with patch('backend.services.chat_service.ChatLiteLLM') as mock_llm, \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            llm = service._create_llm_for_request(preset="concise")

            # Should use preset temperature and max_tokens
            call_kwargs = mock_llm.call_args[1]
            assert call_kwargs['temperature'] == 0.3
            assert call_kwargs['max_tokens'] == 500

    @patch('backend.services.chat_service.settings')
    def test_create_llm_for_request_with_model_override(self, mock_settings, db_session):
        """Test creating LLM with model override"""
        mock_settings.LLM_MODEL_STRING = "openai/gpt-4o-mini"
        mock_settings.CHAT_TEMPERATURE = 0.7
        mock_settings.CHAT_MAX_TOKENS = 1000
        mock_settings.LLM_TIMEOUT = 60
        mock_settings.LLM_PROVIDER = "openai"
        mock_settings.OPENAI_API_KEY = "test_key"
        mock_settings.LLM_API_BASE = None

        with patch('backend.services.chat_service.ChatLiteLLM') as mock_llm, \
             patch('backend.services.chat_service.PromptBuilder'), \
             patch('backend.services.chat_service.DeepReasoningService'), \
             patch('backend.services.chat_service.get_judge_service') as mock_judge, \
             patch('backend.services.chat_service.get_followup_service') as mock_followup:

            mock_judge.return_value = MagicMock()
            mock_followup.return_value = MagicMock()

            service = ChatService(db_session)

            llm = service._create_llm_for_request(model="gpt-4o")

            call_kwargs = mock_llm.call_args[1]
            assert call_kwargs['model'] == "gpt-4o"
