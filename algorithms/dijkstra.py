"""Dijkstra's shortest-path algorithm with exploration statistics."""
import heapq
import math
import time
from typing import Optional


def dijkstra(
    graph: dict[str, dict[str, float]],
    start: str,
    end: str,
) -> dict:
    """
    Run Dijkstra's algorithm and return a result bundle.

    Parameters
    ----------
    graph  : adjacency dict  {node: {neighbour: weight, ...}, ...}
    start  : starting node id
    end    : target node id

    Returns
    -------
    dict with keys:
        path          - list[str]  ordered node ids, empty if unreachable
        cost          - float      total path weight
        nodes_visited - int        nodes moved from open to closed set
        time_us       - float      wall-clock microseconds
        found         - bool
    """
    t0 = time.perf_counter()

    dist: dict[str, float] = {n: math.inf for n in graph}
    dist[start] = 0.0
    prev: dict[str, Optional[str]] = {n: None for n in graph}
    heap = [(0.0, start)]
    visited: set[str] = set()
    nodes_visited = 0

    while heap:
        d, u = heapq.heappop(heap)
        if u in visited:
            continue
        visited.add(u)
        nodes_visited += 1

        if u == end:
            break

        for v, w in graph.get(u, {}).items():
            alt = d + w
            if alt < dist.get(v, math.inf):
                dist[v] = alt
                prev[v] = u
                heapq.heappush(heap, (alt, v))

    elapsed = (time.perf_counter() - t0) * 1_000_000

    if dist.get(end, math.inf) == math.inf:
        return {
            "path": [],
            "cost": math.inf,
            "nodes_visited": nodes_visited,
            "time_us": elapsed,
            "found": False,
        }

    path = _reconstruct(prev, start, end)
    return {
        "path": path,
        "cost": round(dist[end], 2),
        "nodes_visited": nodes_visited,
        "time_us": round(elapsed, 2),
        "found": bool(path),
    }


def _reconstruct(prev: dict, start: str, end: str) -> list[str]:
    path: list[str] = []
    node: Optional[str] = end
    while node is not None:
        path.append(node)
        node = prev.get(node)
    path.reverse()
    return path if (path and path[0] == start) else []
