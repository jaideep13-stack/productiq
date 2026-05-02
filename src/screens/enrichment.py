import streamlit as st
import pandas as pd
from src.llm_enricher import enrich_product
from src.database import get_all_products, get_enrichment


def enrichment_screen():
    st.markdown("## ✨ AI Product Enrichment")
    st.caption("Layer 2 + Layer 4, Service 4 — LLM auto-tagging with closed-vocabulary taxonomy enforcement")

    st.info("💡 LLM picks from a fixed taxonomy (categories, style tags, use-case tags). No hallucination — constrained generation only.", icon="🧠")

    tab_single, tab_batch, tab_view = st.tabs([
        "🔍 Enrich Single", "⚡ Batch Enrich", "📋 View Enriched"
    ])

    with tab_single:
        _single_enrich()

    with tab_batch:
        _batch_enrich()

    with tab_view:
        _view_enriched()


def _single_enrich():
    products = get_all_products()
    if not products:
        st.info("No products. Add some first.")
        return

    options = {f"{p['title'][:55]} (₹{p['price']:,.0f})": p for p in products}
    selected_label = st.selectbox("Select Product", list(options.keys()))
    selected = options[selected_label]

    # Show existing enrichment
    existing = get_enrichment(selected["id"])
    if existing:
        st.success("Already enriched. Showing existing data:")
        _display_enrichment(existing)
        if not st.button("🔄 Re-enrich with AI"):
            return

    if st.button("✨ Enrich with AI", type="primary"):
        with st.spinner("Running LLM enrichment (Llama 3.1)..."):
            result = enrich_product(selected)
        st.success("✅ Enrichment complete!")
        _display_enrichment(result)


def _display_enrichment(enrichment: dict):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Primary Category:** `{enrichment.get('primary_category', 'N/A')}`")
        st.markdown(f"**Subcategory:** {enrichment.get('subcategory', 'N/A')}")
        st.markdown(f"**Pricing Tier:** `{enrichment.get('pricing_tier', 'N/A')}`")
        quality = enrichment.get("quality_score", 0)
        st.markdown(f"**Quality Score:** {quality}/10")
        st.progress(min(quality / 10, 1.0))

    with col2:
        style_tags = enrichment.get("style_tags", [])
        use_tags = enrichment.get("use_case_tags", [])
        missing = enrichment.get("missing_fields", [])

        if style_tags:
            st.markdown("**Style Tags:** " + " ".join([f"`{t}`" for t in style_tags]))
        if use_tags:
            st.markdown("**Use Case:** " + " ".join([f"`{t}`" for t in use_tags]))
        if missing:
            st.markdown("**Missing Fields:** " + " ".join([f"`{m}`" for m in missing]))

    st.markdown("**SEO Title:**")
    st.code(enrichment.get("seo_title", ""), language=None)
    st.markdown("**SEO Description:**")
    st.code(enrichment.get("seo_description", ""), language=None)


def _batch_enrich():
    st.markdown("#### Batch Enrich Products")
    st.caption("Architecture: group products → LLM enrichment → closed taxonomy enforcement")

    products = get_all_products()
    unenriched = [p for p in products if not p.get("enriched")]

    st.metric("Products to enrich", len(unenriched))
    st.metric("Already enriched", len(products) - len(unenriched))

    if not unenriched:
        st.success("All products are enriched!")
        return

    limit = st.slider("How many to enrich now?", 1, min(len(unenriched), 20), 5)

    if st.button(f"✨ Enrich {limit} Products", type="primary"):
        progress = st.progress(0)
        status = st.empty()

        for i, product in enumerate(unenriched[:limit]):
            status.text(f"Enriching {i+1}/{limit}: {product['title'][:40]}...")
            enrich_product(product)
            progress.progress((i + 1) / limit)

        progress.empty()
        status.empty()
        st.success(f"✅ Enriched {limit} products!")
        st.rerun()


def _view_enriched():
    products = get_all_products()
    enriched_products = [p for p in products if p.get("enriched")]

    if not enriched_products:
        st.info("No enriched products yet.")
        return

    st.markdown(f"**{len(enriched_products)} enriched products:**")

    rows = []
    for p in enriched_products:
        enr = get_enrichment(p["id"])
        if enr:
            rows.append({
                "Title": p["title"][:45],
                "Category": enr.get("primary_category", ""),
                "Tier": enr.get("pricing_tier", ""),
                "Style Tags": ", ".join(enr.get("style_tags", [])),
                "Quality": f"{enr.get('quality_score', 0)}/10",
                "SEO Title": enr.get("seo_title", "")[:40],
            })

    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
