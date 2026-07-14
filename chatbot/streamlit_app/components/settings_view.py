import streamlit as st
from sqlalchemy.orm import Session
from app.repositories.user_repository import UserRepository
from app.chatbot.ollama_service import OllamaService
from app.utils.logger import log_event

def render_settings_view(db: Session, user_id: str):
    """
    Renders the Settings page allowing configuration of preferred LLM provider,
    cloud API keys/endpoints, preferred default model, generation temperature,
    max token output, and app color theme (Dark / Light).
    """
    user_repo = UserRepository(db)
    ollama_service = OllamaService()

    setting = user_repo.get_settings(user_id)
    if not setting:
        st.error("Settings not found.")
        return

    st.markdown("## ⚙️ Application & Model Settings")
    st.caption("Customize your LLM inference parameters (local/cloud) and UI visual preferences.")

    st.divider()

    # Providers dictionary mapping identifier to user-facing labels
    providers = {
        "ollama": "Local Ollama (Offline / Open-Source)",
        "openai": "OpenAI (Cloud API)",
        "gemini": "Google Gemini (Cloud API)",
        "custom": "Custom OpenAI-Compatible Endpoint (Groq, TogetherAI, etc.)"
    }

    st.markdown("### 🤖 LLM Provider & API Configuration")
    
    # 1. Provider Selection
    selected_provider = st.selectbox(
        "Select LLM Provider",
        options=list(providers.keys()),
        format_func=lambda x: providers[x],
        index=list(providers.keys()).index(setting.llm_provider) if setting.llm_provider in providers else 0,
        help="Choose whether to run models locally via Ollama or connect to a cloud service."
    )

    # 2. Conditional API Inputs based on Selected Provider
    api_key = setting.api_key or ""
    api_base_url = setting.api_base_url or ""

    if selected_provider != "ollama":
        api_key = st.text_input(
            "API Key",
            value=setting.api_key if setting.api_key else "",
            type="password",
            placeholder="Paste your API key here...",
            help=f"Enter your secret API credentials for {providers[selected_provider]}."
        )

    if selected_provider == "custom":
        api_base_url = st.text_input(
            "API Base URL",
            value=setting.api_base_url if setting.api_base_url else "",
            placeholder="e.g., https://api.groq.com/openai/v1",
            help="Specify the base URL of the OpenAI-compatible endpoint."
        )

    # 3. Model Selector (updates dynamically based on chosen provider)
    available_models = ollama_service.list_available_models(selected_provider)
    current_preferred = setting.preferred_ollama_model
    if current_preferred not in available_models:
        available_models.append(current_preferred)

    preferred_model = st.selectbox(
        "Preferred Default Model",
        options=available_models,
        index=available_models.index(current_preferred) if current_preferred in available_models else 0,
        help="This model will be selected by default when starting new conversations."
    )

    st.markdown("### 🎛️ Inference Parameters")
    
    temperature = st.slider(
        "Model Temperature (Creativity vs. Precision)",
        min_value=0.1,
        max_value=1.0,
        value=float(setting.temperature),
        step=0.05,
        help="Lower values (e.g., 0.2) produce more deterministic, factual responses. Higher values (e.g., 0.8) increase creativity."
    )

    max_tokens = st.slider(
        "Max Tokens per Response",
        min_value=256,
        max_value=4096,
        value=int(setting.max_tokens),
        step=128,
        help="Maximum number of tokens the model will generate for a single turn."
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
    save_btn = st.button("💾 Save Settings", use_container_width=True, type="primary")

    if save_btn:
        user_repo.update_settings(
            user_id=user_id,
            preferred_model=preferred_model,
            temperature=temperature,
            max_tokens=max_tokens,
            theme=theme,
            llm_provider=selected_provider,
            api_key=api_key if selected_provider != "ollama" else None,
            api_base_url=api_base_url if selected_provider == "custom" else None
        )
        st.session_state.preferred_model = preferred_model
        st.session_state.temperature = temperature
        st.session_state.max_tokens = max_tokens
        st.session_state.theme = theme
        st.session_state.llm_provider = selected_provider

        log_event(db, "SETTINGS_UPDATED", f"Updated settings to provider={selected_provider}, model={preferred_model}, temp={temperature}", user_id=user_id)
        st.success("✅ Settings updated successfully!")
        st.rerun()
