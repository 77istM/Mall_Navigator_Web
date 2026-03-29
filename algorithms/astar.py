"""A* shortest-path algorithm with coordinate-based Euclidean heuristic.

Unlike the version in the original A-level project (which used hardcoded per-node
heuristic values that could violate admissibility), this implementation derives
h(n) from the straight-line Euclidean distance between pixel coordinates.
Because edge weights are also Euclidean distances, h(n) <= actual_cost always
holds (admissible), so A* is guaranteed to return the optimal path.
"""
import heapq
import math
import time
from typing import Optional


def astar(
    graph: dict[str, dict[str, float]],
    node_coords: dict[str, dict],
    start: str,
    end: str,
) -> dict:
    """
    Run A* algorithm and return a result bundle.

    Parameters
    ----------
    graph        : adjacency dict {node: {neighbour: weight, ...}, ...}
    node_coords  : {node: {"x": float, "y": float}, ...}
    start        : starting node id
    end          : target node id

    Returns
    -------
    dict with keys:
        path          - list[str]
        cost          - float
        nodes_visited - int
        time_us       - float
        found         - bool
    """
    t0 = time.perf_counter()

    def h(a: str, b: str) -> float:
        """Euclidean straight-line distance — admissible heuristic."""
        ax, ay = node_coords[a]["x"], node_coords[a]["y"]
        bx, by = node_coords[b]["x"], node_coords[b]["y"]
        return math.hypot(ax - bx, ay - by)

    # heap entries: (f_score, g_score, node)
    open_heap = [(h(start, end), 0.0, start)]
    g_score: dict[str, float] = {start: 0.0}
    came_from: dict[str, Optional[str]] = {}
    closed: set[str] = set()
    nodes_visited = 0

    while open_heap:
        f, g, current = heapq.heappop(open_heap)

        if current in closed:
            continue
        closed.add(current)
        nodes_visited += 1

        if current == end:
            elapsed = (time.perf_counter() - t0) * 1_000_000
            path = _reconstruct(came_from, start, end)
            return {
                "path": path,
                "cost": round(g, 2),
                "nodes_visited": nodes_visited,
                "time_us": round(elapsed, 2),
                "found": bool(path),
            }

        for neighbour, weight in graph.get(current, {}).items():
            if neighbour in closed:
                continue
            tentative_g = g + weight
            if tentative_g < g_score.get(neighbour, math.inf):
                came_from[neighbour] = current
                g_score[neighbour] = tentative_g
                f_new = tentative_g + h(neighbour, end)
                heapq.heappush(open_heap, (f_new, tentative_g, neighbour))

    elapsed = (time.perf_counter() - t0) * 1_000_000
    return {
        "path": [],
        "cost": math.inf,
        "nodes_visited": nodes_visited,
        "time_us": round(elapsed, 2),
        "found": False,
    }


def _reconstruct(came_from: dict, start: str, end: str) -> list[str]:
    path: list[str] = []
    node: Optional[str] = end
    while node is not None:
        path.append(node)
        node = came_from.get(node)
    path.reverse()
    return path if (path and path[0] == start) else []
