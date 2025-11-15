"""
ChatMessage Model - Individual messages in conversations
Stores user and assistant messages with retrieval metadata
"""

from sqlalchemy import Column, String, Text, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base


class ChatMessage(Base):
    """
    Chat message model - individual messages in conversation

    Attributes:
        id: Message UUID
        session_id: Parent session
        role: Message role ('user', 'assistant', 'system')
        content: Message text
        chunk_ids: List of chunk UUIDs used (for assistant messages)
        metadata: Flexible metadata (tokens, latency, model, etc.)
        created_at: Message timestamp

    Relationships:
        session: Parent chat session (many-to-one)

    Roles:
        - user: User's message
        - assistant: AI's response
        - system: System message (instructions)

    Cascade Delete:
        - Deleting session deletes all messages
    """

    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)

    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Retrieval metadata (for assistant messages)
    chunk_ids = Column(JSON, default=list)
    metadata_ = Column("metadata", JSON, default=dict)  # metadata is reserved by SQLAlchemy

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role={self.role}, session_id={self.session_id})>"
