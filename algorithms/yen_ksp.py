"""Yen's K-shortest loopless paths implementation."""

from __future__ import annotations

import heapq
import math
from typing import Optional


def _shortest_path(
    graph: dict[str, dict[str, float]],
    start: str,
    end: str,
    *,
    banned_nodes: set[str] | None = None,
    banned_edges: set[tuple[str, str]] | None = None,
) -> tuple[list[str], float]:
    banned_nodes = banned_nodes or set()
    banned_edges = banned_edges or set()

    if start in banned_nodes or end in banned_nodes:
        return [], math.inf

    dist: dict[str, float] = {start: 0.0}
    prev: dict[str, Optional[str]] = {start: None}
    heap: list[tuple[float, str]] = [(0.0, start)]
    visited: set[str] = set()

    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)

        if u == end:
            break

        for v, w in graph.get(u, {}).items():
            if v in banned_nodes or (u, v) in banned_edges:
                continue
            alt = d + float(w)
            if alt < dist.get(v, math.inf):
                dist[v] = alt
                prev[v] = u
                heapq.heappush(heap, (alt, v))

    if dist.get(end, math.inf) == math.inf:
        return [], math.inf

    path: list[str] = []
    cur: Optional[str] = end
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()

    if not path or path[0] != start:
        return [], math.inf

    return path, dist[end]


def _path_cost(graph: dict[str, dict[str, float]], path: list[str]) -> float:
    total = 0.0
    for i in range(len(path) - 1):
        total += float(graph[path[i]][path[i + 1]])
    return total


def yen_k_shortest_paths(
    graph: dict[str, dict[str, float]],
    start: str,
    end: str,
    k: int = 3,
) -> list[dict[str, object]]:
    """Return up to k loopless shortest paths from start to end."""
    if k <= 0:
        return []

    first_path, first_cost = _shortest_path(graph, start, end)
    if not first_path:
        return []

    accepted: list[list[str]] = [first_path]
    candidates: list[tuple[float, tuple[str, ...]]] = []
    seen_candidates: set[tuple[str, ...]] = {tuple(first_path)}

    for kth in range(1, k):
        previous_path = accepted[kth - 1]

        for i in range(len(previous_path) - 1):
            spur_node = previous_path[i]
            root_path = previous_path[: i + 1]

            banned_edges: set[tuple[str, str]] = set()
            for path in accepted:
                if len(path) > i and path[: i + 1] == root_path:
                    banned_edges.add((path[i], path[i + 1]))

            banned_nodes = set(root_path[:-1])
            spur_path, spur_cost = _shortest_path(
                graph,
                spur_node,
                end,
                banned_nodes=banned_nodes,
                banned_edges=banned_edges,
            )
            if not spur_path:
                continue

            total_path = root_path[:-1] + spur_path
            path_key = tuple(total_path)
            if path_key in seen_candidates:
                continue
            seen_candidates.add(path_key)

            root_cost = _path_cost(graph, root_path)
            total_cost = root_cost + spur_cost
            heapq.heappush(candidates, (total_cost, path_key))

        if not candidates:
            break

        _, next_path_tuple = heapq.heappop(candidates)
        accepted.append(list(next_path_tuple))

    results: list[dict[str, object]] = []
    for path in accepted:
        results.append({"path": path, "cost": round(_path_cost(graph, path), 2)})

    return results
