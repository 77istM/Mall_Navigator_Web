"""Tests for Phase 3 analytics tracking."""

from __future__ import annotations

from utils.analytics import AnalyticsStore


def test_track_search_and_top_terms(tmp_path) -> None:
    store = AnalyticsStore(str(tmp_path / "analytics.json"))

    store.track_search("apple")
    store.track_search("apple")
    store.track_search("milk")

    top = store.top_search_terms(limit=2)
    assert top[0] == ("apple", 2)
    assert top[1] == ("milk", 1)


def test_track_route_and_slow_areas(tmp_path) -> None:
    store = AnalyticsStore(str(tmp_path / "analytics.json"))

    store.track_route(["a", "b", "c"])
    store.track_route(["a", "b", "d"])

    routes = dict(store.top_routes(limit=5))
    assert routes["a->c"] == 1
    assert routes["a->d"] == 1

    areas = dict(store.slow_areas(limit=5))
    assert areas["a"] == 2
    assert areas["b"] == 2


def test_algorithm_summary(tmp_path) -> None:
    store = AnalyticsStore(str(tmp_path / "analytics.json"))

    store.track_algorithm_result(
        "astar",
        {"found": True, "time_us": 10.0, "nodes_visited": 5, "cost": 12.0},
    )
    store.track_algorithm_result(
        "astar",
        {"found": False, "time_us": 20.0, "nodes_visited": 8, "cost": 0.0},
    )

    summary = store.algorithm_summary()
    assert "astar" in summary
    assert summary["astar"]["runs"] == 2
    assert summary["astar"]["avg_time_us"] == 15.0
    assert summary["astar"]["avg_nodes_visited"] == 6.5
    assert summary["astar"]["success_rate"] == 0.5
