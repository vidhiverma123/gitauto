# 🤖 End-to-End Guide & Key Points: Intelligent AI Chatbot Application

This document provides an exhaustive, end-to-end explanation of the **Intelligent AI Chatbot Application**, answering exact questions regarding **data storage**, **database schema**, **local LLM models**, and **autonomous agents/services** used throughout the project.

---

## 📌 1. Executive Summary & Core Engineering Goals

Unlike basic wrappers that only forward prompts to an API, this project demonstrates **production-grade chatbot engineering**, focusing on:
1. **Long-Term User Personalization across Sessions**: The chatbot remembers personal facts shared by the user weeks or months ago (e.g., *"My birthday is July 20"*, *"I work as a Data Engineer"*, *"My dog's name is Bruno"*).
2. **Retrieval-Augmented Memory Without Vector DB Bloat**: By using relational PostgreSQL (`user_memory` and `conversation_summaries` tables) and full-text `ILIKE` / SQL queries, we achieve precise, explainable contextual recall without heavy vector database overhead.
3. **Progressive Conversational Summarization**: Automatically compresses long conversation histories (>30 messages) in the background so that exact context is preserved while keeping LLM token consumption low.
4. **Local Data Privacy via Ollama**: Runs 100% locally with open-source models, ensuring no sensitive user or chat data ever leaves your server.

---

## 🗄️ 2. Where & How Chat Data is Stored (Database Engine & Schema)

### Database Engine & Connection
All chat data, user accounts, memories, and audit logs are stored in a relational database accessed via **SQLAlchemy ORM** (`app/database/connection.py`) with schema versioning managed by **Alembic** (`migrations/`).

* **Production / Docker Mode**: Stored in **PostgreSQL 16** (`postgresql+psycopg2://postgres:postgrespassword@localhost:5432/ai_chatbot_db`).
* **Local Quick-Start Mode**: Stored in **SQLite (`ai_chatbot.db`)** automatically created inside the project folder (`/Users/as-mac-1322/chatbot/ai_chatbot.db`) if `DATABASE_URL` is not set to a Postgres instance.

### Exact Table Storage Breakdown

| Table Name | What is Stored Inside | Key Columns & Structure |
| :--- | :--- | :--- |
| **`users`** | User profiles and authentication credentials | `id` (UUID string), `full_name`, `username`, `email`, `hashed_password` (stored using `bcrypt`), `created_at`, `last_login_at` |
| **`conversations`** | Header information for each chat session | `id` (UUID string), `user_id` (FK -> users.id), `title` (auto-generated or customized), `created_at`, `updated_at`, `is_pinned` (Boolean), `ollama_model_used` |
| **`messages`** | **Where exact chat turns live.** Every single user input and AI assistant response is appended here | `id` (UUID), `conversation_id` (FK -> conversations.id), `user_id` (FK), `role` (`'user'` or `'assistant'`), `content` (Full text Markdown of the message), `timestamp`, `ollama_model_used`, `response_time_ms` |
| **`user_memory`** | **Where long-term facts live.** Permanent personal memories extracted from conversations | `id` (UUID), `user_id` (FK), `fact_key` (e.g. `'dog\'s name'`), `fact_value` (e.g. `'Bruno'`), `raw_text`, `updated_at` |
| **`conversation_summaries`** | Compressed background summaries of older chat histories (`count >= 30`) | `id` (UUID), `conversation_id` (FK), `summary_text`, `messages_summarized_count`, `created_at` |
| **`tags` & `conversation_tags`** | Category tagging for conversations (`#Programming`, `#SQL`, `#AI`, etc.) | `id`, `name` (`Programming`, `Travel`, `Finance`, etc.), linked via many-to-many join table `conversation_tags` |
| **`settings`** | User-specific model parameters and appearance settings | `id`, `user_id` (FK), `preferred_ollama_model` (`llama3`), `temperature` (`0.7`), `max_tokens` (`1024`), `theme` (`dark`/`light`) |
| **`audit_logs`** | System diagnostics, latency tracking, and security event logs | `id`, `user_id` (FK), `event_type` (`USER_LOGIN`, `MEMORY_EXTRACTED`, `OLLAMA_RESPONSE`), `description`, `metadata_json`, `timestamp` |

> **Why this design matters**: When you open your chat history in the UI, `ConversationRepository.get_messages(conv_id)` queries the `messages` table ordered chronologically (`timestamp.asc()`). This guarantees 100% accurate, persistent chat logs that survive server restarts.

---

## 🤖 3. Which Models Are Used (Local LLM Specification)

We use **Ollama (`http://localhost:11434`)** as the local inference engine. The system supports dynamic model switching right from the Streamlit top bar (`st.selectbox`).

### Supported Models & Their Roles
1. **`llama3` (Meta Llama 3 - Default Model)**:
   * **Parameter Size**: 8B parameters (`llama3:latest`).
   * **Primary Role**: Handles conversational chat responses, dynamic auto-titling (`Generate a 3-word title...`), and progressive background summarization (`ConversationSummarizer`).
2. **`qwen` (Alibaba Qwen Series - Optional/Supported)**:
   * **Primary Role**: Exceptional multilingual reasoning and coding task assistance.
3. **`mistral` (Mistral 7B - Optional/Supported)**:
   * **Primary Role**: High-speed concise generation.
