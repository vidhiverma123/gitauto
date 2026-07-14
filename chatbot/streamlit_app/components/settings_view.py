import streamlit as st
from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.chatbot.ollama_service import OllamaService
from app.utils.logger import log_event

def render_settings_view(db: Session, user_id: str):
    """
    Renders the Settings page allowing configuration of preferred Ollama model,
    generation temperature, max token output, and app color theme (Dark / Light).
    """
    user_repo = UserRepository(db)
    ollama_service = OllamaService()

    setting = user_repo.get_settings(user_id)
    if not setting:
        st.error("Settings not found.")
        return

    st.markdown("## ⚙️ Application & Model Settings")
    st.caption("Customize your local LLM inference parameters and UI visual preferences.")

    st.divider()

    with st.form("settings_form"):
        st.markdown("### 🤖 Ollama LLM Configuration")
        
        available_models = ollama_service.list_available_models()
        if setting.preferred_ollama_model not in available_models:
            available_models.append(setting.preferred_ollama_model)

        preferred_model = st.selectbox(
            "Preferred Default Ollama Model",
            options=available_models,
            index=available_models.index(setting.preferred_ollama_model) if setting.preferred_ollama_model in available_models else 0,
            help="This model will be selected by default when starting new conversations."
        )

        temperature = st.slider(
            "Model Temperature (Creativity vs. Precision)",
            min_value=0.1,
            max_value=1.0,
            value=float(setting.temperature),
            step=0.05,
            help="Lower values (e.g. 0.2) produce more deterministic, factual responses. Higher values (e.g. 0.8) increase creativity."
        )

        max_tokens = st.slider(
            "Max Tokens per Response (`num_predict`)",
            min_value=256,
            max_value=4096,
            value=int(setting.max_tokens),
            step=128,
            help="Maximum number of tokens Ollama will generate for a single turn."
        )

        st.markdown("### 🎨 UI Appearance")
        theme_options = ["dark", "light"]
        theme = st.radio(
            "Theme Color Mode",
            options=theme_options,
            format_func=lambda x: "🌙 Dark Mode (Sleek Glassmorphism)" if x == "dark" else "☀️ Light Mode (Clean White)",
            index=0 if setting.theme == "dark" else 1
        )

        st.divider()
        save_btn = st.form_submit_button("💾 Save Settings", use_container_width=True)

        if save_btn:
            user_repo.update_settings(
                user_id=user_id,
                preferred_model=preferred_model,
                temperature=temperature,
                max_tokens=max_tokens,
                theme=theme
            )
            st.session_state.preferred_model = preferred_model
            st.session_state.temperature = temperature
            st.session_state.max_tokens = max_tokens
            st.session_state.theme = theme

            log_event(db, "SETTINGS_UPDATED", f"Updated settings to model={preferred_model}, temp={temperature}", user_id=user_id)
            st.success("✅ Settings updated successfully!")
            st.rerun()
