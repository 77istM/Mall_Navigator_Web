"""Application health checks for graphs and product cache integrity."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_json(path: str) -> tuple[bool, Any, str]:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return True, payload, "ok"
    except FileNotFoundError:
        return False, None, "file_not_found"
    except json.JSONDecodeError:
        return False, None, "invalid_json"
    except OSError:
        return False, None, "read_error"


def check_graph_file(path: str) -> dict[str, Any]:
    ok, payload, reason = _load_json(path)
    if not ok:
        return {"ok": False, "kind": "graph", "path": path, "reason": reason}

    if not isinstance(payload, dict):
        return {"ok": False, "kind": "graph", "path": path, "reason": "payload_not_object"}

    nodes = payload.get("nodes")
    edges = payload.get("edges")
    if not isinstance(nodes, dict) or not isinstance(edges, dict):
        return {"ok": False, "kind": "graph", "path": path, "reason": "missing_nodes_or_edges"}

    missing_edge_nodes = []
    for node_id, neighbors in edges.items():
        if node_id not in nodes:
            missing_edge_nodes.append(node_id)
        if isinstance(neighbors, dict):
            for target in neighbors:
                if target not in nodes:
                    missing_edge_nodes.append(f"{node_id}->{target}")

    return {
        "ok": len(missing_edge_nodes) == 0,
        "kind": "graph",
        "path": path,
        "reason": "ok" if not missing_edge_nodes else "edge_references_missing_nodes",
        "node_count": len(nodes),
        "edge_count": sum(len(v) for v in edges.values() if isinstance(v, dict)),
        "issues": missing_edge_nodes[:10],
    }


def check_products_file(path: str) -> dict[str, Any]:
    ok, payload, reason = _load_json(path)
    if not ok:
        return {"ok": False, "kind": "products", "path": path, "reason": reason}

    if not isinstance(payload, dict):
        return {"ok": False, "kind": "products", "path": path, "reason": "payload_not_object"}

    malformed = []
    for name, info in payload.items():
        if not isinstance(info, dict):
            malformed.append(name)
            continue
        required = {"floor", "x", "y", "nearest_node"}
        if not required.issubset(set(info.keys())):
            malformed.append(name)

    return {
        "ok": len(malformed) == 0,
        "kind": "products",
        "path": path,
        "reason": "ok" if not malformed else "invalid_product_entries",
        "product_count": len(payload),
        "issues": malformed[:10],
    }


def run_health_checks(*, graph_paths: list[str], products_path: str) -> dict[str, Any]:
    checks = [check_graph_file(path) for path in graph_paths]
    checks.append(check_products_file(products_path))
    return {
        "ok": all(item.get("ok", False) for item in checks),
        "checks": checks,
    }
