from datetime import datetime, timezone, timedelta
import streamlit as st
from sqlalchemy.orm import Session
from app.repositories.conversation_repository import ConversationRepository
from app.chatbot.conversation_service import ConversationService
from app.utils.logger import log_event

def render_sidebar(db: Session, user_id: str) -> str:
    """
    Renders the sidebar including user greeting, view navigation, conversation management,
    full-text keyword search, tag filtering, and grouped chat history (Today, Yesterday, Last 7 Days, Older).
    Returns the currently active view name ('chat', 'profile', 'settings', or 'analytics').
    """
    conv_repo = ConversationRepository(db)
    conv_service = ConversationService(db)

    with st.sidebar:
        # Personalized Greeting Display
        greeting = st.session_state.get("greeting", f"Welcome back, {st.session_state.get('full_name', 'User')}!")
        st.markdown(f"""
        <div style="padding: 10px 14px; background: rgba(56, 189, 248, 0.1); border-left: 4px solid #38bdf8; border-radius: 8px; margin-bottom: 16px;">
            <div style="font-weight: 600; font-size: 0.95rem; color: #38bdf8;">👋 {greeting}</div>
        </div>
        """, unsafe_allow_html=True)

        # View Navigation
        active_view = st.session_state.get("active_view", "chat")
        nav_cols = st.columns(4)
        with nav_cols[0]:
            if st.button("💬", help="Chat Window", use_container_width=True, type="primary" if active_view == "chat" else "secondary"):
                st.session_state.active_view = "chat"
                st.rerun()
        with nav_cols[1]:
            if st.button("👤", help="User Profile & Memory", use_container_width=True, type="primary" if active_view == "profile" else "secondary"):
                st.session_state.active_view = "profile"
                st.rerun()
        with nav_cols[2]:
            if st.button("⚙️", help="Settings", use_container_width=True, type="primary" if active_view == "settings" else "secondary"):
                st.session_state.active_view = "settings"
                st.rerun()
        with nav_cols[3]:
            if st.button("📊", help="Analytics & Audit Logs", use_container_width=True, type="primary" if active_view == "analytics" else "secondary"):
                st.session_state.active_view = "analytics"
                st.rerun()

        st.divider()

        # Start New Chat Button
        if st.button("➕ Start New Chat", use_container_width=True, type="primary"):
            preferred_model = st.session_state.get("preferred_model", "llama3")
            new_conv = conv_service.start_new_conversation(user_id, model_used=preferred_model)
            st.session_state.current_conversation_id = new_conv.id
            st.session_state.active_view = "chat"
            st.rerun()

        # Search and Filter
        st.markdown("#### 🔍 Search & Filter")
        search_kw = st.text_input("Search keyword across titles & messages", value=st.session_state.get("search_keyword", ""), placeholder="e.g. Python, SQL, Bruno...", key="sb_search")
        st.session_state.search_keyword = search_kw

        tag_options = ["All", "Programming", "SQL", "AI", "Travel", "Finance", "Education", "Personal"]
        selected_tag = st.selectbox("Filter by Tag", options=tag_options, index=tag_options.index(st.session_state.get("selected_tag", "All")), key="sb_tag")
        st.session_state.selected_tag = selected_tag

        st.divider()

        # Fetch matching conversations
        conversations = conv_repo.search_conversations(user_id, keyword=search_kw, tag_name=selected_tag)

        # Group conversations by Pinned and Date buckets
        now = datetime.now(timezone.utc)
        today_date = now.date()
        yesterday_date = today_date - timedelta(days=1)
        seven_days_ago = today_date - timedelta(days=7)

        pinned_convs = [c for c in conversations if c.is_pinned]
        unpinned_convs = [c for c in conversations if not c.is_pinned]

        today_convs = [c for c in unpinned_convs if c.updated_at and c.updated_at.date() == today_date]
        yesterday_convs = [c for c in unpinned_convs if c.updated_at and c.updated_at.date() == yesterday_date]
        last_7_days_convs = [c for c in unpinned_convs if c.updated_at and seven_days_ago <= c.updated_at.date() < yesterday_date]
        older_convs = [c for c in unpinned_convs if not c.updated_at or c.updated_at.date() < seven_days_ago]

        def render_conversation_item(c):
            is_active = (st.session_state.get("current_conversation_id") == c.id)
            title_display = (f"📌 " if c.is_pinned else "💬 ") + (c.title[:24] + "..." if len(c.title) > 24 else c.title)

            col_main, col_actions = st.columns([4, 1])
            with col_main:
                if st.button(
                    title_display,
                    key=f"btn_conv_{c.id}",
                    use_container_width=True,
                    type="primary" if is_active else "secondary",
                    help=f"Model: {c.ollama_model_used} | Created: {c.created_at.strftime('%Y-%m-%d')}"
                ):
                    st.session_state.current_conversation_id = c.id
                    st.session_state.active_view = "chat"
                    st.rerun()

            with col_actions:
                with st.popover("⚙️", use_container_width=True):
                    st.markdown(f"**Manage:** `{c.title}`")
                    # Pin/Unpin
                    pin_label = "📍 Unpin" if c.is_pinned else "📌 Pin"
                    if st.button(pin_label, key=f"pin_{c.id}", use_container_width=True):
                        conv_repo.toggle_pin(c.id)
                        st.rerun()

                    # Rename
                    new_title = st.text_input("New Title", value=c.title, key=f"ren_input_{c.id}")
                    if st.button("✏️ Rename", key=f"ren_btn_{c.id}", use_container_width=True):
                        if new_title.strip():
                            conv_repo.update_title(c.id, new_title.strip())
                            st.rerun()

                    # Delete
                    if st.button("🗑️ Delete", key=f"del_{c.id}", use_container_width=True):
                        conv_repo.delete_conversation(c.id)
                        log_event(db, "CONVERSATION_DELETED", f"Deleted conversation {c.id}", user_id=user_id)
                        if st.session_state.get("current_conversation_id") == c.id:
                            st.session_state.current_conversation_id = None
                        st.rerun()

        if not conversations:
            st.caption("No conversations found matching criteria.")
        else:
            if pinned_convs:
                st.markdown("##### 📌 Pinned")
                for c in pinned_convs:
                    render_conversation_item(c)

            if today_convs:
                st.markdown("##### 📅 Today")
                for c in today_convs:
                    render_conversation_item(c)

            if yesterday_convs:
                st.markdown("##### 📆 Yesterday")
                for c in yesterday_convs:
                    render_conversation_item(c)

            if last_7_days_convs:
                st.markdown("##### 🗓️ Last 7 Days")
                for c in last_7_days_convs:
                    render_conversation_item(c)

            if older_convs:
                st.markdown("##### 🗄️ Older")
                for c in older_convs:
                    render_conversation_item(c)

        st.divider()
        if st.button("🚪 Log Out", use_container_width=True):
            log_event(db, "USER_LOGOUT", f"User logged out: {st.session_state.get('username')}", user_id=user_id)
            for k in ["user_id", "username", "full_name", "greeting", "current_conversation_id"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()

    return st.session_state.get("active_view", "chat")
