import streamlit as st
import json
from typing import Dict, List
from src.database import save_enrichment

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

# Closed vocabulary taxonomy (Architecture doc: prevents "scandinavian" vs "nordic" drift)
CATEGORY_TAXONOMY = [
    "furniture", "electronics", "home_decor", "apparel", "books",
    "kitchen", "sports", "beauty", "toys", "automotive", "uncategorized"
]

STYLE_TAXONOMY = [
    "minimalist", "scandinavian", "industrial", "bohemian", "modern",
    "traditional", "rustic", "luxury", "ergonomic", "compact", "vintage"
]

USE_CASE_TAXONOMY = [
    "home_office", "travel", "gaming", "study", "bedroom", "living_room",
    "outdoor", "professional", "everyday", "gifting", "eco_friendly"
]


def get_groq_client():
    try:
        api_key = st.secrets.get("GROQ_API_KEY", "")
        if not api_key:
            import os
            api_key = os.getenv("GROQ_API_KEY", "")
        return Groq(api_key=api_key) if api_key else None
    except Exception:
        return None


def enrich_product(product: dict) -> Dict:
    """
    LLM-based product enrichment.
    Architecture: constrained generation from closed vocabulary.
    LLM picks from taxonomy — no hallucination of tag names.
    """
    client = get_groq_client()

    if not client or not GROQ_AVAILABLE:
        result = _rule_based_enrichment(product)
        save_enrichment(product["id"], result)
        return result

    prompt = f"""You are a product catalog expert. Analyze this product and return ONLY a JSON object.

Product Title: {product.get('title', '')}
Description: {product.get('description', '')}
Price: ₹{product.get('price', 0)}
Current Category: {product.get('category', '')}

Return ONLY this JSON (no markdown, no explanation):
{{
  "primary_category": "<one of: {', '.join(CATEGORY_TAXONOMY)}>",
  "subcategory": "<specific subcategory, 2-3 words>",
  "style_tags": ["<from: {', '.join(STYLE_TAXONOMY)}>", "<max 3 tags>"],
  "use_case_tags": ["<from: {', '.join(USE_CASE_TAXONOMY)}>", "<max 3 tags>"],
  "pricing_tier": "<one of: budget, mid_range, premium, luxury>",
  "seo_title": "<optimized title, max 60 chars>",
  "seo_description": "<meta description, max 160 chars>",
  "quality_score": <integer 1-10, based on description completeness>,
  "missing_fields": ["<list fields that would improve this listing, e.g. dimensions, material, warranty>"]
}}"""

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": "Return only valid JSON. No markdown. No explanation."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.1
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        # Enforce taxonomy constraints
        result["primary_category"] = _enforce_vocab(
            result.get("primary_category", "uncategorized"), CATEGORY_TAXONOMY
        )
        result["style_tags"] = [
            t for t in result.get("style_tags", []) if t in STYLE_TAXONOMY
        ][:3]
        result["use_case_tags"] = [
            t for t in result.get("use_case_tags", []) if t in USE_CASE_TAXONOMY
        ][:3]

        save_enrichment(product["id"], result)
        return result

    except Exception as e:
        result = _rule_based_enrichment(product)
        result["llm_error"] = str(e)[:100]
        save_enrichment(product["id"], result)
        return result


def enrich_batch(products: List[dict]) -> List[Dict]:
    """
    Batch enrichment. Architecture: group 50 products per LLM call.
    For demo, we enrich individually.
    """
    return [enrich_product(p) for p in products]


def _rule_based_enrichment(product: dict) -> Dict:
    """Fallback rule-based enrichment when LLM unavailable."""
    title_lower = (product.get("title", "") + " " + product.get("description", "")).lower()
    price = product.get("price", 0)

    # Category detection
    cat_keywords = {
        "furniture": ["desk", "chair", "table", "shelf", "cabinet", "sofa", "bed"],
        "electronics": ["laptop", "phone", "keyboard", "monitor", "headphone", "mouse", "usb"],
        "home_decor": ["lamp", "rug", "pot", "vase", "plant", "candle", "organizer"],
        "apparel": ["shirt", "dress", "shoes", "jacket", "pants", "bag"],
    }
    detected_cat = product.get("category", "uncategorized")
    for cat, keywords in cat_keywords.items():
        if any(k in title_lower for k in keywords):
            detected_cat = cat
            break

    # Style detection
    style_keywords = {
        "minimalist": ["minimalist", "minimal", "simple", "clean"],
        "scandinavian": ["scandinavian", "nordic", "oak", "birch"],
        "ergonomic": ["ergonomic", "lumbar", "adjustable", "posture"],
        "industrial": ["industrial", "metal", "steel", "iron"],
    }
    detected_styles = [s for s, kws in style_keywords.items() if any(k in title_lower for k in kws)]

    # Pricing tier
    if price < 1000:
        tier = "budget"
    elif price < 5000:
        tier = "mid_range"
    elif price < 20000:
        tier = "premium"
    else:
        tier = "luxury"

    # Quality score based on completeness
    quality = 5
    if product.get("description") and len(product["description"]) > 100:
        quality += 2
    if product.get("image_url"):
        quality += 1
    if product.get("category"):
        quality += 1

    return {
        "primary_category": detected_cat,
        "subcategory": detected_cat.replace("_", " ").title(),
        "style_tags": detected_styles[:3],
        "use_case_tags": ["everyday"],
        "pricing_tier": tier,
        "seo_title": product.get("title", "")[:60],
        "seo_description": (product.get("description", "")[:157] + "...") if product.get("description") else "",
        "quality_score": quality,
        "missing_fields": _detect_missing(product),
        "source": "rule_based"
    }


def _enforce_vocab(value: str, vocab: List[str]) -> str:
    if value in vocab:
        return value
    # Try partial match
    for v in vocab:
        if v in value.lower() or value.lower() in v:
            return v
    return vocab[-1]  # fallback to last (uncategorized)


def _detect_missing(product: dict) -> List[str]:
    missing = []
    desc = product.get("description", "")
    if not product.get("image_url"):
        missing.append("product_image")
    if not desc or len(desc) < 50:
        missing.append("detailed_description")
    if "dimension" not in desc.lower() and "cm" not in desc.lower() and "inch" not in desc.lower():
        missing.append("dimensions")
    if "material" not in desc.lower() and "fabric" not in desc.lower():
        missing.append("material_info")
    if "warranty" not in desc.lower():
        missing.append("warranty_info")
    return missing
