import numpy as np
from typing import List, Dict, Tuple
from src.embedder import get_vector_store
from src.database import get_all_products, get_products_by_ids, save_duplicate_pair
from src.image_utils import phash_distance


# Architecture thresholds from the doc:
# > 0.95 = exact duplicate → auto-merge candidate
# 0.88–0.95 = near duplicate → flag for review
# 0.82–0.88 = variant → group as variants

EXACT_THRESHOLD = 0.95
NEAR_THRESHOLD = 0.88
VARIANT_THRESHOLD = 0.82


def classify_duplicate(score: float) -> str:
    if score >= EXACT_THRESHOLD:
        return "exact"
    elif score >= NEAR_THRESHOLD:
        return "near_duplicate"
    elif score >= VARIANT_THRESHOLD:
        return "variant"
    return "different"


def run_dedup_scan(max_products: int = 100) -> List[Dict]:
    """
    Scan all products for duplicates using vector similarity.
    Architecture: pHash pre-filter → vector similarity.

    Returns list of duplicate pairs with classification.
    """
    products = get_all_products(limit=max_products)
    if len(products) < 2:
        return []

    vs = get_vector_store()
    if not vs.is_ready():
        return []

    found_pairs = []
    seen_pairs = set()

    for product in products:
        pid = product["id"]

        # Get top similar products
        similar = vs.get_similar(pid, top_k=10)

        for sim in similar:
            other_pid = sim["product_id"]
            pair_key = tuple(sorted([pid, other_pid]))

            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            score = sim["score"]
            cluster_type = classify_duplicate(score)

            if cluster_type == "different":
                continue

            # pHash pre-filter (Architecture doc: catches exact pixel duplicates fast)
            phash_check = _phash_precheck(product, other_pid, products)

            found_pairs.append({
                "product_id_a": pid,
                "product_id_b": other_pid,
                "similarity_score": round(score, 4),
                "cluster_type": cluster_type,
                "phash_match": phash_check
            })

            # Save to DB
            save_duplicate_pair(pid, other_pid, score, cluster_type)

    # Sort by similarity
    found_pairs.sort(key=lambda x: x["similarity_score"], reverse=True)
    return found_pairs


def _phash_precheck(product_a: dict, product_b_id: str, all_products: list) -> bool:
    """Check if two products have similar image hashes."""
    product_b = next((p for p in all_products if p["id"] == product_b_id), None)
    if not product_b:
        return False

    hash_a = product_a.get("phash")
    hash_b = product_b.get("phash")

    if not hash_a or not hash_b:
        return False

    return phash_distance(hash_a, hash_b) <= 8


def enrich_duplicate_pairs(pairs: List[Dict]) -> List[Dict]:
    """Add product metadata to duplicate pairs for display."""
    all_ids = list(set(
        [p["product_id_a"] for p in pairs] +
        [p["product_id_b"] for p in pairs]
    ))
    products = {p["id"]: p for p in get_products_by_ids(all_ids)}

    enriched = []
    for pair in pairs:
        prod_a = products.get(pair["product_id_a"], {})
        prod_b = products.get(pair["product_id_b"], {})

        enriched.append({
            **pair,
            "title_a": prod_a.get("title", "Unknown"),
            "title_b": prod_b.get("title", "Unknown"),
            "price_a": prod_a.get("price", 0),
            "price_b": prod_b.get("price", 0),
            "category_a": prod_a.get("category", ""),
            "category_b": prod_b.get("category", ""),
        })

    return enriched
