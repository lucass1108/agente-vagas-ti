import os
import pytest

os.environ.setdefault("ADMIN_KEY", "")
os.environ.setdefault("GEMINI_API_KEY", "")

try:
    import streamlit_app
    HAS_STREAMLIT = True
except Exception:
    HAS_STREAMLIT = False


@pytest.mark.skipif(not HAS_STREAMLIT, reason="streamlit_app nao importavel em modo bare")
def test_fallback_predefinido():
    resp = streamlit_app.chatbot_response("oi")
    assert "bbzinho" in resp.lower() or "ola" in resp.lower() or "olá" in resp.lower()


@pytest.mark.skipif(not HAS_STREAMLIT, reason="streamlit_app nao importavel em modo bare")
def test_fallback_ajuda():
    resp = streamlit_app.chatbot_response("/ajuda")
    assert "comandos" in resp.lower() or "ajuda" in resp.lower()