import os
import sys
from pathlib import Path

# Add project root directory to Python path so `app.*` modules can be imported directly
root_path = Path(__file__).resolve().parent.parent
if str(root_path) not in sys.path:
    sys.path.insert(0, str(root_path))

import streamlit as st
from app.database.connection import SessionLocal, init_db
from streamlit_app.styles.custom_css import apply_custom_styles
from streamlit_app.components import (
    render_auth_view,
    render_sidebar,
    render_chat_view,
    render_profile_view,
    render_settings_view,
    render_analytics_view
)

st.set_page_config(
    page_title="Intelligent AI Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Initialize database tables automatically if not already created
    try:
        init_db()
    except Exception as e:
        st.error(f"Failed to connect to database or initialize schema: {e}")
        return

    # Create database session for this Streamlit turn
    db = SessionLocal()
    try:
        # Apply custom theme styles
        current_theme = st.session_state.get("theme", "dark")
        apply_custom_styles(theme=current_theme)

        # Check authentication status
        user_id = st.session_state.get("user_id")
        if not user_id:
            render_auth_view(db)
        else:
            # Render Navigation Sidebar and get active tab view
            active_view = render_sidebar(db, user_id)

            # Render active view content
            if active_view == "chat":
                render_chat_view(db, user_id)
            elif active_view == "profile":
                render_profile_view(db, user_id)
            elif active_view == "settings":
                render_settings_view(db, user_id)
            elif active_view == "analytics":
                render_analytics_view(db, user_id)
            else:
                render_chat_view(db, user_id)
    finally:
        db.close()

if __name__ == "__main__":
    main()
