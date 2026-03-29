"""
Generate PNG floor-plan images for the three mall floors.

Coordinates match the original A-level project's GIF images as closely as
possible.  The original tkinter window was 1200 × 1000 px; the Picture
widget occupied roughly 900 × 780 px of that, which is the canvas size used
here.  Store bounding boxes are taken directly from the PDF source code:

  lower_coordinates = [(65,146,294,588,"John Lewis LG"), (391,360,503,573,"H&M")]
  ground_coordinates= [(108,279,308,661,"John Lewis GF"), (340,300,416,408,"Apple")]
  upper_coordinates = [(502,169,609,289,"Nando's"),       (551,596,714,726,"Leon")]

Run this module directly to (re-)generate the images:
    python utils/generate_maps.py
"""

import math
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------------------
# Canvas size – matches the original GIF coordinate space
# ---------------------------------------------------------------------------
W, H = 900, 780

# Colour palette
COL_FLOOR      = (245, 240, 230)   # cream – walkable area
COL_WALL       = (80,  80,  80)    # dark grey – outer walls
COL_CORRIDOR   = (255, 255, 255)   # white – main corridor highlight
COL_STORE_A    = (173, 216, 230)   # light-blue  – anchor stores (John Lewis)
COL_STORE_B    = (255, 228, 196)   # bisque – mid-size stores
COL_STORE_C    = (198, 226, 200)   # sage-green – restaurants
COL_STORE_D    = (230, 190, 230)   # lavender – tech / brand stores
COL_BORDER     = (100, 100, 100)
COL_TEXT       = (30,  30,  30)
COL_TEXT_LIGHT = (255, 255, 255)
COL_STAIRS     = (255, 213, 100)   # amber – stairs / escalator
COL_ENTRY      = (100, 180, 100)   # green – entrance
COL_WAYPOINT   = (220,  60,  60)   # red – navigation waypoint dot


def _font(size: int):
    """Try to load a reasonable font; fall back to built-in."""
    for name in ("DejaVuSans-Bold.ttf", "Arial.ttf", "Helvetica.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except (IOError, OSError):
            pass
    return ImageFont.load_default()


def _draw_store(draw: ImageDraw.Draw, x1, y1, x2, y2, name, colour,
                font_size=13):
    """Draw a filled store block with a centred label."""
    draw.rectangle([(x1, y1), (x2, y2)], fill=colour, outline=COL_BORDER, width=2)
    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    font = _font(font_size)
    # wrap long names
    words = name.split()
    lines: list[str] = []
    current = ""
    for w in words:
        test = (current + " " + w).strip()
        if len(test) > 14:
            if current:
                lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)
    line_h = font_size + 4
    start_y = cy - (len(lines) * line_h) // 2
    for i, line in enumerate(lines):
        draw.text((cx, start_y + i * line_h), line, fill=COL_TEXT,
                  font=font, anchor="mm")


def _draw_stairs(draw: ImageDraw.Draw, x, y, label="Escalator"):
    """Draw an escalator/stairs symbol."""
    r = 18
    draw.ellipse([(x - r, y - r), (x + r, y + r)],
                 fill=COL_STAIRS, outline=COL_BORDER, width=2)
    font = _font(9)
    draw.text((x, y - 3), "⬆", fill=COL_TEXT, font=font, anchor="mm")
    draw.text((x, y + 9), label[:8], fill=COL_TEXT, font=_font(8), anchor="mm")


def _draw_entrance(draw: ImageDraw.Draw, x, y):
    draw.polygon([(x, y - 20), (x - 20, y + 15), (x + 20, y + 15)],
                 fill=COL_ENTRY, outline=COL_BORDER)
    draw.text((x, y + 28), "ENTRANCE", fill=COL_ENTRY, font=_font(10),
              anchor="mm")


def _base_image() -> tuple[Image.Image, ImageDraw.Draw]:
    img = Image.new("RGB", (W, H), COL_FLOOR)
    draw = ImageDraw.Draw(img)
    # outer wall border
    draw.rectangle([(2, 2), (W - 3, H - 3)], outline=COL_WALL, width=4)
    return img, draw


# ---------------------------------------------------------------------------
# Floor 0 – Lower Ground
# ---------------------------------------------------------------------------

