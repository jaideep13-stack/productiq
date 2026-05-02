import streamlit as st
import time
from src.search_engine import hybrid_search
from src.embedder import get_vector_store


DEMO_QUERIES = [
    "minimalist desk for home office",
    "wireless keyboard bluetooth",
    "noise cancelling headphones",
    "ergonomic chair lumbar support",
    "scandinavian wooden furniture",
    "monitor for coding",
]


def search_screen():
    st.markdown("## 🔍 Semantic Product Search")
    st.caption("Layer 4, Service 1 — BGE embeddings + Reciprocal Rank Fusion + metadata filtering")

    vs = get_vector_store()
    if not vs.is_ready():
        st.warning("⚠️ Vector index not built. Go to **Ingest → Build Vector Index** first.")
        return

    # Search input
    col_q, col_btn = st.columns([4, 1])
    with col_q:
        query = st.text_input(
            "Search",
            placeholder="e.g. minimalist desk for small apartment...",
            label_visibility="collapsed"
        )
    with col_btn:
        search_clicked = st.button("🔍 Search", type="primary", use_container_width=True)

    # Demo queries
    st.markdown("**Try:** " + " · ".join([
        f"`{q}`" for q in DEMO_QUERIES[:4]
    ]))

    # Filters
    with st.expander("🔧 Filters"):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            category = st.selectbox("Category", [
                "all", "furniture", "electronics", "home_decor",
                "apparel", "kitchen", "sports"
            ])
        with col2:
            max_price = st.number_input("Max Price (₹)", value=100000, min_value=0, step=1000)
        with col3:
            min_price = st.number_input("Min Price (₹)", value=0, min_value=0, step=100)
        with col4:
            in_stock = st.checkbox("In Stock Only", value=False)
        top_k = st.slider("Results to show", 5, 30, 10)

    if (search_clicked or query) and query.strip():
        with st.spinner("Searching..."):
            results, latency = hybrid_search(
                query,
                category_filter=category if category != "all" else None,
                max_price=max_price if max_price < 100000 else None,
                min_price=min_price if min_price > 0 else None,
                in_stock_only=in_stock,
                top_k=top_k
            )

        if not results:
            st.info("No results found. Try a different query or adjust filters.")
            return

        st.markdown(f"**{len(results)} results** in `{latency:.0f}ms`")
        st.markdown("---")

        # Results grid
        for i in range(0, len(results), 3):
            cols = st.columns(3)
            for j, col in enumerate(cols):
                if i + j >= len(results):
                    break
                product = results[i + j]
                with col:
                    _render_product_card(product, rank=i + j + 1)


def _render_product_card(product: dict, rank: int):
    score = product.get("relevance_score", 0)
    price = product.get("price", 0)
    category = product.get("category", "").replace("_", " ").title()
    explanation = product.get("match_explanation", "")

    # Image
    img_url = product.get("image_url", "")
    if img_url and img_url.startswith("http"):
        st.image(img_url, use_column_width=True)

    st.markdown(f"""
    <div style='padding:8px 0;'>
        <div style='font-weight:700;font-size:0.9rem;color:#0f172a;line-height:1.3;margin-bottom:4px;'>
            #{rank} {product.get('title', '')[:55]}{'...' if len(product.get('title','')) > 55 else ''}
        </div>
        <div style='color:#6366f1;font-weight:700;font-size:1rem;margin-bottom:4px;'>₹{price:,.0f}</div>
        <div style='display:flex;gap:6px;flex-wrap:wrap;margin-bottom:6px;'>
            <span style='background:#f1f5f9;color:#475569;font-size:0.72rem;padding:2px 8px;border-radius:100px;'>{category}</span>
            <span style='background:#eef2ff;color:#4338ca;font-size:0.72rem;padding:2px 8px;border-radius:100px;'>Score: {score:.0f}</span>
        </div>
        <div style='color:#94a3b8;font-size:0.75rem;font-style:italic;'>{explanation[:60]}</div>
    </div>
    """, unsafe_allow_html=True)

    desc = product.get("description", "")
    if desc:
        with st.expander("Details"):
            st.caption(desc[:300])
            st.caption(f"ID: `{product.get('id')}` · Seller: {product.get('seller_id', 'N/A')}")
