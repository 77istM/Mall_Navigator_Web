"""Directions panel + algorithm comparison component.

Renders:
  1. Step-by-step human-readable directions
  2. Side-by-side Dijkstra vs A* statistics table
"""
import math
import streamlit as st

from utils.coordinates import walking_time_str, metres_str

# Scale: approximate pixels per real-world metre.
# Without measured floor-plan dimensions this is a rough estimate.
# Users can override via the sidebar slider.
DEFAULT_PX_PER_M = 10.0


def render_comparison(
    dijk_result: dict,
    astar_result: dict,
    px_per_metre: float = DEFAULT_PX_PER_M,
) -> None:
    """
    Show a two-column educational comparison of Dijkstra vs A*.

    Parameters
    ----------
    dijk_result  : result dict from algorithms.dijkstra.dijkstra()
    astar_result : result dict from algorithms.astar.astar()
    px_per_metre : scale factor for converting pixel distances to metres
    """
    st.subheader("🔬 Algorithm Comparison")

    col1, col2 = st.columns(2)

    def _render_algo(col, label: str, colour: str, result: dict):
        with col:
            st.markdown(f"### {label}")
            if not result["found"]:
                st.error("No path found")
                return

            dist_m = result["cost"] / px_per_metre
            st.metric("Distance", metres_str(result["cost"], px_per_metre))
            st.metric("Est. walking time",
                      walking_time_str(result["cost"], px_per_metre))
            st.metric("Nodes explored", result["nodes_visited"])
            st.metric("Algorithm time", f"{result['time_us']:.1f} µs")
            steps = len(result["path"]) - 1 if result["path"] else 0
            st.metric("Path steps", steps)

    _render_algo(col1, "🟠 Dijkstra", "#FF8C00", dijk_result)
    _render_algo(col2, "🔵 A\u002a", "#1E78FF", astar_result)

    # ── explanation ──────────────────────────────────────────────────────────
    with st.expander("ℹ️ Why are the paths the same cost but different speeds?"):
        st.markdown(
            """
**Dijkstra** explores nodes in order of total cost from the start, with no
knowledge of the goal's location. It visits every node within cost *d* before
any node at cost *d+1*.

**A&#42;** adds a *heuristic h(n)* — the straight-line (Euclidean) distance from
node *n* to the goal. This lets it prioritise nodes that are physically closer
to the goal, so it usually visits fewer nodes before finding the optimal path.

Both algorithms are **guaranteed to find the shortest path** (A&#42; is optimal
when h(n) never overestimates the true cost — which is satisfied here because
edge weights are Euclidean distances and h(n) is also Euclidean).

**When do results differ?**  
In a small graph (few nodes) both algorithms are equally fast and find the same
path. On larger graphs with many junctions, A&#42; can be 2–10x faster because it
explores far fewer nodes.
            """
        )


def render_directions(
    steps: list[dict],
    path: list[str],
    nodes: dict,
    px_per_metre: float = DEFAULT_PX_PER_M,
) -> None:
    """
    Render step-by-step textual directions.

    Parameters
    ----------
    steps        : output of components.map_view.generate_directions()
    path         : full node-id path list
    nodes        : node dict from graph JSON (used for labels)
    px_per_metre : scale factor
    """
    if not steps:
        st.info("Select a start and end point to see directions.")
        return

    total_px = sum(s["dist_px"] for s in steps)

    st.subheader("🗺️ Directions")
    st.caption(
        f"Total distance ≈ {metres_str(total_px, px_per_metre)}  •  "
        f"Est. time ≈ {walking_time_str(total_px, px_per_metre)}"
    )

    icons = {
        "North": "⬆️", "South": "⬇️", "East": "➡️", "West": "⬅️",
        "North-East": "↗️", "South-East": "↘️",
        "South-West": "↙️", "North-West": "↖️",
    }

    for i, step in enumerate(steps, start=1):
        icon = "🔼" if step["is_stairs"] else icons.get(step["direction"], "➡️")
        verb = "Take escalator / stairs to" if step["is_stairs"] else f"Head **{step['direction']}** toward"
        dist_txt = metres_str(step["dist_px"], px_per_metre)
        st.markdown(
            f"{i}. {icon} {verb} **{step['to_label']}** &nbsp; _{dist_txt}_"
        )

    st.success(f"✅ You have arrived at **{nodes[path[-1]]['label']}**.")
