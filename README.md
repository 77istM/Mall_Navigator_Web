# 🗺️ Mall Navigator

A GUI-based indoor-navigation web application for shopping malls and superstores,
built on **Streamlit** and deployable for free on
[Streamlit Community Cloud](https://share.streamlit.io).

> **A-Level Computer Science Project** — Istiak Mohammad  
> Evolved from the original tkinter/guizero pathfinding project (`final_project.pdf`).

---

## ✨ Features

| Feature | Details |
|---|---|
| **Indoor floor plans** | 3-floor PNG maps (Lower Ground, Ground, Upper) matching the original A-level GIF coordinate space |
| **Dijkstra + A\* pathfinding** | Both algorithms run simultaneously; results shown side-by-side for educational comparison |
| **Product cache** | Click anywhere on a floor plan to pin a product (e.g. "apple", "milk"); stored in `data/products.json` |
| **Product search** | Type a product name → app shows it on the map and routes to it |
| **Multi-floor routing** | Paths automatically cross floors via escalator/stair nodes (with a cost penalty) |
| **Outdoor map** | OpenStreetMap via Folium (free, no API key) shows the store location and your GPS position |
| **GPS location check** | Advisory check — warns if you appear to be outside the store, but never blocks access (indoor GPS is unreliable) |
| **Step-by-step directions** | Turn-by-turn text directions with cardinal bearing and estimated walking time |

---

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/77istM/Alevel_cs_project2023.git
cd Alevel_cs_project2023

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run locally
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## ☁️ Deploy on Streamlit Community Cloud (Free)

1. Push this repo to GitHub (it's already there).
2. Visit [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **"New app"** → select this repo → set **Main file path** to `app.py`.
4. Click **Deploy** — a public HTTPS URL is generated automatically.

No API keys, no billing, no server maintenance required.

---

## 🏗️ Project Structure

```
.
├── app.py                    # Main Streamlit entry point
├── requirements.txt
│
├── algorithms/
│   ├── dijkstra.py           # Dijkstra's algorithm (heapq, with stats)
│   └── astar.py              # A* algorithm (Euclidean heuristic, admissible)
│
├── components/
│   ├── map_view.py           # Floor-plan renderer + path overlay (Pillow)
│   ├── outdoor_map.py        # Folium/OpenStreetMap outdoor map
│   ├── product_manager.py    # Product cache CRUD (JSON-backed)
│   └── directions_panel.py   # Turn-by-turn directions + algorithm comparison
│
├── data/
│   ├── maps/                 # PNG floor-plan images (auto-generated at startup)
│   │   ├── lower.png
│   │   ├── ground.png
│   │   └── upper.png
│   ├── graphs/               # Waypoint graph JSON (nodes + weighted edges)
│   │   ├── lower.json
│   │   ├── ground.json
│   │   └── upper.json
│   └── products.json         # Product cache (name → floor, pixel coords, node)
│
└── utils/
    ├── coordinates.py        # Euclidean / haversine distance, bearing helpers
    ├── generate_maps.py      # Pillow-based floor-plan image generator
    └── gps_verify.py         # GPS distance check (haversine, advisory only)
```

---

## 🧮 Algorithm Design

### Dijkstra's Algorithm

Explores nodes in order of cumulative cost from the start. Guaranteed to find
the shortest path but examines every node within cost *d* before any node at
cost *d + 1* — no directional bias.

```
while open_set not empty:
    u = node with lowest dist[u]
    for each neighbour v of u:
        if dist[u] + weight(u,v) < dist[v]:
            dist[v] = dist[u] + weight(u,v)
            prev[v] = u
```

### A* Algorithm

Extends Dijkstra by adding a **heuristic h(n)** — the straight-line (Euclidean)
pixel distance from node *n* to the goal. This guides the search toward the goal,
so fewer nodes are visited on average.

```
f(n) = g(n) + h(n)
     = cost from start to n  +  straight-line distance n → goal
```

**Why the heuristic is admissible (never overestimates)**:  
Edge weights are Euclidean pixel distances between waypoints. Because the
straight line is always ≤ any path through the graph,
`h(n) ≤ actual_remaining_cost(n)` holds. This guarantees A* returns the
optimal path — fixing the bug in the original A-level project where hardcoded
heuristic values violated admissibility.

### Comparison

| Property | Dijkstra | A\* |
|---|---|---|
| Explores | All nodes within cost d first | Nodes physically close to goal first |
| Optimal? | ✅ Always | ✅ When heuristic is admissible |
| Speed | Slower on large graphs | Faster (explores fewer nodes) |
| Extra data needed | None | Node coordinates for h(n) |

Both algorithms produce the same **optimal** path. A\* is typically faster
(fewer nodes explored) especially on large floor plans with many waypoints.

---

## 🗺️ Graph Design

Each floor has a **waypoint graph** stored in `data/graphs/<floor>.json`:

```json
{
  "nodes": {
    "apple_store": {"x": 378, "y": 354, "floor": 1,
                    "label": "Apple Store", "type": "store"}
  },
  "edges": {
    "apple_store": {"jct_north": 154, "jct_center": 100}
  }
}
```

- **Nodes** represent corridor junctions, store entrances, escalators, and services.
- **Edge weights** are Euclidean pixel distances (matching the ruler-measured
  distances used in the original project).
- **Inter-floor edges** connect stair/escalator nodes on adjacent floors with
  a 200-pixel cost penalty.

### Scale Calibration

The floor-plan images do not have confirmed real-world measurements.
A default scale of **10 px = 1 metre** is used, giving reasonable walking-time
estimates. You can calibrate this using the sidebar slider if you know the
length of a specific corridor.

---

## 📍 Product Cache

Products are pinned by clicking on the floor plan:

1. Switch to the **"Add Product"** tab.
2. Enter a product name (e.g. `milk`, `apple`, `trainers`).
3. Select the floor.
4. Click the map where the product is located.
5. The app finds the nearest waypoint and saves the pin to `data/products.json`.

To navigate to a product, type its name in the **Search** box in the sidebar
while in Navigate mode.

---

## 📡 GPS & Public Access

The application is designed for **public, unauthenticated use** — no login required.

When the page loads, it requests the device's GPS location via the browser
Geolocation API. It then checks whether the user is within **500 m** of the
configured store:

- ✅ **Within range** — green banner confirming location.
- ⚠️ **Out of range** — warning banner (navigation still works fully).
- ℹ️ **No GPS** — info banner (location access denied or unavailable).

> Indoor GPS accuracy is typically 5–50 m, so the check is advisory only.
> The store can be changed in the sidebar (currently: Asda Old Kent Road or
> Sainsbury's Whitechapel).

---

## 🌍 Outdoor Map

The **Outdoor Map** tab shows the store's location on
[OpenStreetMap](https://www.openstreetmap.org/) using
[Folium](https://python-visualization.github.io/folium/):

- **Free, open-source** — no Google Maps API key or billing.
- Shows a 500 m access zone around the store.
- Draws a dashed line between your GPS position and the store entrance.

---

## 🔮 Future Work

### AR Direction Arrows *(planned, not yet implemented)*

**Goal**: When a user points their phone camera toward a corridor, an animated
direction arrow overlaid on the live camera feed guides them to their destination.

**Two levels of AR:**

#### Level 1 — Basic (camera overlay, manual orientation)
- Use `streamlit-webrtc` + `OpenCV` to access the device camera in the browser.
- Draw a direction arrow on each video frame using `cv2.arrowedLine`.
- The arrow always points in a fixed screen direction (e.g. "up = forward").
- The user must physically turn until the arrow points straight ahead.
- Works on any HTTPS-served Streamlit app (Streamlit Cloud provides HTTPS).

```python
# Pseudocode for basic AR
import cv2, av, math
from streamlit_webrtc import webrtc_streamer, VideoProcessorBase

class ARProcessor(VideoProcessorBase):
    bearing: float = 0.0   # updated from session_state

    def recv(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        h, w = img.shape[:2]
        cx, cy = w // 2, h // 2
        # rotate arrow tip by bearing offset
        angle = math.radians(self.bearing - 90)
        tip = (int(cx + 80 * math.cos(angle)), int(cy + 80 * math.sin(angle)))
        cv2.arrowedLine(img, (cx, cy), tip, (0, 255, 100), 8, tipLength=0.4)
        cv2.putText(img, f"{self.bearing:.0f} m", (cx-30, cy+80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255,255,255), 3)
        return av.VideoFrame.from_ndarray(img, format="bgr24")

def render_ar_view(next_bearing_deg: float, dist_m: float):
    processor = webrtc_streamer(
        key="ar_nav",
        video_processor_factory=ARProcessor,
        media_stream_constraints={"video": True, "audio": False},
    )
    if processor.video_processor:
        processor.video_processor.bearing = next_bearing_deg
```

**Extra packages needed:** `streamlit-webrtc>=0.47.0`, `opencv-python-headless>=4.9`, `av>=11.0`

#### Level 2 — Compass-corrected (phone orientation aware)
- Uses the browser `DeviceOrientationEvent` API (requires physical mobile device).
- The arrow rotates to compensate for the phone's compass heading, so it always
  points in the correct real-world direction regardless of how the user holds
  the phone.
- Requires a custom Streamlit component that injects JavaScript and posts the
  device orientation back to Python via `streamlit.components.v1`.
- Only works on HTTPS and on devices with a compass sensor (most smartphones).

**Why AR was deferred:**
Indoor environments have severe GPS + compass interference (metal shelving, WiFi,
crowd density). A compass-corrected arrow may point in the wrong direction.
The QR-anchor positioning system (see below) would need to be implemented first
to give the AR arrow a reliable "true north" reference.

### QR Code Anchors *(planned)*
- Print QR codes at known waypoint locations (aisle ends, near store signs).
- Each QR encodes `{"store": "...", "floor": 1, "node": "aisle_B_north"}`.
- Scanning a QR instantly sets the user's position to that known node, bypassing
  unreliable GPS.
- **Extra package needed:** `qrcode>=7.4`, `pyzbar>=0.1.9`

### Multi-user Product Crowd-sourcing *(planned)*
- Replace local `products.json` with a cloud database (e.g. Supabase free tier).
- Any user can pin a product; all users see each other's pins.

---

## 📚 References

- A\* algorithm structure adapted from [Isaac Computer Science / Raspberry Pi Foundation](https://github.com/isaaccomputerscience/isaac-code-samples/blob/main/pathfinding/a-star/python/a_star.py) (CC BY-SA 4.0)
- Map tiles © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright) (ODbL)
- [Folium documentation](https://python-visualization.github.io/folium/)
- [Streamlit documentation](https://docs.streamlit.io/)