4. **`phi` (Microsoft Phi Series - Optional/Supported)**:
   * **Primary Role**: Lightweight, highly efficient local reasoning on edge/low-resource devices.

### Per-Turn & Per-User Model Tracking
* When you select `llama3` or `qwen` in the UI, that preference is saved directly to `settings.preferred_ollama_model` via `UserRepository.update_settings()`.
* Every response generated by the assistant records which exact model produced it in `messages.ollama_model_used` along with its exact execution latency (`response_time_ms`), giving you full comparative insight across models.

---

## 🕵️‍♂️ 4. Which Agents & Specialized Services Are Used (Term Breakdown)

Rather than using monolithic spaghetti code or generic external agent libraries, this application implements a clean **Service-Agent Architecture** where specialized Python classes act as **autonomous functional agents** coordinating different parts of the AI lifecycle.

### 1. `ConversationService` (The Central Orchestrator Agent)
* **Location**: `app/chatbot/conversation_service.py`
* **Role**: Acts as the master controller for chat workflows. When a user submits a prompt:
  1. Saves the user prompt into the `messages` table.
  2. Invokes the `PromptBuilder` agent to construct the retrieval-augmented prompt.
  3. Streams tokens in real-time from `OllamaService` (`st.write_stream`).
  4. Saves the completed assistant response into the `messages` table with `response_time_ms`.
  5. Asynchronously triggers post-generation maintenance hooks (`MemoryExtractor`, `ConversationSummarizer`, auto-titling, auto-tagging, and `AuditRepository` logging).

### 2. `MemoryExtractor` (The Autonomous Fact-Extraction Agent)
* **Location**: `app/memory/extractor.py`
* **Role**: After every chat turn, this agent scans the user's input text to identify personal details (`e.g. "I love eating pizza on Fridays"`).
* **Mechanism**: It sends a structured extraction prompt to Ollama (`JSON` output) or runs a high-precision Regex pipeline (`fallback_extract_facts_regex`) to extract `(key, value)` pairs like `("favorite food", "pizza")`. It then calls `MemoryRepository.create_or_update_memory()` to insert/update the `user_memory` table in PostgreSQL.

### 3. `ConversationSummarizer` (The Background Compressing Agent)
* **Location**: `app/memory/summarizer.py`
* **Role**: Monitors the exact depth of every conversation. Once `messages.count()` reaches or exceeds 30 (`summary_threshold = 30`):
  1. Fetches all older messages that have not yet been summarized (`offset = messages_summarized_count`).
  2. Prompts `llama3` to generate a concise, highly accurate paragraph summarizing key decisions and context (`"Summarize the following conversation..."`).
  3. Stores the output in the `conversation_summaries` table.
* **Benefit**: Ensures that conversations with 500+ messages never hit context limits or slow down local inference!

### 4. `PromptBuilder` (The RAG Context Assembly Agent)
* **Location**: `app/prompts/builder.py`
* **Role**: Assembles the exact payload sent to Ollama right before inference (`PromptBuilder.build_messages_payload()`).
* **What it weaves together**:
  * **System Persona**: `"You are an intelligent, helpful, and highly contextual AI Assistant..."`
  * **User Profile Header**: `"User Name: Varsha Sharma | Username: varsha"`
  * **Retrieved Long-Term Memories (`user_memory`)**: Checks PostgreSQL and injects:
    * `- Location: Bangalore`
    * `- Favorite food: Pizza`
    * `- Dog's name: Bruno`
  * **Latest Chat Summary (`conversation_summaries`)**: `"Summary of earlier conversation: ..."`
  * **Recent Message Window (`messages` table limit 10)**: Chronological turns immediately preceding the current prompt.

### 5. `AuthService` & `OllamaService` (Infrastructure Agents)
* **`AuthService` (`app/auth/service.py`)**: Manages `bcrypt` password verification, JWT access token issuing, and personalized greetings (`"Welcome back, Varsha!"`).
* **`OllamaService` (`app/chatbot/ollama_service.py`)**: Manages HTTP connection pooling (`http://localhost:11434`), checks availability, lists installed models, and yields streaming generator tokens (`generate_stream`).

---

## 🔄 5. End-to-End Execution Flow Summary

1. **User Login (`streamlit_app/components/auth_view.py`)**: User logs in with `varsha` / `securepassword`. `AuthService` checks `hashed_password` (`bcrypt`) in `users` table and initializes session state with a personalized greeting.
2. **Chat Input (`streamlit_app/components/chat_view.py`)**: User types: *"Hi! Where do I live and what is my dog's name?"*
3. **Storage & Retrieval (`ConversationService` -> `PromptBuilder`)**:
   * User input is stored right away in `messages`.
   * `PromptBuilder` fetches all facts from `user_memory` (where `location: Bangalore` and `dog's name: Bruno` were previously stored) and injects them into the system prompt.
4. **Streaming Inference (`OllamaService`)**: `llama3` reads the injected memory context and streams back tokens: *"Hello Varsha! You live in Bangalore, and your dog's name is Bruno!"* directly into the UI chat bubble (`st.write_stream`).
5. **Persistence & Diagnostics (`messages` & `audit_logs`)**: Assistant turn is appended to `messages` with `response_time_ms`. Diagnostic metadata (`OLLAMA_RESPONSE`, `response_time_ms = 1420ms`) is written to `audit_logs` where it can be inspected live on the **Analytics Page** (`render_analytics_view`).
