import streamlit as st
from sqlalchemy.orm import Session
from app.repositories.conversation_repository import ConversationRepository
from app.utils.logger import log_event

def render_library_view(db: Session, user_id: str):
    """
    Renders the Chatbot Library & Top Conversations page.
    Allows sorting and displaying top chats based on various condition metrics.
    """
    conv_repo = ConversationRepository(db)
    
    st.markdown("## 📚 Chatbot Library & Top Conversations")
    st.caption("Browse, sort, and analyze your conversations based on message volume, recent activity, response speed, or content size.")
    st.divider()

    # Dropdowns for configuration
    col1, col2 = st.columns(2)
    with col1:
        condition_options = {
            "most_recent": "Most Recent Activity 📅",
            "most_messages": "Most Messages Count 💬",
            "longest_avg_response": "Longest Average Response Time (ms) 🐌",
            "shortest_avg_response": "Shortest Average Response Time (ms) ⚡",
            "longest_content": "Longest Conversations (Characters) 📏"
        }
        selected_condition = st.selectbox(
            "Sort Condition",
            options=list(condition_options.keys()),
            format_func=lambda x: condition_options[x]
        )
    with col2:
        selected_limit = st.selectbox(
            "Max Chats to Display",
            options=[5, 10, 15, 20, 30, 50],
            index=0
        )

    st.divider()

    # Fetch top chats
    results = conv_repo.get_top_conversations(user_id, condition=selected_condition, limit=selected_limit)

    if not results:
        st.info("No conversations found matching this criteria. Start a new chat to accumulate metrics!")
        return

    # Theme parameters for premium CSS cards
    is_dark = (st.session_state.get("theme", "dark") == "dark")
    card_bg = "rgba(30, 41, 59, 0.7)" if is_dark else "rgba(255, 255, 255, 0.85)"
    text_color = "#f1f5f9" if is_dark else "#1e293b"
    border_color = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.08)"

    # Render Cards
    for idx, item in enumerate(results, start=1):
        conv = item["conversation"]
        metric_name = item["metric_name"]
        metric_value = item["metric_value"]

        # Medal icons for top 3
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"

        st.markdown(f"""
        <div style="
            background: {card_bg}; 
            border-left: 4px solid #38bdf8; 
            padding: 16px; 
            border-radius: 10px; 
            margin-bottom: 12px;
            border-top: 1px solid {border_color};
            border-right: 1px solid {border_color};
            border-bottom: 1px solid {border_color};
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div>
                    <span style="font-size: 1.25rem; font-weight: bold; margin-right: 8px;">{medal}</span>
                    <span style="font-size: 1.1rem; font-weight: 600; color: {text_color};">{conv.title}</span>
                </div>
                <div style="background: rgba(56, 189, 248, 0.15); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 6px; padding: 4px 10px; font-size: 0.85rem; color: #38bdf8; font-weight: 600;">
                    {metric_name}: {metric_value}
                </div>
            </div>
            <div style="margin-top: 8px; font-size: 0.85rem; color: #94a3b8;">
                <span style="margin-right: 16px;">🤖 Model: <code>{conv.ollama_model_used}</code></span>
                <span>📅 Created: {conv.created_at.strftime('%Y-%m-%d %H:%M UTC') if conv.created_at else 'N/A'}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Inline Action Buttons
        btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1.5, 1.2, 1.2, 5])
        with btn_col1:
            if st.button("💬 Open Chat", key=f"lib_open_{conv.id}", use_container_width=True):
                st.session_state.current_conversation_id = conv.id
                st.session_state.active_view = "chat"
                st.rerun()
        with btn_col2:
            pin_lbl = "📍 Unpin" if conv.is_pinned else "📌 Pin"
            if st.button(pin_lbl, key=f"lib_pin_{conv.id}", use_container_width=True):
                conv_repo.toggle_pin(conv.id)
                st.rerun()
        with btn_col3:
            if st.button("🗑️ Delete", key=f"lib_del_{conv.id}", use_container_width=True):
                conv_repo.delete_conversation(conv.id)
                log_event(db, "CONVERSATION_DELETED", f"Deleted conversation {conv.id} via Library page", user_id=user_id)
                if st.session_state.get("current_conversation_id") == conv.id:
                    st.session_state.current_conversation_id = None
                st.rerun()
        with btn_col4:
            st.write("") # Spacer

        st.markdown("<div style='margin-bottom: 24px;'></div>", unsafe_allow_html=True)
