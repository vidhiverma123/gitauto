# 🚀 feature/postgres-mode Branch Updates & Changelog

This document provides a summary of all architectural updates, new features, and database/LLM enhancements introduced on the **`feature/postgres-mode`** branch.

---

## 1. 📊 Chatbot Library & Top Conversations Feature (New)
We introduced a **Chatbot Library** dashboard page (`render_library_view`) allowing users to easily analyze, rank, and manage their conversation histories using database-level metrics.

### Key Capabilities:
- **Five Sort Conditions**:
  1. **Most Recent Activity**: Sorted by `updated_at` timestamp.
  2. **Most Messages Count**: Order by conversations with the highest message volume.
  3. **Longest Average Response Time (ms)**: Order by conversations where assistant average latency is highest.
  4. **Shortest Average Response Time (ms)**: Order by conversations where assistant average latency is lowest (excluding null values).
  5. **Longest Conversations (Characters)**: Order by total combined string length of all user and assistant messages.
- **Top N Limits**: Selectable counts (5, 10, 15, 20, 30, 50) using interactive dropdown controls.
- **Interactive Library Cards**: High-end glassmorphic UI card designs displaying:
  - Ranking medals (🥇, 🥈, 🥉 for the top 3).
  - Selected sort metric value.
  - LLM model used and creation timestamp.
  - Badges displaying conversation tags.
- **Inline Controls**:
  - 💬 **Open Chat**: Loads the conversation history and redirects the active view to the Chat workspace.
  - 📌 **Pin / Unpin**: Quick-toggles pinned status.
  - 🗑️ **Delete**: Removes the conversation from PostgreSQL.

### Implemented Files:
- [NEW] [library_view.py](file:///Users/as-mac-1375/Documents/GitHub/gitauto/chatbot/streamlit_app/components/library_view.py) - Streamlit page container.
- [MODIFY] [conversation_repository.py](file:///Users/as-mac-1375/Documents/GitHub/gitauto/chatbot/app/repositories/conversation_repository.py#L221) - DB query methods for top conversations.
- [MODIFY] [dto.py](file:///Users/as-mac-1375/Documents/GitHub/gitauto/chatbot/app/schemas/dto.py#L86) - Added `TopConversationResponse` schema structure.
- [MODIFY] [main.py](file:///Users/as-mac-1375/Documents/GitHub/gitauto/chatbot/app/main.py#L115) - Added `/api/conversations/top` REST API endpoint.
- [MODIFY] [sidebar.py](file:///Users/as-mac-1375/Documents/GitHub/gitauto/chatbot/streamlit_app/components/sidebar.py#L44-L48) - Added `📚` library to the navigation grid.
- [MODIFY] [main.py](file:///Users/as-mac-1375/Documents/GitHub/gitauto/chatbot/streamlit_app/main.py#L55-L57) - Added library rendering router.
- [MODIFY] [__init__.py](file:///Users/as-mac-1375/Documents/GitHub/gitauto/chatbot/streamlit_app/components/__init__.py#L7) - Exported the library page render method.
- [MODIFY] [test_conversations.py](file:///Users/as-mac-1375/Documents/GitHub/gitauto/chatbot/tests/test_conversations.py#L65) - Added database tests covering all 5 metrics.

---

## 2. 🗄️ PostgreSQL Default Database & Alembic Integration
- Switched default backend configurations to **PostgreSQL** by default, aligning database sessions (`connection.py`) with pgpool features and automatic retry schemas.
- Configured connection arguments cleanly to prevent connection leaking or threading bottlenecks across FastAPI and Streamlit worker pools.

---

## 3. 🤖 Hybrid LLM Inference Pipeline
Enhanced `OllamaService` with a hybrid inference client configuration supporting local models and cloud providers:
- **Local Ollama Fallback**: Maintains fast local model routing (`llama3`, `qwen`, `mistral`).
- **Cloud LLM API Support**: Added settings-configurable support for **OpenAI** and **Google Gemini** API connections.
- **Provider Switching UI**: Fully integrated API Key entry fields and provider select dropdowns directly inside the **Settings** view (`settings_view.py`).

---

## 🚀 Pushing Changes to Git
To commit and push all newly implemented files and modifications, run the following commands:

```bash
# 1. Stage the modifications and the new files
git add .

# 2. Commit the changes
git commit -m "feat: implement top chats library view and PostgreSQL metrics querying"

# 3. Push to the remote branch
git push origin feature/postgres-mode
```
