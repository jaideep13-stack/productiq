import numpy as np
from typing import List, Dict, Optional
from src.search_engine import get_comparables
from src.database import get_product, save_pricing


def analyze_pricing(product_id: str) -> Dict:
    """
    Comparable-based pricing analysis.
    Architecture: Service 3 — statistics first, LLM only explains.

    Steps:
    A. Find top-50 similar products (comparables)
    B. Compute price distribution (median, p25, p75)
    C. Suggest pricing tier based on position
    """
    product = get_product(product_id)
    if not product:
        return {}

    # Step A: Find comparables
    comparables = get_comparables(product_id, top_k=50)

    if len(comparables) < 3:
        return {
            "error": "Not enough comparable products in catalog. Add more products first.",
            "product": product,
            "comparable_count": len(comparables)
        }

    # Filter to same category if possible
    same_cat = [c for c in comparables if c.get("category") == product.get("category")]
    use_comps = same_cat if len(same_cat) >= 3 else comparables

    prices = [c["price"] for c in use_comps if c.get("price", 0) > 0]

    if not prices:
        return {"error": "No valid prices in comparables."}

    # Step B: Statistical distribution
    prices_arr = np.array(prices)
    median_price = float(np.median(prices_arr))
    p25 = float(np.percentile(prices_arr, 25))
    p75 = float(np.percentile(prices_arr, 75))
    mean_price = float(np.mean(prices_arr))
    std_price = float(np.std(prices_arr))

    current_price = product.get("price", 0)
    price_diff_pct = ((current_price - median_price) / median_price * 100) if median_price > 0 else 0

    # Step C: Positioning
    if current_price < p25:
        position = "budget"
        suggestion = f"Your price ₹{current_price:,.0f} is below the budget floor (₹{p25:,.0f}). You may be underpricing."
    elif current_price <= median_price:
        position = "mid_budget"
        suggestion = f"Your price ₹{current_price:,.0f} is competitive — between budget (₹{p25:,.0f}) and median (₹{median_price:,.0f})."
    elif current_price <= p75:
        position = "mid_premium"
        suggestion = f"Your price ₹{current_price:,.0f} is in the premium range (median ₹{median_price:,.0f} – p75 ₹{p75:,.0f})."
    else:
        position = "premium"
        suggestion = f"Your price ₹{current_price:,.0f} is above the premium ceiling (₹{p75:,.0f}). Ensure differentiation is clear."

    result = {
        "product": product,
        "current_price": current_price,
        "comparable_count": len(use_comps),
        "median_price": round(median_price, 2),
        "p25_price": round(p25, 2),
        "p75_price": round(p75, 2),
        "mean_price": round(mean_price, 2),
        "std_price": round(std_price, 2),
        "price_diff_pct": round(price_diff_pct, 1),
        "position": position,
        "suggestion": suggestion,
        "suggested_min": round(p25, 2),
        "suggested_max": round(p75, 2),
        "top_comparables": use_comps[:8],
        "comparable_ids": [c["id"] for c in use_comps[:20]],
    }

    # Save to DB
    save_pricing(product_id, result)

    return result


def get_pricing_tier_label(price: float, p25: float, p75: float) -> str:
    if price < p25:
        return "🟢 Budget"
    elif price <= p75:
        return "🟡 Mid-Range"
    else:
        return "🔴 Premium"
