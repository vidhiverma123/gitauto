import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base

def get_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class UserMemory(Base):
    """
    Stores long-term user memories extracted automatically from conversations.
    Examples:
      - fact_key: 'favorite programming language', fact_value: 'Python'
      - fact_key: 'birthday', fact_value: 'July 20'
      - fact_key: 'profession', fact_value: 'Data Engineer'
      - fact_key: 'pet', fact_value: 'dog named Bruno'
      - fact_key: 'location', fact_value: 'Bangalore'
    """
    __tablename__ = "user_memory"

    id = Column(String(36), primary_key=True, default=get_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    fact_key = Column(String(255), index=True, nullable=False)
    fact_value = Column(Text, nullable=False)
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now, nullable=False)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="memories")

    def __repr__(self) -> str:
        return f"<UserMemory(user_id='{self.user_id}', key='{self.fact_key}', value='{self.fact_value}')>"
