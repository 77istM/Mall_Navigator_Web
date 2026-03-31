"""Floor-plan map component.

Renders the floor-plan PNG as an interactive image and draws the shortest path
on top of it. Returns any click event so the caller can update start/end nodes.
"""
import io
import math
from PIL import Image, ImageDraw, ImageFont

from utils.coordinates import nearest_node, bearing_degrees, bearing_to_cardinal
from config import (
    FONT_NAMES, LABEL_SIZE_DEFAULT, LABEL_SIZE_MARKER, LABEL_SIZE_START_END,
    LABEL_SIZE_WAYPOINT, LABEL_OFFSET_NODE_ABOVE, LABEL_OFFSET_PRODUCT_BELOW,
    LABEL_OFFSET_MARKER_ABOVE, WAYPOINT_TYPES, OUTLINE_WIDTH_DEFAULT,
    OUTLINE_WIDTH_THICK, OUTLINE_WIDTH_THIN, MARKER_START_END_RADIUS, MARKER_WAYPOINT_RADIUS,
    MARKER_PRODUCT_RADIUS, MARKER_PATH_ENDPOINT_RADIUS, PATH_LINE_WIDTH_BACKGROUND,
    PATH_LINE_WIDTH_FOREGROUND, COLOR_START, COLOR_END, COLOR_PATH_DIJKSTRA,
    COLOR_PATH_ASTAR, COLOR_WAYPOINT, COLOR_PRODUCT, COLOR_TEXT, COLOR_OUTLINE,
    ALPHA_WAYPOINT_BG, ALPHA_WAYPOINT_OUTLINE, ALPHA_PRODUCT_BG,
    ALPHA_PRODUCT_OUTLINE, ALPHA_START_END, PATH_BACKGROUND_ALPHA,
    PATH_FOREGROUND_ALPHA,
)


def _try_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for name in FONT_NAMES:
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


# ── helper drawing functions ─────────────────────────────────────────────────

def _circle(draw: ImageDraw.Draw, cx: float, cy: float, r: float, fill: tuple, outline: tuple = COLOR_OUTLINE, w: int = OUTLINE_WIDTH_DEFAULT) -> None:
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)],
                 fill=fill, outline=outline, width=w)


def _label(draw: ImageDraw.Draw, cx: float, cy: float, text: str, size: int = LABEL_SIZE_DEFAULT, colour: tuple = COLOR_TEXT) -> None:
    font = _try_font(size)
    draw.text((cx, cy), text, fill=colour, font=font, anchor="mm")


def _draw_path_line(draw: ImageDraw.Draw, pixels: list[tuple], colour: tuple, width: int = PATH_LINE_WIDTH_FOREGROUND) -> None:
    if len(pixels) >= 2:
        draw.line(pixels, fill=colour, width=width, joint="curve")
    for px, py in pixels:
        _circle(draw, px, py, MARKER_PATH_ENDPOINT_RADIUS, colour)


# ── public API ───────────────────────────────────────────────────────────────

