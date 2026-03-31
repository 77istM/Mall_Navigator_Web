"""Product cache manager with pluggable JSON/SQLite storage."""

from datetime import datetime
import os
from typing import Dict

from config import PRODUCTS_DB_FILE, PRODUCTS_FILE
from utils.coordinates import nearest_node as _nearest_node
from utils.db import JsonProductStore, SQLiteProductStore
from utils.security import is_valid_product_name, sanitize_query, sanitize_text


def _build_store():
    backend = os.getenv("PRODUCT_STORE_BACKEND", "json").lower().strip()
    if backend == "sqlite":
        db_path = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", PRODUCTS_DB_FILE)
        )
        return SQLiteProductStore(db_path)

    json_path = os.path.normpath(
        os.path.join(os.path.dirname(__file__), "..", PRODUCTS_FILE)
    )
    return JsonProductStore(json_path)


_PRODUCT_STORE = _build_store()


def load_products() -> Dict[str, Dict]:
    """Load and return the full product cache dict."""
    return _PRODUCT_STORE.load_all()


def save_products(products: dict) -> None:
    """Persist all product entries to the configured store backend."""
    for name, product in products.items():
        _PRODUCT_STORE.upsert(name, product)


def add_product(
    name: str,
    floor: int,
    x: float,
    y: float,
    nodes_for_floor: Dict,
    note: str = "",
    opening_hours: str = "",
    category: str = "",
) -> tuple[dict, str]:
    """Add or overwrite a product entry and return (products, nearest_node)."""
    products = load_products()
    clean_name = sanitize_text(name, max_len=80)
    if not is_valid_product_name(clean_name):
        raise ValueError("Product name must be 2-80 valid characters")

    key = clean_name.lower().strip()
    nn = _nearest_node(x, y, nodes_for_floor)
    payload = {
        "floor": floor,
        "x": x,
        "y": y,
        "nearest_node": nn,
        "note": sanitize_text(note, max_len=200),
        "opening_hours": sanitize_text(opening_hours, max_len=32),
        "category": sanitize_text(category, max_len=32),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    products[key] = payload
    _PRODUCT_STORE.upsert(key, payload)
    return products, nn


def delete_product(name: str) -> Dict[str, Dict]:
    """Remove a product from the cache. Returns updated dict."""
    products = load_products()
    key = sanitize_text(name, max_len=80).lower().strip()
    products.pop(key, None)
    _PRODUCT_STORE.delete(key)
    return products


def search_products(query: str, products: dict | None = None) -> list[tuple[str, dict]]:
    """Case-insensitive partial-match search with exact-match priority."""
    if products is None:
        products = load_products()
    q = sanitize_query(query, max_len=80)
    if not q:
        return list(products.items())
    exact = [(k, v) for k, v in products.items() if k == q]
    partial = [(k, v) for k, v in products.items() if q in k and k != q]
    return exact + sorted(partial, key=lambda t: t[0])


def products_for_floor(floor: int, products: Dict[str, Dict] | None = None) -> Dict[str, Dict]:
    """Return only products on the given floor."""
    if products is None:
        products = load_products()
    return {k: v for k, v in products.items() if v.get("floor") == floor}


def is_product_open(product: dict, now: datetime | None = None) -> bool | None:
    """Return open status for simple HH:MM-HH:MM schedule, None if unknown."""
    opening_hours = str(product.get("opening_hours", "")).strip()
    if not opening_hours or "-" not in opening_hours:
        return None

    now = now or datetime.now()
    try:
        start_s, end_s = [part.strip() for part in opening_hours.split("-", 1)]
        start_h, start_m = [int(part) for part in start_s.split(":", 1)]
        end_h, end_m = [int(part) for part in end_s.split(":", 1)]
    except (TypeError, ValueError):
        return None

    cur_min = now.hour * 60 + now.minute
    start_min = start_h * 60 + start_m
    end_min = end_h * 60 + end_m
    if end_min < start_min:
        return cur_min >= start_min or cur_min <= end_min
    return start_min <= cur_min <= end_min
