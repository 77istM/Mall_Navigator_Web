"""Tests for Phase 2 feature foundations."""

from __future__ import annotations

import json

from algorithms.yen_ksp import yen_k_shortest_paths
from components.product_manager import is_product_open
from utils.db import migrate_json_to_sqlite, SQLiteProductStore
from utils.routing import build_accessible_graph, walking_time_seconds


def test_accessible_graph_penalizes_stairs_edges() -> None:
    graph = {
        "a": {"b": 10.0, "c": 3.0},
        "b": {"a": 10.0},
        "c": {"a": 3.0},
    }
    nodes = {
        "a": {"type": "corridor"},
        "b": {"type": "stairs"},
        "c": {"type": "corridor"},
    }

    weighted = build_accessible_graph(graph, nodes, prefer_accessible=True, stairs_penalty=5.0)
    assert weighted["a"]["b"] == 50.0
    assert weighted["a"]["c"] == 3.0


def test_walking_time_counts_stairs_as_slower() -> None:
    nodes = {
        "s": {"x": 0, "y": 0, "type": "corridor"},
        "m": {"x": 10, "y": 0, "type": "stairs"},
        "e": {"x": 20, "y": 0, "type": "corridor"},
    }

    direct = walking_time_seconds(["s", "e"], nodes, px_per_metre=10.0)
    with_stairs = walking_time_seconds(["s", "m", "e"], nodes, px_per_metre=10.0)
    assert with_stairs > direct


def test_yen_k_shortest_returns_multiple_paths() -> None:
    graph = {
        "A": {"B": 1.0, "C": 1.0},
        "B": {"D": 1.0},
        "C": {"D": 1.0},
        "D": {},
    }

    routes = yen_k_shortest_paths(graph, "A", "D", k=3)
    assert len(routes) >= 2
    assert routes[0]["cost"] == 2.0


def test_is_product_open_simple_schedule() -> None:
    sample = {"opening_hours": "00:00-23:59"}
    assert is_product_open(sample) is True


def test_migrate_json_to_sqlite(tmp_path) -> None:
    source = tmp_path / "products.json"
    target = tmp_path / "products.db"

    source.write_text(
        json.dumps(
            {
                "apple": {
                    "floor": 1,
                    "x": 10,
                    "y": 20,
                    "nearest_node": "apple_store",
                    "note": "",
                    "timestamp": "2026-01-01T10:00:00",
                }
            }
        ),
        encoding="utf-8",
    )

    migrated = migrate_json_to_sqlite(source, target)
    assert migrated == 1

    store = SQLiteProductStore(target)
    all_products = store.load_all()
    assert "apple" in all_products
