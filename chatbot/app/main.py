import logging
from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.database.connection import get_db, init_db
from app.auth.service import AuthService
from app.chatbot.conversation_service import ConversationService
from app.repositories.user_repository import UserRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.memory_repository import MemoryRepository
from app.models.user import User
from app.schemas.dto import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    UserResponse,
    ConversationCreateRequest,
    ConversationResponse,
    MessageCreateRequest,
    MessageResponse,
    MemoryCreateRequest,
    MemoryResponse,
    AnalyticsResponse
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(
    title="Intelligent AI Chatbot API",
    description="Backend API demonstrating conversational memory, Postgres full-text search, Ollama LLM integration, and user personalization.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    logger.info("Starting Intelligent AI Chatbot API server...")
    try:
        init_db()
    except Exception as e:
        logger.error(f"Error initializing DB on startup: {e}")

def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header.")
    token = authorization.split("Bearer ")[1]
    auth_service = AuthService(db)
    user = auth_service.get_user_from_token(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Expired or invalid JWT token.")
    return user

# ==================== AUTH ENTRIES ====================
@app.post("/api/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    user, error = auth_service.register_user(req.full_name, req.username, req.email, req.password)
    if error or not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error or "Registration failed.")
    return user

@app.post("/api/auth/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    token, user, error = auth_service.login_for_token(req.username_or_email, req.password)
    if error or not token or not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=error or "Login failed.")
    greeting = auth_service.get_personalized_greeting(user)
    return TokenResponse(
        access_token=token,
        username=user.username,
        full_name=user.full_name,
        greeting=greeting
    )

@app.get("/api/auth/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# ==================== CONVERSATIONS & MESSAGES ====================
@app.get("/api/conversations", response_model=List[ConversationResponse])
def list_conversations(
    keyword: Optional[str] = None,
    tag: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    conv_repo = ConversationRepository(db)
    convs = conv_repo.search_conversations(current_user.id, keyword=keyword, tag_name=tag)
    res = []
    for c in convs:
        res.append(ConversationResponse(
            id=c.id,
            user_id=c.user_id,
            title=c.title,
            created_at=c.created_at,
            updated_at=c.updated_at,
            is_pinned=c.is_pinned,
            ollama_model_used=c.ollama_model_used,
            tags=[t.name for t in c.tags]
        ))
    return res

@app.post("/api/conversations", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def create_conversation(req: ConversationCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv_service = ConversationService(db)
    conv = conv_service.start_new_conversation(current_user.id, model_used=req.model)
    return ConversationResponse(
        id=conv.id,
        user_id=conv.user_id,
        title=conv.title,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        is_pinned=conv.is_pinned,
        ollama_model_used=conv.ollama_model_used,
        tags=[]
    )

@app.get("/api/conversations/{conv_id}/messages", response_model=List[MessageResponse])
def get_conversation_messages(conv_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv_repo = ConversationRepository(db)
    conv = conv_repo.get_by_id(conv_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    return conv_repo.get_messages(conv_id)

@app.post("/api/conversations/{conv_id}/messages", response_model=MessageResponse)
def send_message(conv_id: str, req: MessageCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv_repo = ConversationRepository(db)
    conv = conv_repo.get_by_id(conv_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    
    conv_service = ConversationService(db)
    # Execute full retrieval and generation loop synchronously for REST endpoint
    full_resp = ""
    for token in conv_service.send_message_and_stream_response(
        user=current_user,
        conversation_id=conv_id,
        user_message_text=req.content,
        model_used=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens
    ):
        full_resp += token

    messages = conv_repo.get_messages(conv_id)
    return messages[-1] if messages else MessageResponse(
        id="error", conversation_id=conv_id, role="assistant", content=full_resp, timestamp=datetime.utcnow()
    )

@app.delete("/api/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(conv_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv_repo = ConversationRepository(db)
    conv = conv_repo.get_by_id(conv_id)
    if not conv or conv.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    conv_repo.delete_conversation(conv_id)

# ==================== USER MEMORY ENDPOINTS ====================
@app.get("/api/memory", response_model=List[MemoryResponse])
def get_user_memories(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mem_repo = MemoryRepository(db)
    return mem_repo.get_user_memories(current_user.id)

@app.post("/api/memory", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
def create_or_update_memory(req: MemoryCreateRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mem_repo = MemoryRepository(db)
    mem = mem_repo.create_or_update_memory(current_user.id, req.fact_key, req.fact_value)
    return mem

@app.delete("/api/memory/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user_memory(memory_id: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    mem_repo = MemoryRepository(db)
    success = mem_repo.delete_memory(memory_id, current_user.id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory fact not found.")

# ==================== ANALYTICS ENDPOINT ====================
@app.get("/api/analytics", response_model=AnalyticsResponse)
def get_analytics(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv_repo = ConversationRepository(db)
    stats = conv_repo.get_user_analytics(current_user.id)
    return AnalyticsResponse(**stats)
