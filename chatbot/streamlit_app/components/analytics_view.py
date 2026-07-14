import streamlit as st
from sqlalchemy.orm import Session
from app.repositories.conversation_repository import ConversationRepository
from app.repositories.audit_repository import AuditRepository

def render_analytics_view(db: Session, user_id: str):
    """
    Renders the Analytics & Diagnostics dashboard displaying engagement statistics
    and live system audit logs.
    """
    conv_repo = ConversationRepository(db)
    audit_repo = AuditRepository(db)

    stats = conv_repo.get_user_analytics(user_id)

    st.markdown("## 📊 Analytics & System Diagnostics")
    st.caption("Track your conversational volume, model usage patterns, average response speed, and live system audit logs.")

    st.divider()

    # Metrics Display
    row1_cols = st.columns(3)
    with row1_cols[0]:
        st.metric("Total Conversations", stats["total_conversations"])
    with row1_cols[1]:
        st.metric("Total Messages", stats["total_messages"])
    with row1_cols[2]:
        st.metric("Avg Msgs / Conversation", f"{stats['avg_messages_per_conversation']}")

    row2_cols = st.columns(3)
    with row2_cols[0]:
        st.metric("Most Active Day", stats["most_active_day"][:15])
    with row2_cols[1]:
        st.metric("Most Frequently Used Model", f"🤖 {stats['most_frequently_used_model']}")
    with row2_cols[2]:
        st.metric("Avg Assistant Response Speed", f"⚡ {stats['avg_assistant_response_time_ms']} ms")

    st.divider()

    # System Audit & Diagnostics Logs
    st.markdown("### 🔍 Live System Audit & Diagnostics Logs (`audit_logs` in PostgreSQL)")
    st.caption("Provides full visibility into memory extraction, Ollama latency, login events, and database diagnostics.")

    filter_cols = st.columns([2, 1])
    with filter_cols[0]:
        event_options = [
            "All Events",
            "USER_LOGIN",
            "LOGIN_FAILED",
            "USER_REGISTER",
            "CONVERSATION_CREATED",
            "CONVERSATION_DELETED",
            "MEMORY_EXTRACTED",
            "CONVERSATION_SUMMARIZED",
            "OLLAMA_RESPONSE",
            "DATABASE_ERROR",
            "AUTH_FAILURE"
        ]
        selected_event = st.selectbox("Filter by Event Type", options=event_options, index=0)
    with filter_cols[1]:
        show_only_my_logs = st.checkbox("Show only my logs", value=True)

    target_user_id = user_id if show_only_my_logs else None
    target_event = selected_event if selected_event != "All Events" else None

    logs = audit_repo.get_logs(user_id=target_user_id, event_type=target_event, limit=100)

    if not logs:
        st.info("No diagnostic logs found matching the selected filters.")
    else:
        log_data = []
        for l in logs:
            log_data.append({
                "Timestamp (UTC)": l.timestamp.strftime("%Y-%m-%d %H:%M:%S") if l.timestamp else "",
                "Event Type": l.event_type,
                "Description": l.description,
                "Metadata": l.metadata_json or ""
            })
        st.dataframe(log_data, use_container_width=True, hide_index=True)
