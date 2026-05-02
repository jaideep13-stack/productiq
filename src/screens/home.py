import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from src.database import get_stats, get_all_products
from src.embedder import get_vector_store


def home_screen():
    st.markdown("""
    <div style='background:linear-gradient(135deg,#0f172a 0%,#1e293b 50%,#1a1a3e 100%);
                border-radius:16px;padding:2rem 2.5rem;margin-bottom:1.5rem;'>
        <h1 style='color:white;margin:0;font-size:2rem;'>🏗️ ProductIQ</h1>
        <p style='color:#94a3b8;margin:8px 0 0 0;font-size:1rem;'>
            Multi-Modal Product Intelligence Engine · Semantic Search · Dedup · Auto-Pricing · AI Tagging
        </p>
    </div>
    """, unsafe_allow_html=True)

    stats = get_stats()
    vs = get_vector_store()

    # Stats row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📦 Total Products", stats["total_products"])
    c2.metric("🧠 Vector Indexed", vs.size())
    c3.metric("✨ AI Enriched", stats["enriched"])
    c4.metric("🔁 Duplicates Found", stats["duplicates_found"])
    c5.metric("🔍 Total Searches", stats["total_searches"])

    # Index status
    if not vs.is_ready():
        st.warning("⚠️ Vector index not built yet. Go to **Catalog** tab → click **Build Vector Index**.")
    else:
        st.success(f"✅ Vector index ready — {vs.size()} products indexed for semantic search.")

    st.markdown("---")

    col_left, col_right = st.columns([1.5, 1])

    with col_left:
        st.markdown("#### 🏗️ System Architecture")
        layers = [
            ("1", "#eff6ff", "#1e40af", "Ingestion & Normalization",
             "Pydantic schema validation → Canonical product format",
             "Pydantic · CSV · Manual API"),
            ("2", "#eef2ff", "#3730a3", "Embedding & Enrichment",
             "BGE-large text embeddings + LLM structured metadata generation",
             "sentence-transformers · Groq · Llama 3.1"),
            ("3", "#f5f3ff", "#5b21b6", "Vector Storage",
             "FAISS flat index for cosine similarity search across all products",
             "FAISS · SQLite"),
            ("4", "#f0fdfa", "#134e4a", "Intelligence Services",
             "Hybrid search (RRF) · Dedup detection · Pricing tier · Auto-tagging",
             "RRF · pHash · Statistical pricing"),
            ("5", "#fff7ed", "#9a3412", "Frontend & Analytics",
             "Streamlit dashboard with search, dedup, pricing, enrichment screens",
             "Streamlit · Plotly"),
        ]

        for num, bg, fg, name, desc, tech in layers:
            st.markdown(f"""
            <div style='background:{bg};border-left:4px solid {fg};border-radius:8px;
                        padding:12px 16px;margin-bottom:10px;'>
                <div style='display:flex;align-items:center;gap:10px;'>
                    <span style='background:{fg};color:white;border-radius:50%;
                                 width:26px;height:26px;display:inline-flex;
                                 align-items:center;justify-content:center;
                                 font-weight:800;font-size:0.8rem;flex-shrink:0;'>{num}</span>
                    <div>
                        <b style='color:#0f172a;'>{name}</b>
                        <div style='color:#475569;font-size:0.82rem;'>{desc}</div>
                        <div style='color:#94a3b8;font-size:0.75rem;margin-top:2px;'>{tech}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col_right:
        st.markdown("#### 📊 Catalog Breakdown")
        products = get_all_products(limit=200)

        if products:
            df = pd.DataFrame(products)

            # Category distribution
            if "category" in df.columns:
                cat_counts = df["category"].value_counts().reset_index()
                cat_counts.columns = ["Category", "Count"]
                fig = px.pie(cat_counts, values="Count", names="Category",
                             hole=0.5, title="By Category")
                fig.update_layout(height=260, margin=dict(t=30, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)

            # Price distribution
            if "price" in df.columns:
                fig2 = px.histogram(df, x="price", nbins=15,
                                    title="Price Distribution",
                                    color_discrete_sequence=["#6366f1"])
                fig2.update_layout(height=200, margin=dict(t=30, b=0, l=0, r=0),
                                   showlegend=False)
                fig2.update_xaxes(title="Price (₹)")
                st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No products yet. Go to **Ingest** to add products.")

    st.markdown("---")
    st.markdown("#### 🚀 Quick Actions")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        #st.page_link("app.py", label="➕ Add Products", disabled=True)
        if st.button("➕ Ingest Products", use_container_width=True):
            st.session_state["page"] = "ingest"
    with c2:
        if st.button("🔍 Search Catalog", use_container_width=True, type="primary"):
            st.session_state["page"] = "search"
    with c3:
        if st.button("🔁 Run Dedup Scan", use_container_width=True):
            st.session_state["page"] = "dedup"
    with c4:
        if st.button("✨ AI Enrich Products", use_container_width=True):
            st.session_state["page"] = "enrich"
