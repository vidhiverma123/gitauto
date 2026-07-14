import streamlit as st
from sqlalchemy.orm import Session
from app.auth.service import AuthService

def render_auth_view(db: Session):
    """
    Renders clean, secure tabs for user registration and login.
    Once authenticated, stores user credentials and personalized greeting in session state.
    """
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0;">
        <h1 style="font-size: 2.5rem; font-weight: 700; background: linear-gradient(135deg, #38bdf8, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            Intelligent AI Chatbot
        </h1>
        <p style="color: #94a3b8; font-size: 1.1rem; max-width: 600px; margin: 0 auto;">
            Powered by local <b>Ollama</b> models, persistent <b>PostgreSQL</b> memory, and dynamic retrieval.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_register = st.tabs(["🔐 Log In", "✨ Create Account"])

        auth_service = AuthService(db)

        with tab_login:
            st.markdown("### Welcome Back")
            with st.form("login_form", clear_on_submit=False):
                username_or_email = st.text_input("Username or Email", placeholder="e.g. varsha or varsha@example.com")
                password = st.text_input("Password", type="password")
                submit_login = st.form_submit_button("Sign In", use_container_width=True)

                if submit_login:
                    if not username_or_email or not password:
                        st.error("Please enter both username/email and password.")
                    else:
                        user, error = auth_service.authenticate_user(username_or_email, password)
                        if error or not user:
                            st.error(f"⚠️ {error}")
                        else:
                            greeting = auth_service.get_personalized_greeting(user)
                            st.session_state.user_id = user.id
                            st.session_state.username = user.username
                            st.session_state.full_name = user.full_name
                            st.session_state.greeting = greeting
                            st.success(greeting)
                            st.rerun()

        with tab_register:
            st.markdown("### Join & Build Personalized AI Memory")
            with st.form("register_form", clear_on_submit=True):
                full_name = st.text_input("Full Name", placeholder="e.g. Varsha Sharma")
                username = st.text_input("Username", placeholder="e.g. varsha_s")
                email = st.text_input("Email", placeholder="e.g. varsha@example.com")
                reg_password = st.text_input("Password (min 6 characters)", type="password")
                reg_confirm = st.text_input("Confirm Password", type="password")
                submit_reg = st.form_submit_button("Register Securely", use_container_width=True)

                if submit_reg:
                    if reg_password != reg_confirm:
                        st.error("⚠️ Passwords do not match.")
                    elif len(reg_password) < 6:
                        st.error("⚠️ Password must be at least 6 characters.")
                    else:
                        user, error = auth_service.register_user(full_name, username, email, reg_password)
                        if error or not user:
                            st.error(f"⚠️ {error}")
                        else:
                            greeting = auth_service.get_personalized_greeting(user)
                            st.session_state.user_id = user.id
                            st.session_state.username = user.username
                            st.session_state.full_name = user.full_name
                            st.session_state.greeting = greeting
                            st.success(f"Account created successfully! {greeting}")
                            st.rerun()
