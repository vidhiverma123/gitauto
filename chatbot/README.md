# 🤖 Intelligent AI Chatbot Application

An advanced, highly modular conversational AI application built with **Python**, **Streamlit**, **Ollama (local LLM)**, and **PostgreSQL** (`SQLAlchemy ORM` + `Alembic`). 

The primary objective of this project is to demonstrate **state-of-the-art chatbot engineering**, **retrieval-augmented conversational memory (without vector databases)**, **long-term user personalization**, and **PostgreSQL integration** using normalized tables and full-text search.

---

## ✨ Key Features & Highlights

1. **Persistent Conversational & Long-Term Memory**:
   - **Short-Term Context**: Retains recent turns within any chat session.
   - **Progressive Summarization**: After every configurable message threshold (default: `30` messages), an LLM background summarizer (`ConversationSummarizer`) compresses older history into a concise summary stored in the `conversation_summaries` table, preserving exact context while keeping prompt sizes optimal.
   - **Long-Term User Personalization (`UserMemory`)**: Automatically extracts personal facts shared by the user (e.g. *"My birthday is July 20"*, *"I work as a Data Engineer"*, *"My dog's name is Bruno"*) using Ollama + rule-based fallback. When the user asks *"What is my dog's name?"* or *"Where do I live?"* in any future conversation, the retrieved memories are dynamically injected into the prompt.

2. **Intelligent Retrieval-Augmented Prompt Construction (`PromptBuilder`)**:
   Before every inference call to Ollama, the prompt pipeline dynamically assembles:
   - **System Instructions & Persona**
   - **User Profile Data** (Name, Username, Email)
   - **Retrieved Long-Term Memories (`user_memory`)**
   - **Latest Conversation Summary (`conversation_summaries`)**
   - **Recent Conversation History Window** (`limit = 10`)
   - **Latest User Message**

3. **Multi-Model Local LLM with Token-by-Token Streaming (`OllamaService`)**:
   - Streams responses in real-time (`st.write_stream`) with an **"Assistant is thinking..."** indicator.
   - Supports switching across multiple local Ollama models (`llama3`, `qwen`, `mistral`, `phi`).
   - Tracks response latency in milliseconds (`response_time_ms`) and records which model was used per turn.
   - **Graceful Offline Fallback**: If Ollama is not running, yields clear diagnostic instructions instead of crashing.

4. **Normalized PostgreSQL Integration & Full-Text Search**:
   - Built on clean SQLAlchemy ORM models with `Alembic` migration support (`migrations/`).
   - Normalized schema across 8 core tables: `users`, `conversations`, `messages`, `user_memory`, `conversation_summaries`, `settings`, `audit_logs`, `tags`, and `conversation_tags`.
   - Leverages full-text search / `ILIKE` across both **Conversation Titles** and **Message Content** to allow instant keyword searches and category tag filtering (`Programming`, `SQL`, `AI`, `Travel`, `Finance`, `Education`, `Personal`).

5. **Personalized Authentication & Security (`AuthService`)**:
   - Secure registration, login, and logout flows with **bcrypt password hashing** (passwords are never stored in plaintext).
   - Session/JWT-based identity tracking.
   - Grees users personally upon login (*"Welcome back, Varsha!"* or *"Hi Varsha! What would you like to work on today?"*) and never asks for their name again.

6. **Rich, Modern UI & Multi-Format Exports**:
   - Grouped chat sidebar by date: `📌 Pinned`, `📅 Today`, `📆 Yesterday`, `🗓️ Last 7 Days`, and `🗄️ Older`.
   - Rename, delete, and pin/unpin conversations.
   - **Inspect Memory Pipeline Prompt Expander**: Inspect exactly what system prompt, retrieved facts, and chat summary were sent to the LLM on every turn.
   - **Export Chats**: One-click download as **Markdown (`.md`)**, **JSON (`.json`)**, or cleanly rendered **PDF (`.pdf`)** using ReportLab.
   - Interactive **Profile Page** (`render_profile_view`) with an editable Long-Term Memory Fact Manager.
   - **Settings Page** (`render_settings_view`) for default model, temperature slider, max tokens, and Dark/Light mode switcher.
   - **Analytics & Diagnostics Dashboard** (`render_analytics_view`) displaying volume metrics and live database `audit_logs`.

