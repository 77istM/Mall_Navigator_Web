"""Product cache manager.

Products are stored in data/products.json as:
{
  "<name_lowercase>": {
    "floor": int,
    "x": float,
    "y": float,
    "nearest_node": str,
    "note": str,
    "timestamp": ISO-8601 str
  }
}
"""
import json
import os
from datetime import datetime
from typing import Dict, Tuple

from utils.coordinates import nearest_node as _nearest_node

_PRODUCTS_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "products.json"
)


def load_products() -> Dict[str, Dict]:
    """Load and return the full product cache dict."""
    path = os.path.normpath(_PRODUCTS_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_products(products: Dict[str, Dict]) -> None:
    """Persist the product cache to disk."""
    path = os.path.normpath(_PRODUCTS_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2)


def add_product(
    name: str,
    floor: int,
    x: float,
    y: float,
    nodes_for_floor: Dict,
    note: str = "",
) -> Tuple[Dict[str, Dict], str]:
    """
    Add or overwrite a product entry.

    Returns (updated_products_dict, nearest_node_id).
    """
    products = load_products()
    key = name.lower().strip()
    nn = _nearest_node(x, y, nodes_for_floor)
    products[key] = {
        "floor": floor,
        "x": x,
        "y": y,
        "nearest_node": nn,
        "note": note,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    save_products(products)
    return products, nn


def delete_product(name: str) -> Dict[str, Dict]:
    """Remove a product from the cache. Returns updated dict."""
    products = load_products()
    key = name.lower().strip()
    products.pop(key, None)
    save_products(products)
    return products


def search_products(query: str, products: Dict[str, Dict] | None = None) -> list[Tuple[str, Dict]]:
    """
    Case-insensitive partial-match search.

    Returns list of (name, info) pairs sorted by exact-match first,
    then alphabetical.
    """
    if products is None:
        products = load_products()
    q = query.lower().strip()
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
