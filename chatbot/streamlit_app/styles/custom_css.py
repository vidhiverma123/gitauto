import streamlit as st

def apply_custom_styles(theme: str = "dark"):
    """
    Inject rich, premium CSS styling with glassmorphism, dynamic gradients,
    curated color palettes, and micro-animations to create an exceptional user experience.
    """
    is_dark = (theme == "dark")
    bg_color = "#0f172a" if is_dark else "#f8fafc"
    card_bg = "rgba(30, 41, 59, 0.7)" if is_dark else "rgba(255, 255, 255, 0.85)"
    border_color = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.08)"
    text_color = "#f1f5f9" if is_dark else "#1e293b"
    accent_color = "#38bdf8" if is_dark else "#0284c7"
    chat_user_bg = "rgba(56, 189, 248, 0.15)" if is_dark else "rgba(2, 132, 199, 0.1)"
    chat_bot_bg = "rgba(30, 41, 59, 0.9)" if is_dark else "rgba(255, 255, 255, 0.95)"

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=Fira+Code:wght@400;500&display=swap');

    html, body, [class*="css"] {{
        font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif !important;
        color: {text_color};
    }}

    /* Global App Background */
    .stApp {{
        background-color: {bg_color};
        background-image: radial-gradient(at 10% 10%, rgba(56, 189, 248, 0.05) 0px, transparent 50%),
                          radial-gradient(at 90% 90%, rgba(168, 85, 247, 0.05) 0px, transparent 50%);
    }}

    /* Premium Metric Cards */
    div[data-testid="stMetric"] {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.1);
        backdrop-filter: blur(10px);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}
    div[data-testid="stMetric"]:hover {{
        transform: translateY(-3px);
        box-shadow: 0 10px 25px -5px rgba(56, 189, 248, 0.2);
    }}

    /* Sidebar Glassmorphism */
    section[data-testid="stSidebar"] {{
        background: {'rgba(15, 23, 42, 0.95)' if is_dark else 'rgba(241, 245, 249, 0.95)'} !important;
        border-right: 1px solid {border_color};
        backdrop-filter: blur(16px);
    }}

    /* Chat Bubbles Enhancement */
    div[data-testid="stChatMessage"] {{
        border-radius: 16px;
        padding: 1.25rem;
        margin-bottom: 1rem;
        border: 1px solid {border_color};
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease;
    }}
    div[data-testid="stChatMessage"]:hover {{
        border-color: {accent_color};
    }}

    /* Custom Tag Pills */
    .tag-pill {{
        display: inline-block;
        padding: 2px 10px;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 9999px;
        margin-right: 6px;
        margin-bottom: 4px;
        background: linear-gradient(135deg, rgba(56, 189, 248, 0.2), rgba(168, 85, 247, 0.2));
        color: {accent_color};
        border: 1px solid rgba(56, 189, 248, 0.3);
    }}

    /* Code Blocks */
    pre, code {{
        font-family: 'Fira Code', monospace !important;
        border-radius: 8px !important;
    }}

    /* Interactive Button Polish */
    .stButton > button {{
        border-radius: 8px !important;
        font-weight: 600 !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }}
    .stButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(56, 189, 248, 0.25);
    }}

    /* Memory Card Box */
    .memory-card {{
        background: {card_bg};
        border-left: 4px solid {accent_color};
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-right: 1px solid {border_color};
        border-top: 1px solid {border_color};
        border-bottom: 1px solid {border_color};
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
