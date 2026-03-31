"""Advanced product search helpers (Phase 2 scaffold)."""

from __future__ import annotations

from typing import Iterable


def filter_by_category(products: dict[str, dict], category: str | None) -> dict[str, dict]:
    """Return products filtered by category (case-insensitive)."""
    if not category:
        return products

    wanted = category.strip().lower()
    return {
        name: info
        for name, info in products.items()
        if str(info.get("category", "")).strip().lower() == wanted
    }


def search_with_prefix_priority(
    query: str,
    products: dict[str, dict],
    *,
    limit: int = 10,
) -> list[tuple[str, dict]]:
    """Search products with exact > prefix > partial ranking."""
    q = query.strip().lower()
    if not q:
        return sorted(products.items(), key=lambda item: item[0])[:limit]

    exact = []
    prefix = []
    partial = []

    for name, info in products.items():
        n = name.lower()
        if n == q:
            exact.append((name, info))
        elif n.startswith(q):
            prefix.append((name, info))
        elif q in n:
            partial.append((name, info))

    ranked = exact + sorted(prefix, key=lambda i: i[0]) + sorted(partial, key=lambda i: i[0])
    return ranked[:limit]


def products_within_radius(
    products: dict[str, dict],
    *,
    floor: int,
    x: float,
    y: float,
    radius_px: float,
) -> list[tuple[str, dict, float]]:
    """Return products on the same floor within radius in pixel units."""
    hits: list[tuple[str, dict, float]] = []
    radius2 = radius_px * radius_px
    for name, info in products.items():
        if int(info.get("floor", -1)) != floor:
            continue
        dx = float(info["x"]) - x
        dy = float(info["y"]) - y
        d2 = dx * dx + dy * dy
        if d2 <= radius2:
            hits.append((name, info, d2 ** 0.5))

    return sorted(hits, key=lambda item: item[2])