def render_floor_map(
    image_path: str,
    nodes: dict[str, dict],
    *,
    start_node: str | None = None,
    end_node: str | None = None,
    dijkstra_path: list[str] | None = None,
    astar_path: list[str] | None = None,
    products: dict[str, dict] | None = None,
    show_waypoints: bool = False,
) -> Image.Image:
    """
    Return a PIL Image with overlays for:
      - start / end markers
      - Dijkstra path (orange)
      - A* path (blue)
      - product cache markers (purple)
      - optional waypoint dots

    Parameters
    ----------
    image_path      : absolute path to the floor-plan PNG
    nodes           : node dict from the floor's graph JSON
    start_node      : selected start node id (or None)
    end_node        : selected end node id (or None)
    dijkstra_path   : list of node ids from Dijkstra result
    astar_path      : list of node ids from A* result
    products        : product cache dict (filtered to this floor)
    show_waypoints  : draw small dots at every waypoint
    """
    img = Image.open(image_path).convert("RGB")
    
    # ── resize image to fit screen ────────────────────────────────────────────
    # Max dimensions to ensure image fits on one screen (leaving room for UI)
    max_width, max_height = 1200, 900
    orig_width, orig_height = img.size
    
    # Calculate scale factor to fit within max dimensions
    scale_w = max_width / orig_width if orig_width > max_width else 1.0
    scale_h = max_height / orig_height if orig_height > max_height else 1.0
    scale = min(scale_w, scale_h, 1.0)  # Don't upscale if image is already small
    
    if scale < 1.0:
        new_width = int(orig_width * scale)
        new_height = int(orig_height * scale)
        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    else:
        scale = 1.0
    
    draw = ImageDraw.Draw(img, "RGBA")
    
    # Helper function to scale coordinates
    def scale_coord(val):
        return val * scale

    def node_px(nid):
        return (int(scale_coord(nodes[nid]["x"])), int(scale_coord(nodes[nid]["y"])))

    # ── optional: show all waypoints ────────────────────────────────────────
    if show_waypoints:
        for nid, nd in nodes.items():
            if nd["type"] in WAYPOINT_TYPES:
                scaled_x = scale_coord(nd["x"])
                scaled_y = scale_coord(nd["y"])
                _circle(draw, scaled_x, scaled_y, MARKER_WAYPOINT_RADIUS * scale, COLOR_WAYPOINT + (ALPHA_WAYPOINT_BG,),
                        outline=COLOR_OUTLINE + (ALPHA_WAYPOINT_OUTLINE,), w=OUTLINE_WIDTH_THIN)
                _label(draw, scaled_x, scaled_y - LABEL_OFFSET_NODE_ABOVE * scale, nid.split("_")[0][:6],
                       size=max(int(LABEL_SIZE_WAYPOINT * scale), 8), colour=COLOR_WAYPOINT)

    # ── product markers ──────────────────────────────────────────────────────
    if products:
        for name, info in products.items():
            px = int(scale_coord(info["x"]))
            py = int(scale_coord(info["y"]))
            _circle(draw, px, py, MARKER_PRODUCT_RADIUS * scale, COLOR_PRODUCT + (ALPHA_PRODUCT_BG,),
                    outline=COLOR_OUTLINE + (ALPHA_PRODUCT_OUTLINE,), w=OUTLINE_WIDTH_DEFAULT)
            _label(draw, px, py + LABEL_OFFSET_PRODUCT_BELOW * scale, name[:12], size=max(int(LABEL_SIZE_MARKER * scale), 8), colour=COLOR_PRODUCT)

    # ── paths ────────────────────────────────────────────────────────────────
    if dijkstra_path:
        px_list = [node_px(n) for n in dijkstra_path if n in nodes]
        if len(px_list) >= 2:
            # semi-transparent background line
            draw.line(px_list, fill=COLOR_PATH_DIJKSTRA + (PATH_BACKGROUND_ALPHA,), width=max(int(PATH_LINE_WIDTH_BACKGROUND * scale), 1), joint="curve")
            draw.line(px_list, fill=COLOR_PATH_DIJKSTRA + (PATH_FOREGROUND_ALPHA,), width=max(int(PATH_LINE_WIDTH_FOREGROUND * scale), 1), joint="curve")

    if astar_path:
        px_list = [node_px(n) for n in astar_path if n in nodes]
        if len(px_list) >= 2:
            draw.line(px_list, fill=COLOR_PATH_ASTAR + (PATH_BACKGROUND_ALPHA,), width=max(int(PATH_LINE_WIDTH_BACKGROUND * scale), 1), joint="curve")
            draw.line(px_list, fill=COLOR_PATH_ASTAR + (PATH_FOREGROUND_ALPHA,), width=max(int(PATH_LINE_WIDTH_FOREGROUND * scale), 1), joint="curve")

    # ── start / end markers ──────────────────────────────────────────────────
    if start_node and start_node in nodes:
        sx, sy = node_px(start_node)
        _circle(draw, sx, sy, MARKER_START_END_RADIUS * scale, COLOR_START + (ALPHA_START_END,), w=max(int(OUTLINE_WIDTH_THICK * scale), 1))
        _label(draw, sx, sy, "S", size=max(int((LABEL_SIZE_START_END + 4) * scale), 8), colour=COLOR_OUTLINE)
        _label(draw, sx, sy - LABEL_OFFSET_MARKER_ABOVE * scale, nodes[start_node]["label"][:18],
               size=max(int(LABEL_SIZE_START_END * scale), 8), colour=COLOR_START)

    if end_node and end_node in nodes:
        ex, ey = node_px(end_node)
        _circle(draw, ex, ey, MARKER_START_END_RADIUS * scale, COLOR_END + (ALPHA_START_END,), w=max(int(OUTLINE_WIDTH_THICK * scale), 1))
        _label(draw, ex, ey, "E", size=max(int((LABEL_SIZE_START_END + 4) * scale), 8), colour=COLOR_OUTLINE)
        _label(draw, ex, ey - LABEL_OFFSET_MARKER_ABOVE * scale, nodes[end_node]["label"][:18],
               size=max(int(LABEL_SIZE_START_END * scale), 8), colour=COLOR_END)

    return img


def path_pixel_list(path: list[str], nodes: dict[str, dict]) -> list[tuple[int, int]]:
    """Return (x, y) tuples for all nodes in *path* that exist in *nodes*."""
    return [(int(nodes[n]["x"]), int(nodes[n]["y"]))
            for n in path if n in nodes]


def generate_directions(
    path: list[str],
    nodes: dict[str, dict],
    px_per_metre: float = 10.0,
) -> list[dict[str, str | float | bool]]:
    """
    Generate a list of step dicts for the directions panel.

    Each step dict has:
        from_label  : str
        to_label    : str
        direction   : str  (e.g. "North", "South-East")
        dist_px     : float
        dist_m      : float
        is_stairs   : bool
    """
    steps = []
    for i in range(len(path) - 1):
        cur, nxt = path[i], path[i + 1]
        if cur not in nodes or nxt not in nodes:
            continue
        x1, y1 = nodes[cur]["x"], nodes[cur]["y"]
        x2, y2 = nodes[nxt]["x"], nodes[nxt]["y"]
        dist_px = math.hypot(x2 - x1, y2 - y1)
        dist_m  = dist_px / px_per_metre
        steps.append({
            "from_label": nodes[cur]["label"],
            "to_label":   nodes[nxt]["label"],
            "direction":  bearing_to_cardinal(bearing_degrees(x1, y1, x2, y2)),
            "dist_px":    round(dist_px, 1),
            "dist_m":     round(dist_m, 1),
            "is_stairs":  nodes[nxt]["type"] == "stairs",
        })
    return steps
