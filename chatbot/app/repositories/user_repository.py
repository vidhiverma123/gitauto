from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User, Setting

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def create(self, full_name: str, username: str, email: str, hashed_password: str) -> User:
        user = User(
            full_name=full_name,
            username=username,
            email=email,
            hashed_password=hashed_password
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        # Create default user settings immediately
        default_settings = Setting(
            user_id=user.id,
            preferred_ollama_model="llama3",
            temperature=0.7,
            max_tokens=1024,
            theme="dark",
            llm_provider="ollama",
            api_key=None,
            api_base_url=None
        )
        self.db.add(default_settings)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update_last_login(self, user_id: str) -> None:
        user = self.get_by_id(user_id)
        if user:
            user.last_login_at = datetime.now(timezone.utc)
            self.db.commit()

    def get_settings(self, user_id: str) -> Optional[Setting]:
        setting = self.db.query(Setting).filter(Setting.user_id == user_id).first()
        if not setting and self.get_by_id(user_id):
            # Create if missing
            setting = Setting(user_id=user_id)
            self.db.add(setting)
            self.db.commit()
            self.db.refresh(setting)
        return setting

    def update_settings(
        self,
        user_id: str,
        preferred_model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        theme: Optional[str] = None,
        llm_provider: Optional[str] = None,
        api_key: Optional[str] = None,
        api_base_url: Optional[str] = None
    ) -> Setting:
        setting = self.get_settings(user_id)
        if setting:
            if preferred_model is not None:
                setting.preferred_ollama_model = preferred_model
            if temperature is not None:
                setting.temperature = temperature
            if max_tokens is not None:
                setting.max_tokens = max_tokens
            if theme is not None:
                setting.theme = theme
            if llm_provider is not None:
                setting.llm_provider = llm_provider
            if api_key is not None:
                setting.api_key = api_key
            if api_base_url is not None:
                setting.api_base_url = api_base_url
            self.db.commit()
            self.db.refresh(setting)
        return setting