---

## 🏗️ Clean Modular Architecture

```text
app/
├── auth/
│   ├── __init__.py
│   └── service.py               # Bcrypt auth, JWT token generation, & personalized greetings
├── chatbot/
│   ├── __init__.py
│   ├── conversation_service.py  # Chat orchestration, auto-titling, auto-tagging, & streaming
│   └── ollama_service.py        # Synchronous and streaming HTTP client for Ollama API
├── config/
│   ├── __init__.py
│   └── settings.py              # Pydantic BaseSettings loading from .env
├── database/
│   ├── __init__.py
│   └── connection.py            # SQLAlchemy Engine, SessionLocal generator, & init_db
├── memory/
│   ├── __init__.py
│   ├── extractor.py             # LLM + Regex fact extraction into UserMemory
│   └── summarizer.py            # Progressive chat history summarization via Ollama
├── models/
│   ├── __init__.py
│   ├── audit.py                 # AuditLog model
│   ├── conversation.py          # Conversation, Message, ConversationSummary, Tag, conversation_tags
│   ├── memory.py                # UserMemory model
│   └── user.py                  # User and Setting models
├── prompts/
│   ├── __init__.py
│   └── builder.py               # Dynamic prompt assembler combining profile + memories + history
├── repositories/
│   ├── __init__.py
│   ├── audit_repository.py      # Data access for diagnostic and audit logs
│   ├── conversation_repository.py # Data access for chats, messages, full-text search, & tags
│   ├── memory_repository.py     # Data access for reading/updating user memory facts
│   └── user_repository.py       # Data access for users and preferences
├── schemas/
│   ├── __init__.py
│   └── dto.py                   # Pydantic schemas for data validation and REST API models
├── services/
│   ├── __init__.py
│   └── export_service.py        # Export to Markdown (.md), JSON (.json), and PDF (.pdf)
├── utils/
│   ├── __init__.py
│   ├── logger.py                # System and database audit logging utility
│   └── security.py              # Bcrypt hashing and JWT encoding/decoding utilities
└── main.py                      # Optional FastAPI entrypoint exposing all features via REST API

streamlit_app/
├── __init__.py
├── main.py                      # Streamlit UI runner managing session state & views
├── components/
│   ├── __init__.py
│   ├── analytics_view.py        # Analytics metrics & live audit log table
│   ├── auth_view.py             # Login and Registration tabs
│   ├── chat_view.py             # Chat view with streaming, prompt inspector, & exports
│   ├── profile_view.py          # User profile info & editable Long-Term Memory manager
│   ├── settings_view.py         # Preferred model, temperature, & UI theme configuration
│   └── sidebar.py               # Date-grouped chat sidebar, search box, & tag filters
└── styles/
    ├── __init__.py
    └── custom_css.py            # Glassmorphism, Google Fonts, & dark/light theme CSS

migrations/                      # Alembic database migration environment & revisions
tests/                           # Unit test suite verifying Auth, Memory, and Conversations
Dockerfile                       # Docker container specification
docker-compose.yml               # Multi-container setup (Postgres + Ollama + UI + API)
requirements.txt                 # Python dependencies
```

---

## 🗄️ Normalized Database Schema

```mermaid
erDiagram
    users ||--o| settings : "has 1"
    users ||--o{ conversations : "owns"
    users ||--o{ user_memory : "has memories"
    users ||--o{ audit_logs : "triggers"
    conversations ||--o{ messages : "contains"
    conversations ||--o{ conversation_summaries : "summarized by"
    conversations }|..|{ tags : "tagged with"

    users {
        string id PK
        string full_name
        string username
        string email
        string hashed_password
        datetime created_at
        datetime last_login_at
    }
    conversations {
        string id PK
        string user_id FK
        string title
        datetime created_at
        datetime updated_at
        boolean is_pinned
        string ollama_model_used
    }
    messages {
        string id PK
        string conversation_id FK
        string user_id FK
        string role
        text content
        datetime timestamp
        string ollama_model_used
        float response_time_ms
    }
    user_memory {
        string id PK
        string user_id FK
        string fact_key
        text fact_value
        text raw_text
        datetime created_at
        datetime updated_at
    }
    conversation_summaries {
        string id PK
        string conversation_id FK
        text summary_text
        integer messages_summarized_count
        datetime created_at
    }
    settings {
        string id PK
        string user_id FK
        string preferred_ollama_model
        float temperature
        integer max_tokens
        string theme
    }
    tags {
        string id PK
        string name
    }
    audit_logs {
        string id PK
        string user_id FK
        string event_type
        text description
        text metadata_json
        datetime timestamp
    }
```

