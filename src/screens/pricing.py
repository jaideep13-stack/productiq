import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from src.pricing_engine import analyze_pricing, get_pricing_tier_label
from src.database import get_all_products


def pricing_screen():
    st.markdown("## 💰 Pricing Intelligence")
    st.caption("Layer 4, Service 3 — Comparable-based statistical pricing. Statistics first, LLM only explains.")

    products = get_all_products()
    if not products:
        st.info("No products found.")
        return

    options = {f"{p['title'][:50]} (₹{p['price']:,.0f})": p for p in products}
    selected_label = st.selectbox("Select Product to Analyze", list(options.keys()))
    selected = options[selected_label]

    st.markdown("---")

    if st.button("📊 Analyze Pricing", type="primary", use_container_width=True):
        with st.spinner("Finding comparables and computing price distribution..."):
            result = analyze_pricing(selected["id"])

        if "error" in result:
            st.error(result["error"])
            return

        _display_pricing_result(result)


def _display_pricing_result(result: dict):
    product = result["product"]
    current_price = result["current_price"]
    median = result["median_price"]
    p25 = result["p25_price"]
    p75 = result["p75_price"]
    comp_count = result["comparable_count"]
    suggestion = result["suggestion"]
    position = result["position"]

    # Position badge
    pos_colors = {
        "budget": ("#f0fdf4", "#16a34a", "🟢 Budget"),
        "mid_budget": ("#fefce8", "#ca8a04", "🟡 Mid-Budget"),
        "mid_premium": ("#fff7ed", "#ea580c", "🟠 Mid-Premium"),
        "premium": ("#fef2f2", "#dc2626", "🔴 Premium"),
    }
    bg, fg, label = pos_colors.get(position, ("#f1f5f9", "#475569", "⚪ Unknown"))

    st.markdown(
        f"<div style='background:{bg};color:{fg};padding:10px 18px;border-radius:8px;"
        f"font-weight:700;font-size:1rem;display:inline-block;margin-bottom:12px;'>"
        f"{label} Positioning</div>",
        unsafe_allow_html=True
    )

    # Key metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Your Price", f"₹{current_price:,.0f}")
    c2.metric("Market Median", f"₹{median:,.0f}",
              delta=f"{result['price_diff_pct']:+.1f}%")
    c3.metric("Budget Floor (p25)", f"₹{p25:,.0f}")
    c4.metric("Premium Ceiling (p75)", f"₹{p75:,.0f}")
    c5.metric("Comparables Used", comp_count)

    # Gauge chart
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=current_price,
        delta={"reference": median, "valueformat": ",.0f"},
        title={"text": "Your Price vs Market"},
        gauge={
            "axis": {"range": [0, max(p75 * 1.5, current_price * 1.2)]},
            "bar": {"color": fg},
            "steps": [
                {"range": [0, p25], "color": "#f0fdf4"},
                {"range": [p25, median], "color": "#fefce8"},
                {"range": [median, p75], "color": "#fff7ed"},
                {"range": [p75, max(p75 * 1.5, current_price * 1.2)], "color": "#fef2f2"},
            ],
            "threshold": {
                "line": {"color": "#6366f1", "width": 3},
                "thickness": 0.75,
                "value": median
            }
        }
    ))
    fig.update_layout(height=280, margin=dict(t=30, b=0, l=20, r=20))
    st.plotly_chart(fig, use_container_width=True)

    # AI Suggestion
    st.markdown(f"""
    <div style='background:#f0f9ff;border-left:4px solid #0284c7;border-radius:8px;
                padding:14px 18px;margin-bottom:16px;'>
        <div style='font-size:0.72rem;font-weight:800;color:#0284c7;text-transform:uppercase;
                    letter-spacing:0.08em;margin-bottom:6px;'>Pricing Recommendation</div>
        <p style='margin:0;color:#0f172a;'>{suggestion}</p>
        <p style='margin:6px 0 0 0;color:#475569;font-size:0.88rem;'>
            Suggested range: <b>₹{result['suggested_min']:,.0f}</b> – <b>₹{result['suggested_max']:,.0f}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Comparables table
    if result.get("top_comparables"):
        st.markdown("#### 📋 Top Comparable Products")
        df = pd.DataFrame(result["top_comparables"])
        display_cols = ["title", "price", "category", "similarity"]
        df_display = df[[c for c in display_cols if c in df.columns]].copy()
        if "title" in df_display.columns:
            df_display["title"] = df_display["title"].str[:50]
        if "price" in df_display.columns:
            df_display["price"] = df_display["price"].apply(lambda x: f"₹{x:,.0f}")
        if "similarity" in df_display.columns:
            df_display["similarity"] = df_display["similarity"].apply(lambda x: f"{x:.3f}")
        st.dataframe(df_display, use_container_width=True, hide_index=True)
