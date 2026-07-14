import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables and .env file.
    """
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./ai_chatbot.db"

    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    DEFAULT_OLLAMA_MODEL: str = "llama3"
    SUPPORTED_OLLAMA_MODELS: List[str] = ["llama3", "qwen", "mistral", "phi"]
    OLLAMA_TIMEOUT: int = 120

    # JWT Authentication
    SECRET_KEY: str = "super-secret-jwt-key-change-this-in-production-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # Conversational Memory & Summarization
    SUMMARIZATION_MESSAGE_THRESHOLD: int = 30
    RECENT_MESSAGES_WINDOW: int = 10

    @property
    def is_postgres(self) -> bool:
        return "postgres" in self.DATABASE_URL.lower()

settings = Settings()
