import io
import requests
from PIL import Image
import numpy as np

try:
    import imagehash
    IMAGEHASH_AVAILABLE = True
except ImportError:
    IMAGEHASH_AVAILABLE = False


def compute_phash(image_bytes: bytes) -> str | None:
    """
    Compute perceptual hash of an image.
    Architecture doc: pHash pre-filter catches pixel-level duplicates
    in microseconds before expensive vector search.
    """
    if not IMAGEHASH_AVAILABLE:
        return None
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return str(imagehash.phash(img))
    except Exception:
        return None


def phash_distance(hash_a: str, hash_b: str) -> int:
    """
    Hamming distance between two pHashes.
    0 = identical, >10 = different images.
    """
    if not IMAGEHASH_AVAILABLE or not hash_a or not hash_b:
        return 999
    try:
        h1 = imagehash.hex_to_hash(hash_a)
        h2 = imagehash.hex_to_hash(hash_b)
        return h1 - h2
    except Exception:
        return 999


def is_exact_pixel_duplicate(hash_a: str, hash_b: str) -> bool:
    """pHash distance <= 4 = near-identical images."""
    return phash_distance(hash_a, hash_b) <= 4


def fetch_image(url: str, timeout: int = 5) -> bytes | None:
    """Download image from URL."""
    if not url or not url.startswith("http"):
        return None
    try:
        r = requests.get(url, timeout=timeout, stream=True)
        if r.status_code == 200:
            return r.content
        return None
    except Exception:
        return None


def image_to_thumbnail_bytes(image_bytes: bytes, size: tuple = (200, 200)) -> bytes | None:
    """Resize image to thumbnail for display."""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img.thumbnail(size)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    except Exception:
        return None


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
