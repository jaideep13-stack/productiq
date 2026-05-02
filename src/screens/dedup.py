import streamlit as st
import pandas as pd
from src.dedup_engine import run_dedup_scan, enrich_duplicate_pairs
from src.database import get_all_duplicates, get_all_products
from src.embedder import get_vector_store


def dedup_screen():
    st.markdown("## 🔁 Duplicate Detection")
    st.caption("Layer 4, Service 2 — Vector similarity with 3-tier thresholds: Exact (>0.95) · Near (0.88-0.95) · Variant (0.82-0.88)")

    vs = get_vector_store()
    if not vs.is_ready():
        st.warning("⚠️ Build the vector index first (Ingest → Build Vector Index).")
        return

    # Thresholds explanation
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div style='background:#fef2f2;border:1px solid #fecaca;border-radius:8px;padding:12px;text-align:center;'>
            <b style='color:#dc2626;'>🔴 Exact Duplicate</b>
            <div style='font-size:0.8rem;color:#475569;margin-top:4px;'>Similarity > 0.95<br>Auto-merge candidate</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div style='background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;padding:12px;text-align:center;'>
            <b style='color:#ea580c;'>🟠 Near Duplicate</b>
            <div style='font-size:0.8rem;color:#475569;margin-top:4px;'>0.88 – 0.95<br>Flag for review</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div style='background:#fefce8;border:1px solid #fef08a;border-radius:8px;padding:12px;text-align:center;'>
            <b style='color:#ca8a04;'>🟡 Variant</b>
            <div style='font-size:0.8rem;color:#475569;margin-top:4px;'>0.82 – 0.88<br>Group as variants</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    if st.button("🔍 Run Dedup Scan", type="primary", use_container_width=True):
        products = get_all_products()
        with st.spinner(f"Scanning {len(products)} products for duplicates..."):
            pairs = run_dedup_scan(max_products=len(products))

        if pairs:
            enriched = enrich_duplicate_pairs(pairs)
            st.session_state["dedup_results"] = enriched
            st.success(f"✅ Found {len(pairs)} duplicate pairs!")
        else:
            st.info("No duplicates found. Catalog looks clean!")
            st.session_state["dedup_results"] = []

    # Show results
    results = st.session_state.get("dedup_results")
    if results is None:
        # Load from DB
        raw = get_all_duplicates()
        if raw:
            results = enrich_duplicate_pairs(raw)

    if results:
        # Filter
        filter_type = st.selectbox("Filter by type", ["all", "exact", "near_duplicate", "variant"])
        if filter_type != "all":
            filtered = [r for r in results if r["cluster_type"] == filter_type]
        else:
            filtered = results

        st.markdown(f"**{len(filtered)} pairs** ({filter_type})")

        for pair in filtered[:20]:
            cluster = pair["cluster_type"]
            score = pair["similarity_score"]
            badge_color = {"exact": "#dc2626", "near_duplicate": "#ea580c", "variant": "#ca8a04"}.get(cluster, "#475569")
            badge_label = {"exact": "🔴 EXACT", "near_duplicate": "🟠 NEAR DUP", "variant": "🟡 VARIANT"}.get(cluster, "⚪")

            with st.expander(
                f"{badge_label} — {pair['title_a'][:40]}... vs {pair['title_b'][:40]}... (sim: {score:.3f})"
            ):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Product A:**\n{pair['title_a']}")
                    st.markdown(f"Price: ₹{pair['price_a']:,.0f}")
                    st.markdown(f"Category: {pair['category_a']}")
                    st.caption(f"ID: `{pair['product_id_a']}`")
                with col2:
                    st.markdown(f"**Product B:**\n{pair['title_b']}")
                    st.markdown(f"Price: ₹{pair['price_b']:,.0f}")
                    st.markdown(f"Category: {pair['category_b']}")
                    st.caption(f"ID: `{pair['product_id_b']}`")

                st.progress(min(score, 1.0), text=f"Similarity: {score:.3f}")

                action = st.radio(
                    "Action",
                    ["No action", "Mark as reviewed", "Flag as duplicate"],
                    horizontal=True,
                    key=f"action_{pair['product_id_a']}_{pair['product_id_b']}"
                )
