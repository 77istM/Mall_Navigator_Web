"""UX utility functions for better user experience.

Provides helpers for formatting output, displaying errors, and managing
user interactions in a more user-friendly way.
"""
import math
from typing import Optional


def format_distance_summary(
    dijkstra_result: dict,
    astar_result: dict,
    px_per_metre: float = 10.0,
) -> str:
    """Format a brief summary of both algorithm results.
    
    Returns a formatted string with distance and comparison info.
    """
    if not dijkstra_result["found"] or not astar_result["found"]:
        return "❌ **No path found** — Try a different start/end location."
    
    cost = dijkstra_result["cost"]
    dist_m = cost / px_per_metre
    
    # Both should be same cost, show which is faster
    dijk_time = dijkstra_result["time_us"]
    astar_time = astar_result["time_us"]
    faster = "A*" if astar_time < dijk_time else "Dijkstra"
    
    return (
        f"✅ **Path found!**\n\n"
        f"📏 **Distance:** {dist_m:.1f} metres (~{cost:.0f} pixels)\n\n"
        f"⚡ **Faster algorithm:** {faster} "
        f"({min(dijk_time, astar_time):.1f} µs)"
    )


def get_error_message(result: dict) -> Optional[str]:
    """Return a helpful error message for a failed pathfinding result."""
    if not result:
        return "❌ No path information available."
    
    if not result.get("found"):
        return (
            "❌ **Path not found** — The start and end locations may be "
            "on a disconnected part of the graph. Try clicking on a different area."
        )
    
    if result.get("cost") == math.inf:
        return (
            "❌ **Unreachable destination** — There may be locked doors or "
            "restricted areas blocking the path."
        )
    
    return None


def format_node_info(node_label: str, floor_name: str) -> str:
    """Format a node's display information."""
    return f"{node_label} — {floor_name}"


def format_path_info(
    start_label: str,
    end_label: str,
    start_floor: str,
    end_floor: str,
    multi_floor: bool,
) -> str:
    """Format a readable path description."""
    if multi_floor:
        return (
            f"🟢 {start_label} ({start_floor}) "
            f"→ 🔴 {end_label} ({end_floor})"
        )
    else:
        return f"🟢 {start_label} → 🔴 {end_label}"


def get_instruction_message(state: str) -> str:
    """Get the current instruction message based on selection state."""
    instructions = {
        "start": "👆 Click on the map to set your **START** location",
        "end": "👆 Click on the map to set your **DESTINATION** location",
        "done": "✅ Both locations set! Analyzing paths...",
    }
    return instructions.get(state, "")