---

## 🧠 Memory Pipeline & Dynamic Prompt Flow

When a user submits a message in the chat interface:

```mermaid
flowchart TD
    A[User Submits Message] --> B[ConversationService.send_message_and_stream_response]
    B --> C[Persist User Message to PostgreSQL]
    
    subgraph Retrieval Pipeline [Retrieval-Augmented Memory Pipeline]
        D1[Fetch User Profile from users table]
        D2[Fetch Long-Term Facts from user_memory table]
        D3[Fetch Latest Summary from conversation_summaries]
        D4[Fetch Last 10 Messages from messages table]
    end
    
    C --> D1 & D2 & D3 & D4
    D1 & D2 & D3 & D4 --> E[PromptBuilder.build_messages_payload]
    
    E --> F[OllamaService.generate_stream - /api/chat]
    F --> G[Stream Tokens to Streamlit UI in Real-Time]
    G --> H[Persist Assistant Message with Response Time & Model]
    
    subgraph Post Generation Hooks [Background Memory & Maintenance Hooks]
        I1[MemoryExtractor: Extract New Self-Facts via LLM/Regex -> Save to user_memory]
        I2[Auto-Title & Auto-Tag via LLM if conversation is new]
        I3[ConversationSummarizer: Summarize Older Turns if msg count >= 30]
        I4[AuditLogger: Record OLLAMA_RESPONSE and MEMORY_EXTRACTED events]
    end
    
    H --> I1 & I2 & I3 & I4
```

---

## 🚀 Setup & Installation Instructions

### Option 1: Quick Local Run (Zero-Setup with SQLite Fallback or Local Postgres)

1. **Clone & Navigate into the workspace**:
   ```bash
   cd /Users/as-mac-1322/chatbot
   ```

2. **Create a Virtual Environment & Install Dependencies**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Copy `.env.example` to `.env` or edit `.env` directly:
   ```bash
   cp .env.example .env
   ```
   *Note: By default, `.env` is configured to use `sqlite:///./ai_chatbot.db` so you can run immediately without installing PostgreSQL. If you have PostgreSQL running on port 5432, uncomment `DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/ai_chatbot_db` inside `.env`.*

4. **Ensure Ollama is Running Locally**:
   Download from [ollama.com](https://ollama.com) and pull at least one model:
   ```bash
   ollama pull llama3
   ollama run llama3
   ```

5. **Run Unit Tests**:
   ```bash
   python3 -m pytest tests/
   ```

6. **Launch the Streamlit UI**:
   ```bash
   streamlit run streamlit_app/main.py
   ```
   Open your browser to `http://localhost:8501`.

*(Optional)* **Launch the FastAPI Backend**:
If you also want to interact with the backend via REST API or Swagger documentation (`http://localhost:8000/docs`):
```bash
uvicorn app.main:app --reload --port 8000
```

---

### Option 2: Full Docker Deployment (Postgres + Ollama + Streamlit + FastAPI)

1. **Build and start all containers**:
   ```bash
   docker-compose up --build -d
   ```
2. **Access Services**:
   - **Streamlit UI**: [http://localhost:8501](http://localhost:8501)
   - **FastAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **PostgreSQL**: Port `5432` (`db: ai_chatbot_db`, user: `postgres`, pw: `postgrespassword`)

---

## 🔮 Future Enhancements

- **Vector/Embedding Indexing (`pgvector`)**: While this application demonstrates high-precision keyword/SQL retrieval and progressive summarization without external vector DB dependencies, integrating PostgreSQL `pgvector` could allow semantic similarity lookups across millions of past conversation turns.
- **Multi-Modal Document Ingestion**: Uploading PDFs/CSV files inside conversations and chunking them directly into PostgreSQL for custom RAG over documents.
- **Voice / Speech-to-Text**: Integrating Whisper/WebAudio so users can speak directly to their personalized assistant.
