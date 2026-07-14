import streamlit as st
from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.repositories.conversation_repository import ConversationRepository
from app.chatbot.conversation_service import ConversationService
from app.chatbot.ollama_service import OllamaService
from app.services.export_service import ExportService

def render_chat_view(db: Session, user_id: str):
    """
    Renders the main chat interface supporting token-by-token streaming, Markdown formatting,
    model selection, retrieval pipeline inspection, and multi-format chat export (MD, JSON, PDF).
    """
    user_repo = UserRepository(db)
    conv_repo = ConversationRepository(db)
    conv_service = ConversationService(db)
    ollama_service = OllamaService()

    user = user_repo.get_by_id(user_id)
    if not user:
        st.error("User session expired. Please log in again.")
        return

    # Ensure a conversation is selected or create one automatically
    conv_id = st.session_state.get("current_conversation_id")
    conv = conv_repo.get_by_id(conv_id) if conv_id else None
    if not conv:
        preferred_model = st.session_state.get("preferred_model", "llama3")
        conv = conv_service.start_new_conversation(user_id, model_used=preferred_model)
        st.session_state.current_conversation_id = conv.id

    # Check Ollama Server Connection
    is_ollama_up = ollama_service.check_connection()

    # Top Control Header
    header_cols = st.columns([3, 2, 2])
    with header_cols[0]:
        st.markdown(f"### {conv.title}")
        if conv.tags:
            tags_html = "".join([f'<span class="tag-pill">#{tag.name}</span>' for tag in conv.tags])
            st.markdown(tags_html, unsafe_allow_html=True)
        else:
            st.caption("No tags yet (auto-assigned after first chat exchange)")

    with header_cols[1]:
        available_models = ollama_service.list_available_models()
        current_model = st.session_state.get("preferred_model", conv.ollama_model_used)
        if current_model not in available_models:
            available_models.append(current_model)
        
        selected_model = st.selectbox(
            "🤖 Ollama Model",
            options=available_models,
            index=available_models.index(current_model) if current_model in available_models else 0,
            key="chat_model_selector"
        )
        if selected_model != st.session_state.get("preferred_model"):
            st.session_state.preferred_model = selected_model
            user_repo.update_settings(user_id, preferred_model=selected_model)

    with header_cols[2]:
        status_color = "🟢 Online" if is_ollama_up else "🔴 Offline (Fallback)"
        st.markdown(f"**Ollama Engine:** `{status_color}`")
        
        # Export Popover
        with st.popover("📥 Export Chat", use_container_width=True):
            messages = conv_repo.get_messages(conv.id)
            if not messages:
                st.caption("No messages to export.")
            else:
                md_data = ExportService.to_markdown(conv, messages)
                json_data = ExportService.to_json(conv, messages)
                pdf_data = ExportService.to_pdf_bytes(conv, messages)

                st.download_button(
                    label="📄 Download Markdown (.md)",
                    data=md_data,
                    file_name=f"chat_{conv.id[:8]}.md",
                    mime="text/markdown",
                    use_container_width=True
                )
                st.download_button(
                    label="📦 Download JSON (.json)",
                    data=json_data,
                    file_name=f"chat_{conv.id[:8]}.json",
                    mime="application/json",
                    use_container_width=True
                )
                st.download_button(
                    label="📑 Download PDF (.pdf)",
                    data=pdf_data,
                    file_name=f"chat_{conv.id[:8]}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

    st.divider()

    # Inspect Memory & Retrieval Pipeline Prompt Expander
    with st.expander("🧠 Inspect Memory Retrieval & Prompt Construction Pipeline", expanded=False):
        st.markdown("Before sending every message to Ollama, the **Prompt Builder** dynamically injects **User Profile**, retrieved **Long-Term Memories**, and **Summaries**:")
        debug_str = conv_service.get_debug_prompt_display(user, conv.id, "Preview of next user turn...")
        st.code(debug_str, language="markdown")

    # Display Conversation Messages
    messages = conv_repo.get_messages(conv.id)
    if not messages:
        st.info("👋 Hello! Ask me anything or share facts about yourself (e.g. *'My favorite programming language is Python'* or *'I have a dog named Bruno'*). I will remember them across sessions!")
    else:
        for msg in messages:
            with st.chat_message(msg.role):
                st.markdown(msg.content)
                if msg.role == "assistant":
                    meta_info = []
                    if msg.ollama_model_used:
                        meta_info.append(f"🤖 Model: `{msg.ollama_model_used}`")
                    if msg.response_time_ms is not None:
                        meta_info.append(f"⚡ Time: `{msg.response_time_ms}ms`")
                    if meta_info:
                        st.caption(" | ".join(meta_info))

    # User Chat Input
    user_input = st.chat_input("Type your message here... (Try saying 'My favorite food is pizza' or 'Where do I live?')")
    if user_input:
        # Display user message instantly
        with st.chat_message("user"):
            st.markdown(user_input)

        # Display assistant streaming response
        with st.chat_message("assistant"):
            with st.status("Assistant is thinking and retrieving contextual memories...", expanded=False) as status:
                st.write("Checking long-term memory store (`user_memory` table in PostgreSQL)...")
                st.write("Assembling system instructions and conversation summary...")
                status.update(label="Ready to stream from Ollama!", state="complete")

            # Stream response generator
            response_generator = conv_service.send_message_and_stream_response(
                user=user,
                conversation_id=conv.id,
                user_message_text=user_input,
                model_used=selected_model,
                temperature=st.session_state.get("temperature", 0.7),
                max_tokens=st.session_state.get("max_tokens", 1024)
            )

            # Stream token-by-token
            st.write_stream(response_generator)

        # Trigger full rerun to update sidebar titles, tags, and refresh history
        st.rerun()
