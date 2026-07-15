from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    username: str = Field(..., min_length=3, max_length=100)
    email: str = Field(..., max_length=255)
    password: str = Field(..., min_length=6)

class UserLoginRequest(BaseModel):
    username_or_email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    full_name: str
    greeting: str

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    full_name: str
    username: str
    email: str
    created_at: datetime
    last_login_at: Optional[datetime] = None

class MessageCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    model: str = "llama3"
    temperature: float = 0.7
    max_tokens: int = 1024

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    timestamp: datetime
    ollama_model_used: Optional[str] = None
    response_time_ms: Optional[float] = None

class ConversationCreateRequest(BaseModel):
    title: str = "New Chat"
    model: str = "llama3"

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    is_pinned: bool
    ollama_model_used: str
    tags: List[str] = []

class MemoryCreateRequest(BaseModel):
    fact_key: str = Field(..., min_length=2)
    fact_value: str = Field(..., min_length=1)

class MemoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    fact_key: str
    fact_value: str
    created_at: datetime
    updated_at: datetime

class AnalyticsResponse(BaseModel):
    total_conversations: int
    total_messages: int
    avg_messages_per_conversation: float
    most_active_day: str
    most_frequently_used_model: str
    avg_assistant_response_time_ms: float

class TopConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    is_pinned: bool
    ollama_model_used: str
    metric_name: str
    metric_value: str
    tags: List[str] = []

