from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.memory import UserMemory

class MemoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_user_memories(self, user_id: str) -> List[UserMemory]:
        return self.db.query(UserMemory).filter(
            UserMemory.user_id == user_id
        ).order_by(UserMemory.updated_at.desc()).all()

    def get_by_key(self, user_id: str, fact_key: str) -> Optional[UserMemory]:
        return self.db.query(UserMemory).filter(
            UserMemory.user_id == user_id,
            UserMemory.fact_key.ilike(fact_key.strip())
        ).first()

    def create_or_update_memory(
        self,
        user_id: str,
        fact_key: str,
        fact_value: str,
        raw_text: Optional[str] = None
    ) -> UserMemory:
        clean_key = fact_key.strip().lower()
        clean_val = fact_value.strip()

        existing = self.get_by_key(user_id, clean_key)
        if existing:
            existing.fact_value = clean_val
            if raw_text:
                existing.raw_text = raw_text
            existing.updated_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(existing)
            return existing
        else:
            new_mem = UserMemory(
                user_id=user_id,
                fact_key=clean_key,
                fact_value=clean_val,
                raw_text=raw_text
            )
            self.db.add(new_mem)
            self.db.commit()
            self.db.refresh(new_mem)
            return new_mem

    def delete_memory(self, memory_id: str, user_id: str) -> bool:
        mem = self.db.query(UserMemory).filter(
            UserMemory.id == memory_id,
            UserMemory.user_id == user_id
        ).first()
        if mem:
            self.db.delete(mem)
            self.db.commit()
            return True
        return False
