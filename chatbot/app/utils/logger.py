import json
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)

def log_event(
    db: Session,
    event_type: str,
    description: str,
    user_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an audit or diagnostic event to both system logger and PostgreSQL/SQLite audit_logs table.
    """
    logger.info(f"[{event_type}] {description} (User: {user_id})")
    try:
        metadata_str = json.dumps(metadata) if metadata else None
        audit_entry = AuditLog(
            user_id=user_id,
            event_type=event_type,
            description=description,
            metadata_json=metadata_str
        )
        db.add(audit_entry)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to write audit log to database: {e}")
        db.rollback()
