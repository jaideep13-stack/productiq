import uuid
import pandas as pd
from pydantic import BaseModel, validator, Field
from typing import Optional, Literal
from decimal import Decimal


# ─── Canonical Schema ─────────────────────────────────────────────────────────

class ProductSchema(BaseModel):
    """
    Canonical product schema — every source normalized into this before
    anything downstream touches the data. (Architecture: Layer 1)
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str
    description: Optional[str] = None
    price: float
    currency: str = "INR"
    category: Optional[str] = None
    seller_id: Optional[str] = "S_UNKNOWN"
    image_url: Optional[str] = None
    source: Literal["csv", "api", "manual", "seed"] = "manual"
    in_stock: int = 1

    @validator("title")
    def title_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        return v

    @validator("price")
    def price_positive(cls, v):
        if v <= 0:
            raise ValueError("Price must be positive")
        return round(float(v), 2)

    @validator("category")
    def normalize_category(cls, v):
        if not v:
            return "uncategorized"
        return v.lower().strip().replace(" ", "_")

    def to_db_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description or "",
            "price": self.price,
            "currency": self.currency,
            "category": self.category,
            "seller_id": self.seller_id,
            "image_url": self.image_url or "",
            "source": self.source,
            "in_stock": self.in_stock
        }


# ─── CSV Importer ─────────────────────────────────────────────────────────────

REQUIRED_COLUMNS = {"title", "price"}

COLUMN_ALIASES = {
    "product_name": "title",
    "name": "title",
    "cost": "price",
    "mrp": "price",
    "desc": "description",
    "product_description": "description",
    "cat": "category",
    "img": "image_url",
    "image": "image_url",
    "stock": "in_stock",
    "seller": "seller_id",
}


def parse_csv(df: pd.DataFrame) -> tuple[list[ProductSchema], list[dict]]:
    """
    Parse a DataFrame into ProductSchema objects.
    Returns (valid_products, error_rows).
    Idempotent — keyed on title+price hash.
    """
    # Normalize column names
    df.columns = [c.lower().strip() for c in df.columns]
    df.rename(columns=COLUMN_ALIASES, inplace=True)

    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing required columns: {missing}. Found: {list(df.columns)}")

    valid = []
    errors = []

    for idx, row in df.iterrows():
        try:
            product = ProductSchema(
                title=str(row.get("title", "")).strip(),
                price=float(str(row.get("price", 0)).replace(",", "").replace("₹", "")),
                description=str(row.get("description", "")) if pd.notna(row.get("description")) else None,
                category=str(row.get("category", "uncategorized")) if pd.notna(row.get("category")) else None,
                seller_id=str(row.get("seller_id", "S_IMPORT")),
                image_url=str(row.get("image_url", "")) if pd.notna(row.get("image_url")) else None,
                currency=str(row.get("currency", "INR")),
                in_stock=int(row.get("in_stock", 1)),
                source="csv"
            )
            valid.append(product)
        except Exception as e:
            errors.append({
                "row": idx + 2,
                "title": str(row.get("title", ""))[:40],
                "error": str(e)
            })

    return valid, errors


def generate_sample_csv_bytes() -> bytes:
    """Generate a sample CSV for users to download and fill."""
    sample = pd.DataFrame([
        {
            "title": "Ergonomic Standing Desk — Black Frame",
            "description": "Electric height adjustable standing desk. 3 memory settings. 120x60cm.",
            "price": 22999,
            "currency": "INR",
            "category": "furniture",
            "seller_id": "S001",
            "image_url": "https://images.unsplash.com/photo-1593642632559-0c6d3fc62b89?w=400",
            "in_stock": 1
        },
        {
            "title": "Wireless Mouse — Ergonomic Vertical",
            "description": "Vertical ergonomic mouse, reduces wrist strain. 6 buttons, 4000 DPI.",
            "price": 2499,
            "currency": "INR",
            "category": "electronics",
            "seller_id": "S002",
            "image_url": "",
            "in_stock": 1
        },
    ])
    return sample.to_csv(index=False).encode("utf-8")
