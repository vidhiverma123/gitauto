import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Float, Text, Boolean, Table
from sqlalchemy.orm import relationship
from app.database.connection import Base

def get_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

# Association table for many-to-many relationship between conversations and tags
conversation_tags = Table(
    "conversation_tags",
    Base.metadata,
    Column("conversation_id", String(36), ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", String(36), ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)
)

class Tag(Base):
    __tablename__ = "tags"

    id = Column(String(36), primary_key=True, default=get_uuid)
    name = Column(String(100), unique=True, index=True, nullable=False)

    conversations = relationship("Conversation", secondary=conversation_tags, back_populates="tags")

    def __repr__(self) -> str:
        return f"<Tag(name='{self.name}')>"


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=get_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    title = Column(String(255), default="New Chat", nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)
    is_pinned = Column(Boolean, default=False, nullable=False)
    ollama_model_used = Column(String(100), default="llama3", nullable=False)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.timestamp")
    summaries = relationship("ConversationSummary", back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationSummary.created_at")
    tags = relationship("Tag", secondary=conversation_tags, back_populates="conversations")

    def __repr__(self) -> str:
        return f"<Conversation(id='{self.id}', title='{self.title}')>"


class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=get_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', or 'system'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=get_utc_now, nullable=False)
    ollama_model_used = Column(String(100), nullable=True)
    response_time_ms = Column(Float, nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message(id='{self.id}', role='{self.role}', timestamp='{self.timestamp}')>"


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"

    id = Column(String(36), primary_key=True, default=get_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    summary_text = Column(Text, nullable=False)
    messages_summarized_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)

    # Relationships
    conversation = relationship("Conversation", back_populates="summaries")

    def __repr__(self) -> str:
        return f"<ConversationSummary(id='{self.id}', count={self.messages_summarized_count})>"
