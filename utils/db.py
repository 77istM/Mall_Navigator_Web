"""SQLite-backed product storage and migration helpers."""

from __future__ import annotations

import abc
import json
import sqlite3
from pathlib import Path


class ProductStore(abc.ABC):
    """Abstract product store interface."""

    @abc.abstractmethod
    def load_all(self) -> dict[str, dict]:
        """Return all products keyed by normalized product name."""

    @abc.abstractmethod
    def upsert(self, name: str, product: dict) -> None:
        """Insert or update a product entry."""

    @abc.abstractmethod
    def delete(self, name: str) -> None:
        """Delete a product entry by name."""


class JsonProductStore(ProductStore):
    """JSON-file implementation, backwards-compatible with existing app data."""

    def __init__(self, file_path: str | Path):
        self.file_path = Path(file_path)

    def load_all(self) -> dict[str, dict]:
        if not self.file_path.exists():
            return {}
        return json.loads(self.file_path.read_text(encoding="utf-8"))

    def upsert(self, name: str, product: dict) -> None:
        products = self.load_all()
        products[name] = product
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(products, indent=2),
            encoding="utf-8",
        )

    def delete(self, name: str) -> None:
        products = self.load_all()
        products.pop(name, None)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(
            json.dumps(products, indent=2),
            encoding="utf-8",
        )


class SQLiteProductStore(ProductStore):
    """SQLite implementation for larger datasets and richer queries."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS products (
                    name TEXT PRIMARY KEY,
                    floor INTEGER NOT NULL,
                    x REAL NOT NULL,
                    y REAL NOT NULL,
                    nearest_node TEXT NOT NULL,
                    note TEXT,
                    timestamp TEXT,
                    opening_hours TEXT,
                    category TEXT,
                    rating REAL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_products_floor ON products(floor)"
            )

    def load_all(self) -> dict[str, dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM products").fetchall()
        return {
            row["name"]: {
                "floor": row["floor"],
                "x": row["x"],
                "y": row["y"],
                "nearest_node": row["nearest_node"],
                "note": row["note"] or "",
                "timestamp": row["timestamp"] or "",
                "opening_hours": row["opening_hours"] or "",
                "category": row["category"] or "",
                "rating": row["rating"],
            }
            for row in rows
        }

    def upsert(self, name: str, product: dict) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO products (
                    name, floor, x, y, nearest_node, note, timestamp,
                    opening_hours, category, rating
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    floor = excluded.floor,
                    x = excluded.x,
                    y = excluded.y,
                    nearest_node = excluded.nearest_node,
                    note = excluded.note,
                    timestamp = excluded.timestamp,
                    opening_hours = excluded.opening_hours,
                    category = excluded.category,
                    rating = excluded.rating
                """,
                (
                    name,
                    int(product["floor"]),
                    float(product["x"]),
                    float(product["y"]),
                    str(product["nearest_node"]),
                    str(product.get("note", "")),
                    str(product.get("timestamp", "")),
                    str(product.get("opening_hours", "")),
                    str(product.get("category", "")),
                    product.get("rating"),
                ),
            )

    def delete(self, name: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM products WHERE name = ?", (name,))


def migrate_json_to_sqlite(json_path: str | Path, sqlite_path: str | Path) -> int:
    """Migrate all JSON products into SQLite and return migrated count."""
    source = JsonProductStore(json_path)
    target = SQLiteProductStore(sqlite_path)

    products = source.load_all()
    for name, product in products.items():
        target.upsert(name, product)
    return len(products)
