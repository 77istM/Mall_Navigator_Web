"""Routing utilities for accessibility and time estimation."""

from __future__ import annotations

from typing import Iterable


DEFAULT_WALKING_SPEED_MPS = 1.35
STAIRS_SPEED_MULTIPLIER = 1.8
DEFAULT_STAIRS_PENALTY = 4.0


def is_stairs_node(node_id: str, node_data: dict) -> bool:
    """Return True when a node represents stairs/escalator movement."""
    node_type = str(node_data.get("type", "")).lower()
    if node_type in {"stairs", "escalator", "lift"}:
        return True
    return "stairs" in node_id.lower() or "escalator" in node_id.lower()


def is_stairs_edge(u: str, v: str, nodes: dict[str, dict]) -> bool:
    """Return True if either edge endpoint is a stairs/escalator node."""
    return is_stairs_node(u, nodes.get(u, {})) or is_stairs_node(v, nodes.get(v, {}))


def build_accessible_graph(
    graph: dict[str, dict[str, float]],
    nodes: dict[str, dict],
    *,
    prefer_accessible: bool,
    stairs_penalty: float = DEFAULT_STAIRS_PENALTY,
) -> dict[str, dict[str, float]]:
    """Return a graph copy with optional stairs penalties for accessibility mode."""
    if not prefer_accessible:
        return graph

    weighted: dict[str, dict[str, float]] = {}
    for u, neighbours in graph.items():
        weighted[u] = {}
        for v, cost in neighbours.items():
            edge_cost = float(cost)
            if is_stairs_edge(u, v, nodes):
                edge_cost *= stairs_penalty
            weighted[u][v] = edge_cost
    return weighted


def walking_time_seconds(
    path: list[str],
    nodes: dict[str, dict],
    px_per_metre: float = 10.0,
    *,
    walking_speed_mps: float = DEFAULT_WALKING_SPEED_MPS,
    stairs_multiplier: float = STAIRS_SPEED_MULTIPLIER,
) -> int:
    """Estimate walking time in seconds using segment distance and complexity."""
    if not path or len(path) == 1:
        return 0

    seconds = 0.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        if u not in nodes or v not in nodes:
            continue

        dx = float(nodes[v]["x"]) - float(nodes[u]["x"])
        dy = float(nodes[v]["y"]) - float(nodes[u]["y"])
        metres = ((dx * dx + dy * dy) ** 0.5) / px_per_metre

        segment_seconds = metres / max(walking_speed_mps, 0.1)
        if is_stairs_edge(u, v, nodes):
            segment_seconds *= stairs_multiplier

        seconds += segment_seconds

    return int(round(seconds))


def path_cost(graph: dict[str, dict[str, float]], path: Iterable[str]) -> float:
    """Compute total path cost from a graph adjacency dictionary."""
    p = list(path)
    total = 0.0
    for i in range(len(p) - 1):
        total += float(graph[p[i]][p[i + 1]])
    return total
