from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

BASE_DIR = Path(__file__).resolve().parent
HTML_PATH = BASE_DIR / "index.html"

st.set_page_config(
    page_title="FinSight AI",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Keep Streamlit chrome from competing with the FinSight workspace UI.
st.markdown(
    """
    <style>
      .stApp { background: #0b1220; }
      .block-container { padding: 0 !important; max-width: 100% !important; }
      header[data-testid="stHeader"] { background: transparent; }
      footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

if not HTML_PATH.exists():
    st.error("FinSight UI 파일(index.html)을 찾을 수 없습니다.")
    st.stop()

html = HTML_PATH.read_text(encoding="utf-8")

# The existing V2.5 app remains a browser-side workspace inside the Streamlit page.
# File parsing/editing stays in the browser iframe; Streamlit is the deployment shell.
components.html(html, height=2200, scrolling=True)
