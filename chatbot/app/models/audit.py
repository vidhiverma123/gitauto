import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database.connection import Base

def get_uuid() -> str:
    return str(uuid.uuid4())

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class AuditLog(Base):
    """
    Audit log table for recording security, memory extraction, system events, and error diagnostics.
    """
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=get_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    event_type = Column(String(50), index=True, nullable=False)
    description = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)  # JSON formatted string
    timestamp = Column(DateTime, default=get_utc_now, index=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog(event='{self.event_type}', timestamp='{self.timestamp}')>"
