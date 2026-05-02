import streamlit as st
import pandas as pd
import uuid
from src.ingestion import parse_csv, generate_sample_csv_bytes, ProductSchema
from src.database import insert_product, get_all_products, init_db
from src.embedder import get_vector_store


def ingest_screen():
    st.markdown("## ➕ Product Ingestion")
    st.caption("Layer 1 — Canonical schema validation + vector indexing")

    tab_csv, tab_manual, tab_index = st.tabs([
        "📄 CSV Upload", "✍️ Manual Entry", "🧠 Build Vector Index"
    ])

    with tab_csv:
        _csv_tab()

    with tab_manual:
        _manual_tab()

    with tab_index:
        _index_tab()


def _csv_tab():
    st.markdown("#### Upload Product CSV")
    st.caption("Required columns: `title`, `price` · Optional: description, category, seller_id, image_url")

    col1, col2 = st.columns([2, 1])
    with col2:
        sample_bytes = generate_sample_csv_bytes()
        st.download_button(
            "⬇️ Download Sample CSV",
            data=sample_bytes,
            file_name="sample_products.csv",
            mime="text/csv",
            use_container_width=True
        )

    uploaded = st.file_uploader("Upload CSV file", type=["csv"])

    if uploaded:
        df = pd.read_csv(uploaded)
        st.markdown(f"**Preview — {len(df)} rows:**")
        st.dataframe(df.head(5), use_container_width=True)

        if st.button("✅ Validate & Import", type="primary", use_container_width=True):
            with st.spinner("Validating schema..."):
                try:
                    valid, errors = parse_csv(df)
                except ValueError as e:
                    st.error(str(e))
                    return

            if errors:
                st.warning(f"⚠️ {len(errors)} rows had errors:")
                st.dataframe(pd.DataFrame(errors), use_container_width=True)

            if valid:
                with st.spinner(f"Importing {len(valid)} products..."):
                    for p in valid:
                        insert_product(p.to_db_dict())

                st.success(f"✅ Imported {len(valid)} products! Now go to **Build Vector Index** tab.")

                if errors:
                    st.info(f"{len(errors)} rows were skipped due to validation errors (shown above).")


def _manual_tab():
    st.markdown("#### Add Product Manually")

    with st.form("manual_product_form"):
        col1, col2 = st.columns(2)
        with col1:
            title = st.text_input("Product Title *", placeholder="Ergonomic Mesh Chair — Black")
            price = st.number_input("Price (₹) *", min_value=1.0, value=999.0, step=100.0)
            category = st.selectbox("Category", [
                "furniture", "electronics", "home_decor", "apparel",
                "kitchen", "sports", "beauty", "books", "uncategorized"
            ])
        with col2:
            seller_id = st.text_input("Seller ID", value="S_MANUAL", placeholder="S001")
            image_url = st.text_input("Image URL", placeholder="https://...")
            in_stock = st.checkbox("In Stock", value=True)

        description = st.text_area("Description", height=100,
                                   placeholder="Detailed product description. Include dimensions, material, features...")

        submitted = st.form_submit_button("➕ Add Product", type="primary", use_container_width=True)

    if submitted:
        if not title or price <= 0:
            st.error("Title and price are required.")
            return

        try:
            product = ProductSchema(
                title=title,
                description=description or None,
                price=price,
                category=category,
                seller_id=seller_id,
                image_url=image_url or None,
                source="manual",
                in_stock=int(in_stock)
            )
            insert_product(product.to_db_dict())
            st.success(f"✅ Product added — ID: `{product.id}`")
            st.info("Go to **Build Vector Index** tab to include it in search.")
        except Exception as e:
            st.error(f"Validation failed: {e}")


def _index_tab():
    st.markdown("#### 🧠 Build Vector Index")
    st.caption("Embeds all products using BGE-large and stores in FAISS index for semantic search.")

    products = get_all_products()
    vs = get_vector_store()

    col1, col2 = st.columns(2)
    col1.metric("Products in DB", len(products))
    col2.metric("Products in Index", vs.size())

    if len(products) == 0:
        st.warning("No products in database. Add some first.")
        return

    st.markdown("---")

    if vs.is_ready():
        st.success(f"✅ Index is ready with {vs.size()} products.")
        rebuild = st.button("🔄 Rebuild Index (full re-embed)", use_container_width=True)
    else:
        st.warning("Index not built yet.")
        rebuild = st.button("🚀 Build Index Now", type="primary", use_container_width=True)

    if rebuild:
        with st.spinner(f"Embedding {len(products)} products with BGE-large... (first time may take 2-5 min)"):
            count = vs.rebuild(products)

        if count > 0:
            st.success(f"✅ Index built! {count} products embedded and indexed.")
            st.balloons()
        else:
            st.error("❌ Embedding failed. Make sure sentence-transformers is installed.")
            st.code("pip install sentence-transformers faiss-cpu", language="bash")
