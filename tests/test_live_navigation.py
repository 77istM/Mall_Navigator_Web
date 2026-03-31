"""Tests for Phase 3 live navigation tracking helpers."""

from __future__ import annotations

from utils.location_tracking import (
    LocationTracker,
    auto_advance_step_index,
    estimate_eta_seconds,
    is_off_route,
    nearest_route_index,
    remaining_distance_metres,
)


def test_record_position_requires_consent(tmp_path) -> None:
    tracker = LocationTracker(str(tmp_path / "history.json"))
    nodes = {
        "a": {"x": 0, "y": 0},
        "b": {"x": 10, "y": 0},
    }

    saved = tracker.record_position(
        user_id="u1",
        floor=1,
        x=1,
        y=1,
        nodes=nodes,
        source="manual",
        consent=False,
    )

    assert saved is None
    assert tracker.history_for("u1") == []


def test_record_position_persists_with_consent(tmp_path) -> None:
    tracker = LocationTracker(str(tmp_path / "history.json"))
    nodes = {
        "a": {"x": 0, "y": 0},
        "b": {"x": 10, "y": 0},
    }

    tracker.record_position(
        user_id="u1",
        floor=1,
        x=9,
        y=0,
        nodes=nodes,
        source="manual",
        consent=True,
    )

    history = tracker.history_for("u1")
    assert len(history) == 1
    assert history[0]["node_id"] == "b"


def test_route_progress_helpers() -> None:
    nodes = {
        "a": {"x": 0, "y": 0},
        "b": {"x": 10, "y": 0},
        "c": {"x": 20, "y": 0},
    }
    path = ["a", "b", "c"]

    idx = nearest_route_index(path, nodes, x=9, y=0, start_index=0)
    assert idx == 1

    remaining = remaining_distance_metres(path, nodes, px_per_metre=10.0, start_index=1)
    assert remaining == 1.0

    eta = estimate_eta_seconds(remaining, speed_mps=1.0)
    assert eta == 1


def test_off_route_and_auto_advance() -> None:
    nodes = {
        "a": {"x": 0, "y": 0},
        "b": {"x": 10, "y": 0},
        "c": {"x": 20, "y": 0},
    }
    path = ["a", "b", "c"]

    off_route, deviation = is_off_route(
        path,
        nodes,
        x=10,
        y=0,
        px_per_metre=10.0,
        max_deviation_metres=0.5,
    )
    assert off_route is False
    assert deviation == 0.0

    advanced = auto_advance_step_index(
        path,
        nodes,
        x=10,
        y=0,
        px_per_metre=10.0,
        current_index=1,
        arrival_threshold_metres=0.5,
    )
    assert advanced == 2
