"""Phase 4 health-check tests."""

from __future__ import annotations

import json

from utils.health import run_health_checks


def test_run_health_checks_success(tmp_path) -> None:
    graph = tmp_path / "ground.json"
    products = tmp_path / "products.json"

    graph.write_text(
        json.dumps(
            {
                "nodes": {
                    "a": {"x": 0, "y": 0},
                    "b": {"x": 1, "y": 0},
                },
                "edges": {"a": {"b": 1}, "b": {"a": 1}},
            }
        ),
        encoding="utf-8",
    )
    products.write_text(
        json.dumps(
            {
                "milk": {
                    "floor": 1,
                    "x": 10,
                    "y": 20,
                    "nearest_node": "a",
                }
            }
        ),
        encoding="utf-8",
    )

    result = run_health_checks(graph_paths=[str(graph)], products_path=str(products))
    assert result["ok"] is True


def test_run_health_checks_detects_invalid_edges(tmp_path) -> None:
    graph = tmp_path / "broken.json"
    products = tmp_path / "products.json"

    graph.write_text(
        json.dumps(
            {
                "nodes": {"a": {"x": 0, "y": 0}},
                "edges": {"a": {"missing": 1}},
            }
        ),
        encoding="utf-8",
    )
    products.write_text("{}", encoding="utf-8")

    result = run_health_checks(graph_paths=[str(graph)], products_path=str(products))
    assert result["ok"] is False
    assert any(check["reason"] == "edge_references_missing_nodes" for check in result["checks"])
