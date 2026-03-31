"""Live location tracking and route-progress helpers for Phase 3 MVP."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from utils.coordinates import euclidean, nearest_node

DEFAULT_STORAGE_PATH = "data/location_history.json"
DEFAULT_MAX_HISTORY = 1000
DEFAULT_OFF_ROUTE_METRES = 10.0
DEFAULT_ARRIVAL_THRESHOLD_METRES = 2.5
DEFAULT_WALKING_SPEED_MPS = 1.2


@dataclass(slots=True)
class PositionSample:
    """A single tracked user position sample."""

    timestamp: str
    floor: int
    x: float
    y: float
    node_id: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "floor": self.floor,
            "x": self.x,
            "y": self.y,
            "node_id": self.node_id,
            "source": self.source,
        }


class LocationTracker:
    """Persists consented position history and provides convenience helpers."""

    def __init__(
        self,
        storage_path: str = DEFAULT_STORAGE_PATH,
        *,
        max_history: int = DEFAULT_MAX_HISTORY,
    ) -> None:
        self.storage_path = Path(storage_path)
        self.max_history = max_history

    def _read_all(self) -> dict[str, list[dict[str, Any]]]:
        if not self.storage_path.exists():
            return {}
        try:
            raw = self.storage_path.read_text(encoding="utf-8")
            loaded = json.loads(raw)
            if isinstance(loaded, dict):
                return loaded
        except (json.JSONDecodeError, OSError):
            return {}
        return {}

    def _write_all(self, data: dict[str, list[dict[str, Any]]]) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def history_for(self, user_id: str) -> list[dict[str, Any]]:
        return list(self._read_all().get(user_id, []))

    def latest_for(self, user_id: str) -> dict[str, Any] | None:
        history = self.history_for(user_id)
        return history[-1] if history else None

    def record_position(
        self,
        *,
        user_id: str,
        floor: int,
        x: float,
        y: float,
        nodes: dict[str, dict[str, Any]],
        source: str,
        consent: bool,
    ) -> dict[str, Any] | None:
        if not consent:
            return None

        node_id = nearest_node(x, y, nodes)
        sample = PositionSample(
            timestamp=datetime.now(timezone.utc).isoformat(),
            floor=floor,
            x=float(x),
            y=float(y),
            node_id=node_id,
            source=source,
        )

        data = self._read_all()
        history = list(data.get(user_id, []))
        history.append(sample.to_dict())
        if len(history) > self.max_history:
            history = history[-self.max_history :]
        data[user_id] = history
        self._write_all(data)
        return sample.to_dict()


def nearest_route_index(
    path: list[str],
    nodes: dict[str, dict[str, Any]],
    *,
    x: float,
    y: float,
    start_index: int = 0,
) -> int:
    """Return index of the nearest route waypoint from start_index onward."""
    if not path:
        return 0

    begin = max(0, min(start_index, len(path) - 1))
    best_idx = begin
    best_dist = float("inf")
    for idx in range(begin, len(path)):
        node_id = path[idx]
        if node_id not in nodes:
            continue
        dist = euclidean(x, y, float(nodes[node_id]["x"]), float(nodes[node_id]["y"]))
        if dist < best_dist:
            best_dist = dist
            best_idx = idx
    return best_idx


def remaining_distance_metres(
    path: list[str],
    nodes: dict[str, dict[str, Any]],
    *,
    px_per_metre: float,
    start_index: int,
) -> float:
    """Calculate remaining route distance from start_index in metres."""
    if not path or len(path) < 2:
        return 0.0

    idx = max(0, min(start_index, len(path) - 1))
    remaining_px = 0.0
    for i in range(idx, len(path) - 1):
        a, b = path[i], path[i + 1]
        if a not in nodes or b not in nodes:
            continue
        remaining_px += euclidean(
            float(nodes[a]["x"]),
            float(nodes[a]["y"]),
            float(nodes[b]["x"]),
            float(nodes[b]["y"]),
        )

    safe_scale = max(px_per_metre, 0.1)
    return remaining_px / safe_scale


def estimate_eta_seconds(remaining_metres: float, *, speed_mps: float = DEFAULT_WALKING_SPEED_MPS) -> int:
    """Estimate ETA in seconds from remaining metres and walking speed."""
    safe_speed = max(speed_mps, 0.1)
    return int(round(max(0.0, remaining_metres) / safe_speed))


def is_off_route(
    path: list[str],
    nodes: dict[str, dict[str, Any]],
    *,
    x: float,
    y: float,
    px_per_metre: float,
    max_deviation_metres: float = DEFAULT_OFF_ROUTE_METRES,
    start_index: int = 0,
) -> tuple[bool, float]:
    """Return (off_route, nearest_distance_m)."""
    if not path:
        return False, 0.0

    idx = nearest_route_index(path, nodes, x=x, y=y, start_index=start_index)
    nid = path[idx]
    if nid not in nodes:
        return False, 0.0

    dist_px = euclidean(x, y, float(nodes[nid]["x"]), float(nodes[nid]["y"]))
    dist_m = dist_px / max(px_per_metre, 0.1)
    return dist_m > max_deviation_metres, dist_m


def auto_advance_step_index(
    path: list[str],
    nodes: dict[str, dict[str, Any]],
    *,
    x: float,
    y: float,
    px_per_metre: float,
    current_index: int,
    arrival_threshold_metres: float = DEFAULT_ARRIVAL_THRESHOLD_METRES,
) -> int:
    """Advance to next waypoint when close enough to current or nearest route node."""
    if not path:
        return 0

    idx = max(0, min(current_index, len(path) - 1))
    current_id = path[idx]
    if current_id in nodes:
        dist_px = euclidean(x, y, float(nodes[current_id]["x"]), float(nodes[current_id]["y"]))
        dist_m = dist_px / max(px_per_metre, 0.1)
        if dist_m <= arrival_threshold_metres and idx < len(path) - 1:
            return idx + 1

    return nearest_route_index(path, nodes, x=x, y=y, start_index=idx)
