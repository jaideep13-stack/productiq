import time
import numpy as np
from typing import List, Dict, Optional
from src.embedder import get_vector_store
from src.database import get_products_by_ids, log_search


def reciprocal_rank_fusion(ranked_lists: List[List[Dict]], k: int = 60) -> List[Dict]:
    """
    Reciprocal Rank Fusion — merge multiple ranked lists.
    Architecture doc formula: score(d) = Σ 1/(k + rank_i(d))
    k=60 is the standard parameter — robust, no calibration needed.
    """
    scores = {}
    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list):
            pid = item["product_id"]
            scores[pid] = scores.get(pid, 0) + 1 / (k + rank + 1)

    sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [{"product_id": pid, "rrf_score": score} for pid, score in sorted_items]


def hybrid_search(
    query: str,
    category_filter: Optional[str] = None,
    max_price: Optional[float] = None,
    min_price: Optional[float] = None,
    in_stock_only: bool = False,
    top_k: int = 20
) -> tuple[List[Dict], float]:
    """
    7-Step Hybrid Search (Architecture: Layer 4, Service 1):
    1. Accept query + filters
    2. Encode text with BGE (vector store handles this)
    3. Vector search → top candidates
    4. RRF merge (if multi-modal)
    5. Post-filter by metadata
    6. Return with scores and explanations
    7. Log latency

    Returns (results, latency_ms)
    """
    start = time.time()

    vs = get_vector_store()
    if not vs.is_ready():
        return [], 0.0

    # Text vector search — get more candidates for filtering
    raw_results = vs.search(query, top_k=top_k * 3)

    if not raw_results:
        return [], 0.0

    # Get product metadata for filtering
    pids = [r["product_id"] for r in raw_results]
    products = {p["id"]: p for p in get_products_by_ids(pids)}

    # Apply metadata filters (Architecture: payload filters inside vector store)
    filtered = []
    for r in raw_results:
        p = products.get(r["product_id"])
        if not p:
            continue
        if category_filter and category_filter != "all":
            if p.get("category", "") != category_filter:
                continue
        if max_price and p.get("price", 0) > max_price:
            continue
        if min_price and p.get("price", 0) < min_price:
            continue
        if in_stock_only and not p.get("in_stock", 1):
            continue
        filtered.append({**r, **p})

    # Apply RRF (single list here, but structured for multi-modal extension)
    rrf_results = reciprocal_rank_fusion([
        [{"product_id": r["product_id"]} for r in filtered]
    ])

    # Merge scores back
    score_map = {r["product_id"]: r["rrf_score"] for r in rrf_results}
    product_map = {r["product_id"]: r for r in filtered}

    final = []
    for item in rrf_results[:top_k]:
        pid = item["product_id"]
        p = product_map.get(pid, {})
        if p:
            final.append({
                **p,
                "relevance_score": round(item["rrf_score"] * 100, 2),
                "match_explanation": _explain_match(query, p)
            })

    latency = (time.time() - start) * 1000
    log_search(query, len(final), round(latency, 1))

    return final, round(latency, 1)


def _explain_match(query: str, product: dict) -> str:
    """Generate a simple explanation of why this product matched."""
    query_words = set(query.lower().split())
    title_words = set(product.get("title", "").lower().split())
    desc_words = set(product.get("description", "").lower().split())

    title_overlap = query_words & title_words
    desc_overlap = query_words & desc_words

    parts = []
    if title_overlap:
        parts.append(f"title match: {', '.join(list(title_overlap)[:3])}")
    if desc_overlap - title_overlap:
        parts.append(f"description match: {', '.join(list(desc_overlap - title_overlap)[:2])}")
    if product.get("category"):
        parts.append(f"category: {product['category']}")

    return " · ".join(parts) if parts else "semantic similarity"


def get_comparables(product_id: str, top_k: int = 50) -> List[Dict]:
    """
    Find comparable products for pricing analysis.
    Architecture: used by Pricing Tier Suggester (Service 3).
    """
    vs = get_vector_store()
    similar = vs.get_similar(product_id, top_k=top_k)
    if not similar:
        return []

    pids = [r["product_id"] for r in similar]
    products = get_products_by_ids(pids)
    score_map = {r["product_id"]: r["score"] for r in similar}

    return [
        {**p, "similarity": round(score_map.get(p["id"], 0), 4)}
        for p in products if p.get("price")
    ]
