"""
Configuration constants for Mall Navigator.

Centralized configuration for floors, colors, UI settings, and stores.
"""

import json
import os

from utils.env_config import load_env_file


load_env_file()

# ────────────────────────────────────────────────────────────────────────────
# Streamlit Page Configuration
# ────────────────────────────────────────────────────────────────────────────

PAGE_TITLE = "Mall Navigator"
PAGE_ICON = "🗺️"
PAGE_LAYOUT = "wide"
INITIAL_SIDEBAR_STATE = "expanded"


# ────────────────────────────────────────────────────────────────────────────
# Floor Configuration
# ────────────────────────────────────────────────────────────────────────────

FLOORS = {
    0: {
        "name": "Lower Ground",
        "map": "data/maps/lower.png",
        "graph": "data/graphs/lower.json",
    },
    1: {
        "name": "Ground Floor",
        "map": "data/maps/ground.png",
        "graph": "data/graphs/ground.json",
    },
    2: {
        "name": "Upper Floor",
        "map": "data/maps/upper.png",
        "graph": "data/graphs/upper.json",
    },
}

FLOOR_NAMES = {k: v["name"] for k, v in FLOORS.items()}

# Inter-floor transition edges (stairs/escalators).
# Format: (floor_a, node_a, floor_b, node_b, cost_in_pixels)
INTER_FLOOR_EDGES = [
    (0, "stairs_to_ground", 1, "stairs_to_lower", 200),
    (1, "stairs_to_upper", 2, "stairs_from_ground", 200),
]


# ────────────────────────────────────────────────────────────────────────────
# Colors for Map Rendering
# ────────────────────────────────────────────────────────────────────────────

# RGB tuples for path and marker visualization
COLOR_START = (0, 180, 80)  # Green
COLOR_END = (220, 40, 40)  # Red
COLOR_PATH_DIJKSTRA = (255, 140, 0)  # Orange
COLOR_PATH_ASTAR = (30, 120, 255)  # Blue
COLOR_WAYPOINT = (80, 80, 200)  # Light blue
COLOR_PRODUCT = (200, 60, 200)  # Magenta
COLOR_TEXT = (30, 30, 30)  # Dark gray
COLOR_OUTLINE = (255, 255, 255)  # White


# ────────────────────────────────────────────────────────────────────────────
# Drawing Parameters
# ────────────────────────────────────────────────────────────────────────────

# Marker sizes (pixels)
MARKER_START_END_RADIUS = 12
MARKER_WAYPOINT_RADIUS = 5
MARKER_PRODUCT_RADIUS = 9
MARKER_PATH_ENDPOINT_RADIUS = 4

# Path drawing
PATH_LINE_WIDTH_BACKGROUND = 14
PATH_LINE_WIDTH_FOREGROUND = 5
PATH_BACKGROUND_ALPHA = 60
PATH_FOREGROUND_ALPHA = 230

# Outline and border
OUTLINE_WIDTH_SHORT = 1  # Thin line for small elements
OUTLINE_WIDTH_THIN = 1
OUTLINE_WIDTH_DEFAULT = 2
OUTLINE_WIDTH_THICK = 3

# Transparency/alpha values
ALPHA_WAYPOINT_BG = 160
ALPHA_WAYPOINT_OUTLINE = 200
ALPHA_PRODUCT_BG = 210
ALPHA_PRODUCT_OUTLINE = 220
ALPHA_START_END = 240

# Text/label sizing
LABEL_SIZE_DEFAULT = 11
LABEL_SIZE_MARKER = 10
LABEL_SIZE_START_END = 9
LABEL_SIZE_HEADER = 13
LABEL_SIZE_WAYPOINT = 8

# Label offsets
LABEL_OFFSET_NODE_ABOVE = 12
LABEL_OFFSET_PRODUCT_BELOW = 18
LABEL_OFFSET_MARKER_ABOVE = 24

# Node type filters for visualization
WAYPOINT_TYPES = ("corridor", "stairs", "entrance", "service")


# ────────────────────────────────────────────────────────────────────────────
# Store Configuration
# ────────────────────────────────────────────────────────────────────────────

_STORES_FALLBACK = {
    "asda_old_kent_road": {
        "name": "Asda Superstore - Old Kent Road",
        "lat": 51.4884,
        "lng": -0.0669,
        "graph_dir": "data/graphs",
        "map_dir": "data/maps",
    },
    "sainsburys_whitechapel": {
        "name": "Sainsbury's - Whitechapel",
        "lat": 51.5153,
        "lng": -0.0668,
        "graph_dir": "data/graphs",
        "map_dir": "data/maps",
    },
    "demo": {
        "name": "Demo Mall (any location)",
        "lat": 0.0,
        "lng": 0.0,
        "graph_dir": "data/graphs",
        "map_dir": "data/maps",
    },
}


def _load_stores() -> dict:
    base_dir = os.path.dirname(__file__)
    stores_path = os.path.join(base_dir, "data", "stores.json")
    if not os.path.exists(stores_path):
        return _STORES_FALLBACK
    try:
        with open(stores_path, encoding="utf-8") as f:
            loaded = json.load(f)
        if isinstance(loaded, dict) and loaded:
            return loaded
    except (json.JSONDecodeError, OSError):
        pass
    return _STORES_FALLBACK


STORES = _load_stores()

# GPS verification threshold (metres)
STORE_RADIUS_M = 500


# ────────────────────────────────────────────────────────────────────────────
# Session State Defaults
# ────────────────────────────────────────────────────────────────────────────

DEFAULT_FLOOR = 1  # Ground Floor
DEFAULT_MODE = "navigate"  # "navigate", "add_product", "outdoor"
DEFAULT_PX_PER_METRE = 10.0  # Approximate scale calibration

# Available modes and their display labels
MODES = {
    "navigate": "🧭 Navigate",
    "add_product": "📌 Add Product",
    "outdoor": "🌍 Outdoor Map",
}


# ────────────────────────────────────────────────────────────────────────────
# Product Manager Configuration
# ────────────────────────────────────────────────────────────────────────────

PRODUCTS_FILE = "data/products.json"
PRODUCTS_DB_FILE = "data/products.db"
PRODUCT_SEARCH_RESULTS_LIMIT = 6


# ────────────────────────────────────────────────────────────────────────────
# File Paths
# ────────────────────────────────────────────────────────────────────────────

DATA_DIR = "data"
MAPS_DIR = "data/maps"
GRAPHS_DIR = "data/graphs"


# ────────────────────────────────────────────────────────────────────────────
# UI Settings
# ────────────────────────────────────────────────────────────────────────────

# Font names to try (in order of preference)
FONT_NAMES = ("DejaVuSans-Bold.ttf", "Arial.ttf")

# Slider ranges for settings
PX_PER_METRE_MIN = 5.0
PX_PER_METRE_MAX = 30.0
PX_PER_METRE_STEP = 0.5
