"""Floor-plan map component.

Renders the floor-plan PNG as an interactive image and draws the shortest path
on top of it. Returns any click event so the caller can update start/end nodes.
"""
import io
import math
from PIL import Image, ImageDraw, ImageFont

from utils.coordinates import nearest_node, bearing_degrees, bearing_to_cardinal

# ── colour constants ─────────────────────────────────────────────────────────
_COL_START     = (0,   180,  80)
_COL_END       = (220,  40,  40)
_COL_PATH_DIJ  = (255, 140,   0)   # orange  – Dijkstra
_COL_PATH_STAR = (30,  120, 255)   # blue    – A*
_COL_WAYPOINT  = (80,   80, 200)
_COL_PRODUCT   = (200,  60, 200)


def _try_font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


# ── helper drawing functions ─────────────────────────────────────────────────

def _circle(draw: ImageDraw.Draw, cx, cy, r, fill, outline=(255, 255, 255), w=2):
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)],
                 fill=fill, outline=outline, width=w)


def _label(draw: ImageDraw.Draw, cx, cy, text, size=11, colour=(30, 30, 30)):
    font = _try_font(size)
    draw.text((cx, cy), text, fill=colour, font=font, anchor="mm")


def _draw_path_line(draw: ImageDraw.Draw, pixels: list[tuple],
                    colour: tuple, width: int = 5):
    if len(pixels) >= 2:
        draw.line(pixels, fill=colour, width=width, joint="curve")
    for px, py in pixels:
        _circle(draw, px, py, 4, colour)


# ── public API ───────────────────────────────────────────────────────────────

def render_floor_map(
    image_path: str,
    nodes: dict,
    *,
    start_node: str | None = None,
    end_node: str | None = None,
    dijkstra_path: list[str] | None = None,
    astar_path: list[str] | None = None,
    products: dict | None = None,
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
    draw = ImageDraw.Draw(img, "RGBA")

    def node_px(nid):
        return (int(nodes[nid]["x"]), int(nodes[nid]["y"]))

    # ── optional: show all waypoints ────────────────────────────────────────
    if show_waypoints:
        for nid, nd in nodes.items():
            if nd["type"] in ("corridor", "stairs", "entrance", "service"):
                _circle(draw, nd["x"], nd["y"], 5, _COL_WAYPOINT + (160,),
                        outline=(255, 255, 255, 200), w=1)
                _label(draw, nd["x"], nd["y"] - 12, nid.split("_")[0][:6],
                       size=8, colour=_COL_WAYPOINT)

    # ── product markers ──────────────────────────────────────────────────────
    if products:
        for name, info in products.items():
            px, py = int(info["x"]), int(info["y"])
            _circle(draw, px, py, 9, _COL_PRODUCT + (210,),
                    outline=(255, 255, 255, 220), w=2)
            _label(draw, px, py + 18, name[:12], size=10, colour=_COL_PRODUCT)

    # ── paths ────────────────────────────────────────────────────────────────
    if dijkstra_path:
        px_list = [node_px(n) for n in dijkstra_path if n in nodes]
        if len(px_list) >= 2:
            # semi-transparent background line
            draw.line(px_list, fill=_COL_PATH_DIJ + (60,), width=14, joint="curve")
            draw.line(px_list, fill=_COL_PATH_DIJ + (230,), width=5, joint="curve")

    if astar_path:
        px_list = [node_px(n) for n in astar_path if n in nodes]
        if len(px_list) >= 2:
            draw.line(px_list, fill=_COL_PATH_STAR + (60,), width=14, joint="curve")
            draw.line(px_list, fill=_COL_PATH_STAR + (230,), width=5, joint="curve")

    # ── start / end markers ──────────────────────────────────────────────────
    if start_node and start_node in nodes:
        sx, sy = node_px(start_node)
        _circle(draw, sx, sy, 12, _COL_START + (240,), w=3)
        _label(draw, sx, sy, "S", size=13, colour=(255, 255, 255))
        _label(draw, sx, sy - 24, nodes[start_node]["label"][:18],
               size=9, colour=_COL_START)

    if end_node and end_node in nodes:
        ex, ey = node_px(end_node)
        _circle(draw, ex, ey, 12, _COL_END + (240,), w=3)
        _label(draw, ex, ey, "E", size=13, colour=(255, 255, 255))
        _label(draw, ex, ey - 24, nodes[end_node]["label"][:18],
               size=9, colour=_COL_END)

    return img


def path_pixel_list(path: list[str], nodes: dict) -> list[tuple]:
    """Return (x, y) tuples for all nodes in *path* that exist in *nodes*."""
    return [(int(nodes[n]["x"]), int(nodes[n]["y"]))
            for n in path if n in nodes]


def generate_directions(
    path: list[str],
    nodes: dict,
    px_per_metre: float = 10.0,
) -> list[dict]:
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
