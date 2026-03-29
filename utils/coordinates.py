"""Geometric helpers: distances, bearings, pixel↔scale conversions."""
import math


# ---------------------------------------------------------------------------
# Distance helpers
# ---------------------------------------------------------------------------

def euclidean(x1: float, y1: float, x2: float, y2: float) -> float:
    """Pixel Euclidean distance."""
    return math.hypot(x2 - x1, y2 - y1)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres between two lat/lng points."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Nearest node lookup
# ---------------------------------------------------------------------------

def nearest_node(px: float, py: float, nodes: dict) -> str:
    """Return the node_id whose pixel coordinates are closest to (px, py)."""
    return min(nodes, key=lambda n: euclidean(px, py, nodes[n]["x"], nodes[n]["y"]))


# ---------------------------------------------------------------------------
# Bearing / cardinal direction
# ---------------------------------------------------------------------------

def bearing_degrees(x1: float, y1: float, x2: float, y2: float) -> float:
    """
    Compass bearing (degrees, 0 = up/north on map) from point 1 to point 2.
    y-axis is *inverted* on screen: smaller y means higher on screen (= north).
    """
    dx = x2 - x1
    dy = y1 - y2  # invert y so "up" = north
    return (math.degrees(math.atan2(dx, dy)) + 360) % 360


def bearing_to_cardinal(deg: float) -> str:
    """Convert a bearing in degrees to an 8-point cardinal direction string."""
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((deg + 22.5) / 45) % 8
    full = {
        "N": "North", "NE": "North-East", "E": "East", "SE": "South-East",
        "S": "South", "SW": "South-West", "W": "West", "NW": "North-West",
    }
    return full[dirs[idx]]


# ---------------------------------------------------------------------------
# Walking-time estimate
# ---------------------------------------------------------------------------

def walking_time_str(pixel_dist: float, px_per_metre: float = 10.0,
                     speed_ms: float = 1.2) -> str:
    """
    Convert pixel distance to an estimated walking-time string.

    Parameters
    ----------
    pixel_dist   : path length in pixels
    px_per_metre : calibration factor (pixels per real-world metre).
                   Default 10 px/m is a rough approximation; refine by
                   comparing a known corridor length on the floor plan.
    speed_ms     : walking speed in m/s (default 1.2 m/s ≈ average walk).
    """
    metres = pixel_dist / px_per_metre
    seconds = metres / speed_ms
    if seconds < 60:
        return f"{int(seconds)}s"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins}m {secs}s"


def metres_str(pixel_dist: float, px_per_metre: float = 10.0) -> str:
    """Return a human-readable distance string from a pixel distance."""
    metres = pixel_dist / px_per_metre
    if metres < 1000:
        return f"{metres:.0f} m"
    return f"{metres / 1000:.2f} km"
