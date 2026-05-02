import streamlit as st
from src.database import init_db
from src.screens.home import home_screen
from src.screens.ingest import ingest_screen
from src.screens.search import search_screen
from src.screens.dedup import dedup_screen
from src.screens.pricing import pricing_screen
from src.screens.enrichment import enrichment_screen

st.set_page_config(
    page_title="ProductIQ — Multi-Modal Intelligence",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    #MainMenu {visibility:hidden;}
    footer {visibility:hidden;}
    .block-container {padding-top:1.5rem;}
    .stTabs [data-baseweb="tab"] {
        background:#f1f5f9; border-radius:8px;
        padding:6px 16px; font-weight:500;
    }
    .stTabs [aria-selected="true"] {
        background:#0f172a !important; color:white !important;
    }
    div[data-testid="metric-container"] {
        background:#f8fafc; border:1px solid #e2e8f0;
        border-radius:10px; padding:12px 16px;
    }
</style>
""", unsafe_allow_html=True)

# Init DB on first run
init_db()

# Sidebar nav
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:1rem 0;'>
        <h2 style='color:#0f172a;margin:0;font-size:1.3rem;'>🏗️ ProductIQ</h2>
        <p style='color:#64748b;font-size:0.75rem;margin:4px 0 0 0;'>
            Multi-Modal Product Intelligence
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")

    page = st.radio(
        "Navigation",
        [
            "🏠 Home",
            "➕ Ingest Products",
            "🔍 Semantic Search",
            "🔁 Duplicate Detection",
            "💰 Pricing Intelligence",
            "✨ AI Enrichment",
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.75rem;color:#94a3b8;'>
        <b>Stack:</b><br>
        BGE-large · FAISS · RRF<br>
        Llama 3.1 · Pydantic · SQLite<br>
        Streamlit · Plotly
    </div>
    """, unsafe_allow_html=True)

# Route
if page == "🏠 Home":
    home_screen()
elif page == "➕ Ingest Products":
    ingest_screen()
elif page == "🔍 Semantic Search":
    search_screen()
elif page == "🔁 Duplicate Detection":
    dedup_screen()
elif page == "💰 Pricing Intelligence":
    pricing_screen()
elif page == "✨ AI Enrichment":
    enrichment_screen()
