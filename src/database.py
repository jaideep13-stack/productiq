import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path("data/productiq.db")


def get_conn():
    DB_PATH.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # Products — canonical product record
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            price REAL,
            currency TEXT DEFAULT 'INR',
            category TEXT,
            seller_id TEXT,
            image_url TEXT,
            source TEXT DEFAULT 'manual',
            in_stock INTEGER DEFAULT 1,
            phash TEXT,
            text_embedded INTEGER DEFAULT 0,
            enriched INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # LLM enrichments — auto-generated metadata
    cur.execute("""
        CREATE TABLE IF NOT EXISTS enrichments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT REFERENCES products(id),
            primary_category TEXT,
            subcategory TEXT,
            style_tags TEXT,
            use_case_tags TEXT,
            pricing_tier TEXT,
            seo_title TEXT,
            seo_description TEXT,
            quality_score INTEGER,
            missing_fields TEXT,
            raw_json TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Duplicate clusters
    cur.execute("""
        CREATE TABLE IF NOT EXISTS duplicate_clusters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id_a TEXT,
            product_id_b TEXT,
            similarity_score REAL,
            cluster_type TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Pricing comparables cache
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pricing_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id TEXT,
            comparable_ids TEXT,
            median_price REAL,
            p25_price REAL,
            p75_price REAL,
            suggested_min REAL,
            suggested_max REAL,
            explanation TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Search history
    cur.execute("""
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT,
            result_count INTEGER,
            latency_ms REAL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()

    _seed_sample_products()


def _seed_sample_products():
    """Seed with realistic sample product catalog."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    import uuid
    products = [
        ("Scandinavian Oak Study Desk — Minimalist Home Office",
         "Solid oak wood desk with clean lines and minimalist design. Perfect for small apartments. Dimensions: 120x60x75cm. Includes cable management tray.",
         18999, "furniture", "S001", "https://images.unsplash.com/photo-1518455027359-f3f8164ba6bd?w=400"),
        ("Ergonomic Mesh Office Chair with Lumbar Support",
         "Breathable mesh back, adjustable lumbar support, 4D armrests, height-adjustable. Supports up to 120kg. BIFMA certified.",
         12499, "furniture", "S002", "https://images.unsplash.com/photo-1541558869434-2840d308329a?w=400"),
        ("Nordic Wooden Desk — White Oak Finish",
         "White oak veneer desk for modern home offices. 120cm wide. Cable grommet included. Easy assembly.",
         16499, "furniture", "S001", "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400"),
        ("MacBook Pro M3 Laptop Stand — Aluminum",
         "Adjustable aluminum laptop stand for MacBook and other laptops. 6 height levels. Foldable and portable.",
         2999, "electronics", "S003", "https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=400"),
        ("Wireless Mechanical Keyboard — TKL Layout",
         "Tenkeyless wireless mechanical keyboard. Hot-swappable switches. 3-mode connectivity: Bluetooth 5.0, 2.4GHz, USB-C. 4000mAh battery.",
         5499, "electronics", "S003", "https://images.unsplash.com/photo-1511467687858-23d96c32e4ae?w=400"),
        ("Premium Noise Cancelling Over-Ear Headphones",
         "40-hour battery life, active noise cancellation, LDAC support, foldable design. Ideal for work from home and travel.",
         8999, "electronics", "S004", "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400"),
        ("Handwoven Jute Area Rug — Natural Beige 5x7ft",
         "100% natural jute fiber, handwoven by artisans. Reversible design. Non-slip backing. Eco-friendly and biodegradable.",
         3499, "home_decor", "S005", "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400"),
        ("Minimalist Ceramic Table Lamp — Matte White",
         "Ceramic base with linen shade. E27 bulb socket. Cord length 1.8m. Perfect for bedside or study tables.",
         2199, "home_decor", "S005", "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400"),
        ("Standing Desk Converter — Height Adjustable",
         "Sit-stand desk converter, 80cm wide. Gas spring mechanism. Supports dual monitors up to 15kg. No assembly required.",
         9999, "furniture", "S002", "https://images.unsplash.com/photo-1593642632823-8f785ba67e45?w=400"),
        ("Bamboo Desk Organizer Set — 5 Piece",
         "Set of 5 bamboo organizers including pen holder, letter tray, phone stand, drawer organizer, and file holder. Sustainable bamboo.",
         1299, "home_decor", "S006", "https://images.unsplash.com/photo-1544816565-aa8c1166648f?w=400"),
        ("Ultrawide 34-inch Curved Monitor — 144Hz",
         "34-inch ultrawide IPS panel, 3440x1440 resolution, 144Hz refresh rate, 1ms response time. AMD FreeSync Premium Pro.",
         42999, "electronics", "S004", "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=400"),
        ("Solid Walnut Floating Wall Shelf — Set of 3",
         "Solid American walnut wall shelves. Sizes: 60cm, 45cm, 30cm. Includes heavy-duty brackets rated for 25kg each.",
         4599, "furniture", "S006", "https://images.unsplash.com/photo-1558997519-83ea9252ebc8?w=400"),
        ("Premium Leather Executive Chair",
         "Italian leather office chair, high back, lumbar support, headrest, chrome base. Tilt tension adjustment.",
         24999, "furniture", "S007", "https://images.unsplash.com/photo-1580480055273-228ff5388ef8?w=400"),
        ("USB-C Docking Station — 12-in-1",
         "12-in-1 USB-C hub: 3x USB-A, 2x USB-C, HDMI 4K, DisplayPort, SD/microSD, Ethernet, 100W PD charging.",
         4299, "electronics", "S007", "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=400"),
        ("Indoor Plant Pot Set — Terracotta 3-Pack",
         "Handmade terracotta pots in 3 sizes (10cm, 15cm, 20cm). Drainage holes included. Perfect for succulents and herbs.",
         899, "home_decor", "S008", "https://images.unsplash.com/photo-1485955900006-10f4d324d411?w=400"),
    ]

    for title, desc, price, cat, seller, img in products:
        pid = str(uuid.uuid4())[:8]
        cur.execute("""
            INSERT INTO products (id, title, description, price, category, seller_id, image_url, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'seed')
        """, (pid, title, desc, price, cat, seller, img))

    conn.commit()
    conn.close()


# ─── CRUD ────────────────────────────────────────────────────────────────────

def insert_product(product: dict) -> str:
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO products
        (id, title, description, price, currency, category, seller_id, image_url, source, in_stock)
        VALUES (:id, :title, :description, :price, :currency, :category, :seller_id, :image_url, :source, :in_stock)
    """, product)
    conn.commit()
    conn.close()
    return product["id"]


def get_all_products(limit: int = 200) -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM products ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product(pid: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_products_by_ids(ids: list) -> list:
    if not ids:
        return []
    conn = get_conn()
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT * FROM products WHERE id IN ({placeholders})", ids
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_enrichment(product_id: str, enrichment: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO enrichments
        (product_id, primary_category, subcategory, style_tags, use_case_tags,
         pricing_tier, seo_title, seo_description, quality_score, missing_fields, raw_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        product_id,
        enrichment.get("primary_category", ""),
        enrichment.get("subcategory", ""),
        json.dumps(enrichment.get("style_tags", [])),
        json.dumps(enrichment.get("use_case_tags", [])),
        enrichment.get("pricing_tier", ""),
        enrichment.get("seo_title", ""),
        enrichment.get("seo_description", ""),
        enrichment.get("quality_score", 0),
        json.dumps(enrichment.get("missing_fields", [])),
        json.dumps(enrichment)
    ))
    conn.execute("UPDATE products SET enriched=1 WHERE id=?", (product_id,))
    conn.commit()
    conn.close()


def get_enrichment(product_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM enrichments WHERE product_id=? ORDER BY created_at DESC LIMIT 1",
        (product_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    for f in ["style_tags", "use_case_tags", "missing_fields"]:
        try:
            d[f] = json.loads(d[f]) if d[f] else []
        except Exception:
            d[f] = []
    return d


def save_duplicate_pair(pid_a: str, pid_b: str, score: float, cluster_type: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO duplicate_clusters (product_id_a, product_id_b, similarity_score, cluster_type)
        VALUES (?, ?, ?, ?)
    """, (pid_a, pid_b, score, cluster_type))
    conn.commit()
    conn.close()


def get_all_duplicates() -> list:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM duplicate_clusters ORDER BY similarity_score DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_pricing(product_id: str, pricing: dict):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO pricing_cache
        (product_id, comparable_ids, median_price, p25_price, p75_price,
         suggested_min, suggested_max, explanation)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        product_id,
        json.dumps(pricing.get("comparable_ids", [])),
        pricing.get("median_price", 0),
        pricing.get("p25_price", 0),
        pricing.get("p75_price", 0),
        pricing.get("suggested_min", 0),
        pricing.get("suggested_max", 0),
        pricing.get("explanation", "")
    ))
    conn.commit()
    conn.close()


def get_pricing(product_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM pricing_cache WHERE product_id=? ORDER BY created_at DESC LIMIT 1",
        (product_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def log_search(query: str, result_count: int, latency_ms: float):
    conn = get_conn()
    conn.execute(
        "INSERT INTO search_history (query, result_count, latency_ms) VALUES (?, ?, ?)",
        (query, result_count, latency_ms)
    )
    conn.commit()
    conn.close()


def get_stats() -> dict:
    conn = get_conn()
    stats = {
        "total_products": conn.execute("SELECT COUNT(*) FROM products").fetchone()[0],
        "enriched": conn.execute("SELECT COUNT(*) FROM products WHERE enriched=1").fetchone()[0],
        "duplicates_found": conn.execute("SELECT COUNT(*) FROM duplicate_clusters").fetchone()[0],
        "categories": conn.execute("SELECT COUNT(DISTINCT category) FROM products").fetchone()[0],
        "sellers": conn.execute("SELECT COUNT(DISTINCT seller_id) FROM products").fetchone()[0],
        "total_searches": conn.execute("SELECT COUNT(*) FROM search_history").fetchone()[0],
    }
    conn.close()
    return stats