def make_lower_ground() -> Image.Image:
    img, draw = _base_image()

    # Main central corridor (vertical strip)
    draw.rectangle([(310, 100), (390, 700)], fill=COL_CORRIDOR, outline=None)
    # Bottom horizontal corridor
    draw.rectangle([(50, 610), (870, 700)], fill=COL_CORRIDOR, outline=None)
    # East corridor
    draw.rectangle([(450, 100), (870, 600)], fill=COL_FLOOR, outline=None)

    # Stores (from original PDF coordinates, matching 900×780 canvas)
    _draw_store(draw, 65, 146, 294, 588, "John Lewis\n(Lower Ground)", COL_STORE_A, 14)
    _draw_store(draw, 391, 360, 503, 573, "H&M", COL_STORE_B, 15)

    # Extra stores to populate the floor plan realistically
    _draw_store(draw, 530, 146, 700, 340, "Sports\nDirect", COL_STORE_B, 13)
    _draw_store(draw, 530, 360, 700, 560, "Primark", COL_STORE_B, 14)
    _draw_store(draw, 720, 146, 870, 560, "Food\nCourt", COL_STORE_C, 14)

    # Toilets
    _draw_store(draw, 391, 146, 520, 340, "Toilets /\nServices", (220, 220, 220), 11)

    # Stairs / escalators
    _draw_stairs(draw, 770, 640, "To Ground")

    # Entrance
    _draw_entrance(draw, 450, 730)

    # Floor label
    draw.text((W // 2, 30), "LOWER GROUND FLOOR", fill=COL_WALL,
              font=_font(18), anchor="mm")

    return img


# ---------------------------------------------------------------------------
# Floor 1 – Ground
# ---------------------------------------------------------------------------

def make_ground() -> Image.Image:
    img, draw = _base_image()

    draw.rectangle([(310, 100), (390, 700)], fill=COL_CORRIDOR, outline=None)
    draw.rectangle([(50, 610), (870, 700)], fill=COL_CORRIDOR, outline=None)

    _draw_store(draw, 108, 279, 308, 661, "John Lewis\n(Ground Floor)", COL_STORE_A, 14)
    _draw_store(draw, 340, 300, 416, 408, "Apple", COL_STORE_D, 15)

    _draw_store(draw, 430, 146, 650, 350, "Zara", COL_STORE_B, 15)
    _draw_store(draw, 430, 370, 650, 590, "Next", COL_STORE_B, 15)
    _draw_store(draw, 680, 146, 870, 590, "Marks &\nSpencer", COL_STORE_A, 13)

    _draw_store(draw, 108, 146, 308, 260, "Information\nDesk", (200, 230, 200), 11)

    _draw_stairs(draw, 770, 640, "To Upper")
    _draw_stairs(draw, 630, 640, "To Lower")

    _draw_entrance(draw, 450, 730)

    draw.text((W // 2, 30), "GROUND FLOOR", fill=COL_WALL,
              font=_font(18), anchor="mm")

    return img


# ---------------------------------------------------------------------------
# Floor 2 – Upper
# ---------------------------------------------------------------------------

def make_upper() -> Image.Image:
    img, draw = _base_image()

    draw.rectangle([(310, 100), (760, 180)], fill=COL_CORRIDOR, outline=None)
    draw.rectangle([(310, 500), (760, 580)], fill=COL_CORRIDOR, outline=None)
    draw.rectangle([(310, 100), (390, 700)], fill=COL_CORRIDOR, outline=None)

    _draw_store(draw, 502, 169, 609, 289, "Nando's", COL_STORE_C, 15)
    _draw_store(draw, 551, 596, 714, 726, "Leon", COL_STORE_C, 15)

    _draw_store(draw, 50,  146, 290, 400, "Vue\nCinema", COL_STORE_B, 14)
    _draw_store(draw, 50,  430, 290, 726, "Gym /\nLeisure", COL_STORE_B, 14)
    _draw_store(draw, 630, 146, 870, 400, "Wagamama", COL_STORE_C, 14)
    _draw_store(draw, 630, 430, 870, 560, "Pret\nA Manger", COL_STORE_C, 13)

    _draw_stairs(draw, 770, 640, "To Ground")

    draw.text((W // 2, 30), "UPPER FLOOR", fill=COL_WALL,
              font=_font(18), anchor="mm")

    return img


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

FLOOR_FILES = {
    "lower": "lower.png",
    "ground": "ground.png",
    "upper": "upper.png",
}

_MAKERS = {
    "lower": make_lower_ground,
    "ground": make_ground,
    "upper": make_upper,
}


def ensure_maps(maps_dir: str = "data/maps") -> None:
    """Generate any missing floor-plan PNG files in *maps_dir*."""
    Path(maps_dir).mkdir(parents=True, exist_ok=True)
    for key, filename in FLOOR_FILES.items():
        path = os.path.join(maps_dir, filename)
        if not os.path.exists(path):
            img = _MAKERS[key]()
            img.save(path)


if __name__ == "__main__":
    ensure_maps()
    print("Floor plan images written to data/maps/")
