"""Integration tests for end-to-end routing flow (without UI browser automation)."""

from __future__ import annotations

import json

from algorithms.astar import astar
from components.map_view import generate_directions


DATA_PATH = "data/graphs/ground.json"


def test_full_flow_select_to_directions() -> None:
    payload = json.loads(open(DATA_PATH, encoding="utf-8").read())
    nodes = payload["nodes"]
    edges = payload["edges"]

    start = "entrance_gf"
    end = "apple_store"

    result = astar(edges, nodes, start, end)
    assert result["found"] is True
    assert result["path"][0] == start
    assert result["path"][-1] == end

    steps = generate_directions(result["path"], nodes, px_per_metre=10.0)
    assert len(steps) > 0
    assert all("direction" in step for step in steps)
