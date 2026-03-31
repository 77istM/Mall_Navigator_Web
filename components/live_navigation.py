"""Live navigation UI helpers for Phase 3 MVP."""

from __future__ import annotations

from typing import Any

import streamlit as st
import streamlit.components.v1 as st_components

from utils.location_tracking import (
    LocationTracker,
    auto_advance_step_index,
    estimate_eta_seconds,
    is_off_route,
    remaining_distance_metres,
)


def init_live_navigation_state() -> None:
    """Initialize session-state fields required by live navigation."""
    defaults: dict[str, Any] = {
        "live_nav_enabled": False,
        "live_nav_consent": False,
        "live_nav_capture_click": False,
        "live_nav_audio_enabled": False,
        "live_nav_user_id": "default",
        "live_nav_current_floor": None,
        "live_nav_current_x": None,
        "live_nav_current_y": None,
        "live_nav_current_node": None,
        "live_nav_step_index": 0,
        "live_nav_last_spoken": "",
        "live_nav_speed_mps": 1.2,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def update_live_position(
    *,
    tracker: LocationTracker,
    floor: int,
    x: float,
    y: float,
    nodes: dict[str, dict[str, Any]],
    source: str,
) -> None:
    """Update current live position and optionally persist if consent was granted."""
    node_id = min(
        nodes,
        key=lambda nid: ((float(nodes[nid]["x"]) - float(x)) ** 2 + (float(nodes[nid]["y"]) - float(y)) ** 2),
    )

    st.session_state.live_nav_current_floor = floor
    st.session_state.live_nav_current_x = float(x)
    st.session_state.live_nav_current_y = float(y)
    st.session_state.live_nav_current_node = node_id

    tracker.record_position(
        user_id=st.session_state.live_nav_user_id,
        floor=floor,
        x=x,
        y=y,
        nodes=nodes,
        source=source,
        consent=bool(st.session_state.live_nav_consent),
    )


def _speak(text: str, *, html_key: str) -> None:
    """Trigger browser speech synthesis for the given text."""
    escaped = text.replace("\\", "\\\\").replace("\"", "\\\"")
    st_components.html(
        f"""
        <script>
        (function() {{
            const utterance = new SpeechSynthesisUtterance(\"{escaped}\");
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(utterance);
        }})();
        </script>
        """,
        height=0,
        key=html_key,
    )


def render_live_navigation_panel(
    *,
    tracker: LocationTracker,
    floor: int,
    nodes: dict[str, dict[str, Any]],
    path: list[str],
    steps: list[dict[str, Any]],
    px_per_metre: float,
) -> None:
    """Render live navigation controls and status for the current floor path."""
    st.subheader("📡 Live Navigation (MVP)")

    st.session_state.live_nav_enabled = st.toggle(
        "Enable live navigation",
        value=bool(st.session_state.live_nav_enabled),
    )

    if not st.session_state.live_nav_enabled:
        st.caption("Enable this to track your position and get live turn-by-turn updates.")
        st.session_state.live_nav_capture_click = False
        return

    c1, c2 = st.columns(2)
    with c1:
        st.session_state.live_nav_consent = st.checkbox(
            "I consent to storing location history",
            value=bool(st.session_state.live_nav_consent),
            help="History is saved in data/location_history.json only when consent is enabled.",
        )
    with c2:
        st.session_state.live_nav_audio_enabled = st.checkbox(
            "Audio directions",
            value=bool(st.session_state.live_nav_audio_enabled),
        )

    st.session_state.live_nav_capture_click = st.checkbox(
        "Use map clicks to update current position",
        value=bool(st.session_state.live_nav_capture_click),
        help="When enabled, clicking the map updates live position instead of selecting start/end.",
    )

    speed = st.slider(
        "Walking speed (m/s)",
        min_value=0.6,
        max_value=2.2,
        value=float(st.session_state.live_nav_speed_mps),
        step=0.1,
    )
    st.session_state.live_nav_speed_mps = float(speed)

    mx = float(st.session_state.live_nav_current_x) if st.session_state.live_nav_current_x is not None else 0.0
    my = float(st.session_state.live_nav_current_y) if st.session_state.live_nav_current_y is not None else 0.0

    i1, i2, i3 = st.columns([1, 1, 1])
    with i1:
        manual_x = st.number_input("Manual X", min_value=0.0, value=mx, step=1.0)
    with i2:
        manual_y = st.number_input("Manual Y", min_value=0.0, value=my, step=1.0)
    with i3:
        do_update = st.button("Update position", use_container_width=True)

    if do_update:
        update_live_position(
            tracker=tracker,
            floor=floor,
            x=manual_x,
            y=manual_y,
            nodes=nodes,
            source="manual_button",
        )

    if not path:
        st.info("Compute a route first to start turn-by-turn guidance.")
        return

    if st.session_state.live_nav_current_x is None or st.session_state.live_nav_current_y is None:
        st.info("Set your current position using the update button or map clicks.")
        return

    current_x = float(st.session_state.live_nav_current_x)
    current_y = float(st.session_state.live_nav_current_y)

    old_step = int(st.session_state.live_nav_step_index)
    step_idx = auto_advance_step_index(
        path,
        nodes,
        x=current_x,
        y=current_y,
        px_per_metre=px_per_metre,
        current_index=old_step,
    )
    st.session_state.live_nav_step_index = step_idx

    off_route, deviation_m = is_off_route(
        path,
        nodes,
        x=current_x,
        y=current_y,
        px_per_metre=px_per_metre,
        start_index=step_idx,
    )

    remaining_m = remaining_distance_metres(
        path,
        nodes,
        px_per_metre=px_per_metre,
        start_index=step_idx,
    )
    eta_seconds = estimate_eta_seconds(
        remaining_m,
        speed_mps=float(st.session_state.live_nav_speed_mps),
    )

    m1, m2, m3 = st.columns(3)
    m1.metric("Current waypoint", f"{step_idx + 1}/{max(len(path), 1)}")
    m2.metric("Remaining distance", f"{remaining_m:.1f} m")
    m3.metric("Live ETA", f"{eta_seconds} sec")

    if off_route:
        st.warning(f"Off-route detected: you are about {deviation_m:.1f} m from the nearest route waypoint.")
    else:
        st.success(f"On route: nearest waypoint is {deviation_m:.1f} m away.")

    if steps:
        st.markdown("**Turn-by-turn (live):**")
        for idx, step in enumerate(steps):
            prefix = "▶" if idx == min(step_idx, len(steps) - 1) else "•"
            st.write(f"{prefix} {idx + 1}. {step['direction']} to {step['to_label']} ({step['dist_m']} m)")

        if st.session_state.live_nav_audio_enabled and step_idx != old_step:
            audio_idx = min(step_idx, len(steps) - 1)
            text = f"Next: head {steps[audio_idx]['direction']} toward {steps[audio_idx]['to_label']}"
            if text != st.session_state.live_nav_last_spoken:
                _speak(text, html_key=f"tts_step_{audio_idx}")
                st.session_state.live_nav_last_spoken = text

    with st.expander("Location history", expanded=False):
        history = tracker.history_for(st.session_state.live_nav_user_id)
        if not history:
            st.caption("No saved positions yet.")
        else:
            for item in history[-10:][::-1]:
                st.caption(
                    f"{item['timestamp']} | floor {item['floor']} | "
                    f"({item['x']:.0f}, {item['y']:.0f}) | {item['source']}"
                )
