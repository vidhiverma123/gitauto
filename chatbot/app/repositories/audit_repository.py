from typing import List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_logs(self, user_id: Optional[str] = None, event_type: Optional[str] = None, limit: int = 100) -> List[AuditLog]:
        query = self.db.query(AuditLog)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if event_type:
            query = query.filter(AuditLog.event_type == event_type)
        return query.order_by(desc(AuditLog.timestamp)).limit(limit).all()
