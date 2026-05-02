import streamlit as st
import numpy as np
import faiss
import json
import pickle
from pathlib import Path
from typing import List, Dict

try:
    from sentence_transformers import SentenceTransformer
    ST_AVAILABLE = True
except ImportError:
    ST_AVAILABLE = False

INDEX_PATH = Path("data/faiss_index.pkl")
IDS_PATH = Path("data/faiss_ids.json")

BGE_MODEL = "BAAI/bge-large-en-v1.5"
FALLBACK_MODEL = "all-MiniLM-L6-v2"


@st.cache_resource(show_spinner=False)
def load_embedder():
    if not ST_AVAILABLE:
        return None
    try:
        model = SentenceTransformer(BGE_MODEL)
        return model
    except Exception:
        try:
            return SentenceTransformer(FALLBACK_MODEL)
        except Exception:
            return None


def make_product_text(product: dict) -> str:
    parts = [
        product.get("title", ""),
        product.get("description", ""),
        product.get("category", ""),
    ]
    text = " | ".join([p for p in parts if p])
    return f"passage: {text}"


def make_query_text(query: str) -> str:
    return f"query: {query}"


def embed_texts(texts: List[str]) -> np.ndarray | None:
    model = load_embedder()
    if model is None or not texts:
        return None
    try:
        embeddings = model.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        return embeddings.astype(np.float32)
    except Exception:
        return None


def embed_single(text: str) -> np.ndarray | None:
    result = embed_texts([text])
    return result[0] if result is not None else None


class VectorStore:

    def __init__(self):
        self.index = None
        self.ids = []
        self.dimension = None
        self._vectors = None  # Store vectors separately for safe retrieval
        self._load()

    def _load(self):
        try:
            if INDEX_PATH.exists() and IDS_PATH.exists():
                with open(INDEX_PATH, "rb") as f:
                    data = pickle.load(f)
                    if isinstance(data, dict):
                        self.index = data.get("index")
                        self._vectors = data.get("vectors")
                    else:
                        self.index = data
                        self._vectors = None
                with open(IDS_PATH) as f:
                    self.ids = json.load(f)
                if self.index:
                    self.dimension = self.index.d
        except Exception:
            self.index = None
            self.ids = []
            self._vectors = None

    def _save(self):
        INDEX_PATH.parent.mkdir(exist_ok=True)
        with open(INDEX_PATH, "wb") as f:
            pickle.dump({"index": self.index, "vectors": self._vectors}, f)
        with open(IDS_PATH, "w") as f:
            json.dump(self.ids, f)

    def add_products(self, products: List[Dict]) -> int:
        texts = [make_product_text(p) for p in products]
        embeddings = embed_texts(texts)

        if embeddings is None:
            return 0

        dim = embeddings.shape[1]

        if self.index is None or self.dimension != dim:
            self.index = faiss.IndexFlatIP(dim)
            self.dimension = dim
            self.ids = []
            self._vectors = embeddings
        else:
            if self._vectors is not None:
                self._vectors = np.vstack([self._vectors, embeddings])
            else:
                self._vectors = embeddings

        self.index.add(embeddings)
        self.ids.extend([p["id"] for p in products])
        self._save()
        return len(products)

    def search(self, query: str, top_k: int = 20,
               category_filter: str = None, max_price: float = None) -> List[Dict]:
        if self.index is None or len(self.ids) == 0:
            return []

        query_vec = embed_single(make_query_text(query))
        if query_vec is None:
            return []

        query_vec = query_vec.reshape(1, -1)
        k = min(len(self.ids), top_k * 5)
        scores, indices = self.index.search(query_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or idx >= len(self.ids):
                continue
            results.append({
                "product_id": self.ids[idx],
                "score": float(score)
            })

        return results

    def get_similar(self, product_id: str, top_k: int = 10) -> List[Dict]:
        if product_id not in self.ids or self.index is None:
            return []

        idx = self.ids.index(product_id)

        # Use stored vectors for safe retrieval (no rev_swig_ptr)
        if self._vectors is not None and idx < len(self._vectors):
            vec = self._vectors[idx].reshape(1, -1).astype(np.float32)
        else:
            return []

        k = min(len(self.ids), top_k + 1)
        scores, indices = self.index.search(vec, k)

        results = []
        for score, ridx in zip(scores[0], indices[0]):
            if ridx == -1 or ridx >= len(self.ids):
                continue
            pid = self.ids[ridx]
            if pid == product_id:
                continue
            results.append({"product_id": pid, "score": float(score)})

        return results[:top_k]

    def rebuild(self, products: List[Dict]) -> int:
        self.index = None
        self.ids = []
        self._vectors = None
        return self.add_products(products)

    def is_ready(self) -> bool:
        return self.index is not None and len(self.ids) > 0

    def size(self) -> int:
        return len(self.ids)


@st.cache_resource(show_spinner=False)
def get_vector_store() -> VectorStore:
    return VectorStore()