from datetime import datetime
import streamlit as st
from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.memory_repository import MemoryRepository

def render_profile_view(db: Session, user_id: str):
    """
    Renders the User Profile page displaying personal details, engagement statistics,
    and an interactive Long-Term Memory Fact Manager.
    """
    user_repo = UserRepository(db)
    conv_repo = ConversationRepository(db)
    mem_repo = MemoryRepository(db)

    user = user_repo.get_by_id(user_id)
    if not user:
        st.error("User session expired.")
        return

    setting = user_repo.get_settings(user_id)
    stats = conv_repo.get_user_analytics(user_id)

    st.markdown("## 👤 User Profile & Memory Store")
    st.caption("Here you can inspect your account details, activity statistics, and all long-term facts the AI has remembered about you.")

    st.divider()

    # Profile & Activity Summary Cards
    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown("### 📋 Account Information")
        st.markdown(f"- **Full Name:** `{user.full_name}`")
        st.markdown(f"- **Username:** `{user.username}`")
        st.markdown(f"- **Email:** `{user.email}`")
        st.markdown(f"- **Joined Date:** `{user.created_at.strftime('%Y-%m-%d %H:%M UTC')}`")
        last_login = user.last_login_at.strftime('%Y-%m-%d %H:%M UTC') if user.last_login_at else "Just now"
        st.markdown(f"- **Last Login:** `{last_login}`")
        st.markdown(f"- **Favorite Model:** `{setting.preferred_ollama_model if setting else 'llama3'}`")

    with col2:
        st.markdown("### 📊 Activity Metrics")
        mcol1, mcol2 = st.columns(2)
        with mcol1:
            st.metric("Total Conversations", stats["total_conversations"])
            st.metric("Total Messages", stats["total_messages"])
        with mcol2:
            st.metric("Avg Msgs / Chat", f"{stats['avg_messages_per_conversation']}")
            st.metric("Most Active Day", stats["most_active_day"][:12])

    st.divider()

    # Long-Term Memory Fact Manager
    st.markdown("### 🧠 Long-Term User Memory Table (`user_memory` in PostgreSQL)")
    st.markdown("Whenever you mention facts about yourself in chats (such as *'My birthday is July 20'* or *'I have a dog named Bruno'*), the AI automatically extracts and saves them below. You can also manually add or delete facts:")

    memories = mem_repo.get_user_memories(user.id)

    # Manual Memory Addition Form
    with st.form("add_memory_form", clear_on_submit=True):
        fcol1, fcol2, fcol3 = st.columns([2, 3, 1])
        with fcol1:
            new_key = st.text_input("Fact Key", placeholder="e.g. favorite programming language")
        with fcol2:
            new_val = st.text_input("Fact Value", placeholder="e.g. Python")
        with fcol3:
            st.write("") # Spacer
            st.write("")
            submit_mem = st.form_submit_button("➕ Add Fact", use_container_width=True)

        if submit_mem:
            if not new_key.strip() or not new_val.strip():
                st.error("Please provide both Fact Key and Fact Value.")
            else:
                mem_repo.create_or_update_memory(user.id, new_key.strip(), new_val.strip(), raw_text="Added via Profile UI")
                st.success(f"Remembered: [{new_key.strip()}: {new_val.strip()}]")
                st.rerun()

    # Display Extracted Memories
    if not memories:
        st.info("No long-term memories extracted yet. Try chatting with the AI and sharing a fact about yourself!")
    else:
        for mem in memories:
            mcol_left, mcol_right = st.columns([5, 1])
            with mcol_left:
                st.markdown(f"""
                <div class="memory-card">
                    <b style="color: #38bdf8;">{mem.fact_key.upper()}:</b> {mem.fact_value}
                    <br/><small style="color: #6b7280;">Updated: {mem.updated_at.strftime('%Y-%m-%d %H:%M')}</small>
                </div>
                """, unsafe_allow_html=True)
            with mcol_right:
                if st.button("🗑️ Delete", key=f"del_mem_{mem.id}", use_container_width=True):
                    mem_repo.delete_memory(mem.id, user.id)
                    st.rerun()
