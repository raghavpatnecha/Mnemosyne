"""
ChatSession Model - Conversation container
Stores chat sessions with message history
"""

from sqlalchemy import Column, String, ForeignKey, JSON, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from backend.database import Base


class ChatSession(Base):
    """
    Chat session model - conversation container

    Attributes:
        id: Session UUID
        user_id: Session owner
        collection_id: Optional collection filter for RAG
        title: Session title (auto-generated from first message)
        metadata: Flexible metadata
        created_at: Session creation time
        updated_at: Last update time
        last_message_at: Timestamp of last message

    Relationships:
        user: Session owner (many-to-one)
        collection: Optional collection (many-to-one)
        messages: Chat messages (one-to-many)

    Cascade Delete:
        - Deleting user deletes all sessions
        - Deleting session deletes all messages
    """

    __tablename__ = "chat_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="SET NULL"), index=True)

    title = Column(String(255))
    metadata = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_message_at = Column(DateTime(timezone=True))

    # Relationships
    user = relationship("User")
    collection = relationship("Collection")
    messages = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at"
    )

    def __repr__(self):
        return f"<ChatSession(id={self.id}, user_id={self.user_id}, title={self.title})>"
