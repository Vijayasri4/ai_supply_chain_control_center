"""
App-wide configuration. Centralizes how the Groq API key and model
name are resolved, in priority order:

1. Value entered by the user in the Streamlit sidebar (session_state)
2. Streamlit secrets (.streamlit/secrets.toml) - used when deployed
3. Environment variable / .env file - used for local development
"""

import os

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-120b"


def get_api_key() -> str:
    if st.session_state.get("api_key"):
        return st.session_state["api_key"]

    try:
        if "GROQ_API_KEY" in st.secrets:
            return st.secrets["GROQ_API_KEY"]
    except Exception:
        pass  # no secrets.toml present locally - that's fine

    return os.environ.get("GROQ_API_KEY", "")


def get_model() -> str:
    return st.session_state.get("model") or os.environ.get(
        "GROQ_MODEL", DEFAULT_MODEL
    )