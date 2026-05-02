# 🏗️ ProductIQ — Multi-Modal Product Intelligence Engine

AI-powered product catalog system with semantic search, duplicate detection,
comparable-based pricing, and LLM auto-tagging.

## Architecture (5 Layers)

| Layer | What it does | Tech |
|---|---|---|
| 1 — Ingestion | Pydantic schema validation, CSV import | Pydantic, pandas |
| 2 — Embedding | BGE-large text embeddings + LLM enrichment | sentence-transformers, Groq |
| 3 — Storage | FAISS vector index + SQLite metadata | FAISS, SQLite |
| 4 — Intelligence | Hybrid search (RRF), dedup, pricing, tagging | RRF, pHash, numpy |
| 5 — Frontend | Streamlit dashboard | Streamlit, Plotly |

## Project Structure

```
app.py
requirements.txt
.python-version

src/
  database.py          # SQLite CRUD + seed data
  ingestion.py         # Pydantic schema + CSV parser
  embedder.py          # BGE embeddings + FAISS vector store
  search_engine.py     # RRF hybrid search
  dedup_engine.py      # Duplicate detection (3-tier thresholds)
  pricing_engine.py    # Comparable-based statistical pricing
  llm_enricher.py      # LLM auto-tagging (closed vocabulary)
  image_utils.py       # pHash duplicate pre-filter
  screens/
    home.py
    ingest.py
    search.py
    dedup.py
    pricing.py
    enrichment.py
```

---

## Run on Your Machine

### Step 1 — Extract & open in VS Code
```bash
cd productiq
```

### Step 2 — Virtual environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```
> First install ~5-8 minutes (sentence-transformers is heavy)

### Step 4 — Groq API Key (optional but recommended)
- Free at https://console.groq.com
- Add to `.streamlit/secrets.toml`:
```toml
GROQ_API_KEY = "gsk_your_key_here"
```
> Without key: rule-based enrichment used (still works)

### Step 5 — Run
```bash
streamlit run app.py
```

---

## How to Use

1. **Home** — Overview, stats, architecture diagram
2. **Ingest** — Upload CSV or add products manually → Build Vector Index
3. **Search** — Type any natural language query (e.g. "minimalist desk for small apartment")
4. **Dedup** — Scan catalog for exact/near/variant duplicates
5. **Pricing** — Select any product → get comparable-based price analysis
6. **Enrichment** — AI auto-tag with categories, style tags, SEO title/description

---

## Interview Talking Points

- **Why BGE-large over OpenAI embeddings?** Free, self-hosted, top of MTEB leaderboard, no API cost at scale
- **Why FAISS over Qdrant?** Local demo — same algorithm (HNSW/flat), Qdrant for production
- **What is RRF?** Reciprocal Rank Fusion — merges ranked lists without score calibration: score = Σ 1/(k + rank)
- **Why pHash before vector search?** Catches pixel-level duplicates in microseconds vs milliseconds for vector search — 1000x faster pre-filter
- **Why closed vocabulary for LLM tags?** Prevents "scandinavian" vs "nordic" drift — LLM picks from fixed taxonomy, not free-form
- **Why statistics for pricing, not LLM?** LLM hallucinates prices. Statistics on 50 real comparables are accurate. LLM only writes the explanation.
