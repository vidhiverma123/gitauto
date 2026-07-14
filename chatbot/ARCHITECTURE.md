# 🏗️ System Architecture & Engineering Blueprints: Intelligent AI Chatbot

This document outlines the **multi-layered architectural design**, **component interaction diagrams**, **data pipelines**, and **normalized relational schema** powering the Intelligent AI Chatbot Application.

---

## 🏛️ 1. High-Level System Architecture

The application is architected around a **Service-Repository Pattern** that enforces strict separation of concerns across four distinct layers:

```mermaid
graph TD
    subgraph Layer 1: Presentation & UI Layer
        UI_AUTH[AuthView: Login/Register Tabs]
        UI_SIDEBAR[Sidebar: Date-Grouped History, Search & Tag Filters]
        UI_CHAT[ChatView: Real-Time Streaming & Prompt Inspector]
        UI_PROFILE[ProfileView: Editable Long-Term Memory Manager]
        UI_SETTINGS[SettingsView: Model, Temp, & Theme Config]
        UI_ANALYTICS[AnalyticsView: Metrics & Live Audit Log Table]
    end

    subgraph Layer 2: Service & Orchestration Agent Layer
        SRV_CONV[ConversationService: Turn Orchestrator & Auto-Tagging]
        SRV_AUTH[AuthService: Bcrypt Hashing, JWT & Greeting Logic]
        SRV_OLLAMA[OllamaService: Streaming HTTP Inference Client]
        SRV_PROMPT[PromptBuilder: Dynamic Context Assembly Agent]
        SRV_EXTRACT[MemoryExtractor: Fact Extraction Agent]
        SRV_SUMMARIZE[ConversationSummarizer: Progressive Summarization Agent]
        SRV_EXPORT[ExportService: MD, JSON, & ReportLab PDF Generator]
    end

    subgraph Layer 3: Data Access Layer Repositories
        REPO_USER[UserRepository: User Profiles & Settings]
        REPO_CONV[ConversationRepository: Chats, Messages & TSVECTOR Full-Text Search]
        REPO_MEM[MemoryRepository: UserMemory Key-Value Persistence]
        REPO_AUDIT[AuditRepository: System Diagnostics & Latency Tracking]
    end

    subgraph Layer 4: Storage & Inference Engines
        PG[(PostgreSQL 16 / SQLite Engine: Relational Schema)]
        LLM[[Ollama Local LLM Engine: llama3, qwen, mistral]]
    end

    %% UI to Service Connections
    UI_AUTH --> SRV_AUTH
    UI_SIDEBAR --> REPO_CONV & SRV_CONV
    UI_CHAT --> SRV_CONV & SRV_OLLAMA & SRV_EXPORT
    UI_PROFILE --> REPO_USER & REPO_MEM
    UI_SETTINGS --> REPO_USER & SRV_OLLAMA
    UI_ANALYTICS --> REPO_CONV & REPO_AUDIT

    %% Service Interactions
    SRV_CONV --> SRV_PROMPT & SRV_OLLAMA & SRV_EXTRACT & SRV_SUMMARIZE & REPO_CONV & REPO_AUDIT
    SRV_AUTH --> REPO_USER
    SRV_EXTRACT --> REPO_MEM & SRV_OLLAMA
    SRV_SUMMARIZE --> REPO_CONV & SRV_OLLAMA

    %% Repository to Database Connections
    REPO_USER & REPO_CONV & REPO_MEM & REPO_AUDIT --> PG
    SRV_OLLAMA <--> LLM
```

---

## 🔁 2. Retrieval-Augmented Memory Construction Pipeline

Before every turn is sent to the local Ollama LLM, `PromptBuilder.build_messages_payload()` dynamically constructs an enriched context package:

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Streamlit as Streamlit UI ChatView
    participant ConvSrv as ConversationService Orchestrator
    participant Repo as PostgreSQL Repositories
    participant Prompt as PromptBuilder Agent
    participant Ollama as Ollama Engine (llama3)
    participant Extractor as MemoryExtractor Agent

    User->>Streamlit: Submits Prompt ("Where do I live and what's my dog's name?")
    Streamlit->>ConvSrv: send_message_and_stream_response(user_id, conv_id, prompt, model)
    ConvSrv->>Repo: add_message(conv_id, user_id, role="user", content=prompt)
    
    rect rgb(20, 40, 60)
        Note over ConvSrv,Prompt: RAG Memory Retrieval Pipeline
        ConvSrv->>Repo: get_user_memories(user_id)
        Repo-->>ConvSrv: List of UserMemory facts [location: Bangalore, dog's name: Bruno]
        ConvSrv->>Repo: get_latest_summary(conv_id)
        Repo-->>ConvSrv: ConversationSummary (or None if turns < 30)
        ConvSrv->>Repo: get_messages(conv_id, limit=10)
        Repo-->>ConvSrv: Recent Message Window
        ConvSrv->>Prompt: build_messages_payload(user, memories, summary, window, prompt)
        Prompt-->>ConvSrv: Enriched payload [{role: "system", content: "You remember facts..."}, ...]
    end

    ConvSrv->>Ollama: generate_stream(payload, model="llama3", temp=0.7)
    
    loop Real-Time Token Streaming
        Ollama-->>ConvSrv: Yield Token Chunk
        ConvSrv-->>Streamlit: Stream Token Chunk (`st.write_stream`)
    end

    Streamlit-->>User: Complete Assistant Response Rendered in UI

    ConvSrv->>Repo: add_message(conv_id, role="assistant", content=full_response, response_time_ms)
    
    rect rgb(40, 20, 40)
        Note over ConvSrv,Extractor: Asynchronous Background Maintenance & Learning
        ConvSrv-)Extractor: extract_and_store(user_id, prompt)
        Extractor-)Ollama: Extract new personal facts (`JSON` output)
        Extractor-)Repo: create_or_update_memory(user_id, fact_key, fact_value)
        ConvSrv-)Repo: log_event("OLLAMA_RESPONSE", "Generated turn in 1420ms")
    end
```

---

## 📊 3. Entity-Relationship Schema (SQLAlchemy Models)

```mermaid
erDiagram
    users ||--o| settings : "has preferences"
    users ||--o{ conversations : "owns"
    users ||--o{ user_memory : "has memories"
    users ||--o{ audit_logs : "generates"
    conversations ||--o{ messages : "contains"
    conversations ||--o{ conversation_summaries : "compressed into"
    conversations }|..|{ tags : "categorized by"

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

## 🔒 4. Security & Authentication Architecture

```mermaid
flowchart LR
    A[User Submits Credentials] --> B{Login vs Register?}
    B -->|Register| C[AuthService.register_user]
    C --> D[bcrypt.hashpw: Salt + Hash Password]
    D --> E[Save to users table in PostgreSQL]
    
    B -->|Login| F[AuthService.authenticate_user]
    F --> G[Fetch user from users table by username/email]
    G --> H[bcrypt.checkpw: Verify against hashed_password]
    H -->|Valid| I[Generate JWT Access Token + Personalized Greeting]
    H -->|Invalid| J[Log AUTH_FAILURE to audit_logs & return 401]
```
