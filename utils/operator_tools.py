"""Operator utilities for admin workflows and store onboarding."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

FLOOR_FILE_NAMES = {
    "lower": "lower",
    "ground": "ground",
    "upper": "upper",
}


def _validate_store_id(store_id: str) -> str:
    key = store_id.strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,64}", key):
        raise ValueError("store_id must match [a-z0-9_]{3,64}")
    return key


def load_json(path: Path, default: dict | None = None) -> dict:
    if not path.exists():
        return default.copy() if default else {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def generate_graph_from_image_size(width: int, height: int, floor_label: str) -> dict:
    """Create a simple starter waypoint graph from floor-plan dimensions."""
    cx = max(width // 2, 1)
    cy = max(height // 2, 1)
    x1 = max(width // 5, 1)
    x2 = max((width * 4) // 5, 1)
    y1 = max(height // 5, 1)
    y2 = max((height * 4) // 5, 1)

    nodes = {
        "entrance": {"x": x1, "y": y2, "label": f"{floor_label} Entrance", "type": "entrance"},
        "junction_w": {"x": x1, "y": cy, "label": "Junction West", "type": "corridor"},
        "junction_c": {"x": cx, "y": cy, "label": "Junction Center", "type": "corridor"},
        "junction_e": {"x": x2, "y": cy, "label": "Junction East", "type": "corridor"},
        "stairs": {"x": cx, "y": y1, "label": "Stairs", "type": "stairs"},
    }

    def dist(a: str, b: str) -> float:
        ax, ay = nodes[a]["x"], nodes[a]["y"]
        bx, by = nodes[b]["x"], nodes[b]["y"]
        return float(((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5)

    edges = {
        "entrance": {"junction_w": dist("entrance", "junction_w")},
        "junction_w": {
            "entrance": dist("junction_w", "entrance"),
            "junction_c": dist("junction_w", "junction_c"),
        },
        "junction_c": {
            "junction_w": dist("junction_c", "junction_w"),
            "junction_e": dist("junction_c", "junction_e"),
            "stairs": dist("junction_c", "stairs"),
        },
        "junction_e": {"junction_c": dist("junction_e", "junction_c")},
        "stairs": {"junction_c": dist("stairs", "junction_c")},
    }

    return {"nodes": nodes, "edges": edges}


def update_store_registry(
    stores_json_path: Path,
    *,
    store_id: str,
    store_name: str,
    lat: float,
    lng: float,
    graph_dir: str,
    map_dir: str,
) -> None:
    stores = load_json(stores_json_path, default={})
    stores[store_id] = {
        "name": store_name,
        "lat": lat,
        "lng": lng,
        "graph_dir": graph_dir,
        "map_dir": map_dir,
    }
    save_json(stores_json_path, stores)


def generate_store_readme(store_dir: Path, store_name: str, store_id: str) -> Path:
    readme = store_dir / "README.md"
    content = f"""# {store_name}\n\n## Store Id\n- {store_id}\n\n## Folder Layout\n- maps/: floor-plan images named lower.png, ground.png, upper.png\n- graphs/: waypoint graphs named lower.json, ground.json, upper.json\n\n## Onboarding Checklist\n- Verify floor-plan image scale and orientation\n- Review auto-generated graph nodes and edge weights\n- Update stairs/lift node ids for inter-floor links\n- Run health checks before deployment\n"""
    readme.write_text(content, encoding="utf-8")
    return readme


def scaffold_store(
    *,
    store_id: str,
    store_name: str,
    lat: float,
    lng: float,
    template_store: str,
    stores_json_path: Path,
    stores_root: Path,
) -> list[str]:
    """Create maps/graphs scaffold for a new store and register it."""
    created: list[str] = []
    sid = _validate_store_id(store_id)

    store_dir = stores_root / sid
    maps_dir = store_dir / "maps"
    graphs_dir = store_dir / "graphs"
    maps_dir.mkdir(parents=True, exist_ok=True)
    graphs_dir.mkdir(parents=True, exist_ok=True)
    created.extend([str(maps_dir), str(graphs_dir)])

    # Attempt to clone template files if they exist in current data layout.
    default_maps = Path("data/maps")
    default_graphs = Path("data/graphs")
    for floor_key, file_name in FLOOR_FILE_NAMES.items():
        src_map = default_maps / f"{file_name}.png"
        dst_map = maps_dir / f"{file_name}.png"
        if src_map.exists() and not dst_map.exists():
            shutil.copy2(src_map, dst_map)
            created.append(str(dst_map))

        src_graph = default_graphs / f"{file_name}.json"
        dst_graph = graphs_dir / f"{file_name}.json"
        if src_graph.exists() and not dst_graph.exists():
            shutil.copy2(src_graph, dst_graph)
            created.append(str(dst_graph))

    readme = generate_store_readme(store_dir, store_name, sid)
    created.append(str(readme))

    update_store_registry(
        stores_json_path,
        store_id=sid,
        store_name=store_name,
        lat=lat,
        lng=lng,
        graph_dir=f"data/stores/{sid}/graphs",
        map_dir=f"data/stores/{sid}/maps",
    )
    created.append(str(stores_json_path))

    return created
