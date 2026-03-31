"""
Mall Navigator – Streamlit Web Application
==========================================
A shopping-mall pathfinding app built on:
  • OpenStreetMap (Folium) for outdoor navigation (free, no API key)
  • Custom PNG floor-plan images matching the original A-level project
  • Dijkstra + A* algorithms with side-by-side educational comparison
  • JSON-backed product cache (click to pin a product, search to navigate)
  • GPS-based location verification (advisory, non-blocking)

Deploy on Streamlit Community Cloud (free) via:  https://share.streamlit.io
"""

import io
import json
import math
import os

import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
from PIL import Image

# ── local imports ─────────────────────────────────────────────────────────────
from algorithms.dijkstra import dijkstra
from algorithms.astar import astar
from components.map_view import render_floor_map, generate_directions, path_pixel_list
from components.outdoor_map import render_outdoor_map
from components.product_manager import (
    load_products, add_product, delete_product,
    search_products, products_for_floor,
)
from components.directions_panel import render_comparison, render_directions
from utils.coordinates import nearest_node, euclidean
from utils.generate_maps import ensure_maps
from utils.gps_verify import check_in_range

# ── configuration imports ─────────────────────────────────────────────────────
from config import (
    PAGE_TITLE, PAGE_ICON, PAGE_LAYOUT, INITIAL_SIDEBAR_STATE,
    FLOORS, FLOOR_NAMES, INTER_FLOOR_EDGES,
    STORES, MODES, DEFAULT_FLOOR, DEFAULT_MODE, DEFAULT_PX_PER_METRE,
    PX_PER_METRE_MIN, PX_PER_METRE_MAX, PX_PER_METRE_STEP,
)


# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=PAGE_LAYOUT,
    initial_sidebar_state=INITIAL_SIDEBAR_STATE,
)


# ── helpers ───────────────────────────────────────────────────────────────────

@st.cache_data
def _load_graph(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@st.cache_data
def _load_image(path: str) -> Image.Image:
    return Image.open(path).convert("RGB")


def _all_graphs() -> dict[int, dict]:
    return {i: _load_graph(FLOORS[i]["graph"]) for i in FLOORS}


def _build_combined_graph(graphs: dict[int, dict]) -> tuple[dict, dict]:
    """
    Merge per-floor graphs into one for multi-floor A* / Dijkstra.

    Node ids are prefixed with the floor index: e.g. "1:apple_store".
    Returns (combined_edges, combined_node_coords).
    """
    edges: dict[str, dict[str, float]] = {}
    coords: dict[str, dict] = {}

    for floor_idx, g in graphs.items():
        for nid, nd in g["nodes"].items():
            key = f"{floor_idx}:{nid}"
            coords[key] = nd
            edges.setdefault(key, {})
        for nid, neighbours in g["edges"].items():
            key = f"{floor_idx}:{nid}"
            for nb, w in neighbours.items():
                edges[key][f"{floor_idx}:{nb}"] = w

    # Add inter-floor stair edges
    for fa, na, fb, nb, cost in INTER_FLOOR_EDGES:
        ka, kb = f"{fa}:{na}", f"{fb}:{nb}"
        if ka in edges and kb in edges:
            edges[ka][kb] = cost
            edges[kb][ka] = cost

    return edges, coords


def _run_pathfinding(
    start_floor: int,
    start_node: str,
    end_floor: int,
    end_node: str,
    graphs: dict[int, dict],
) -> tuple[dict, dict]:
    """
    Run both Dijkstra and A* between start and end (possibly on different floors).
    Returns (dijkstra_result, astar_result) with prefixed node-id paths.
    """
    if start_floor == end_floor:
        g = graphs[start_floor]
        node_coords = g["nodes"]
        edge_dict = g["edges"]
        dijk = dijkstra(edge_dict, start_node, end_node)
        star = astar(edge_dict, node_coords, start_node, end_node)
    else:
        combined_edges, combined_coords = _build_combined_graph(graphs)
        sk = f"{start_floor}:{start_node}"
        ek = f"{end_floor}:{end_node}"
        dijk = dijkstra(combined_edges, sk, ek)
        star = astar(combined_edges, combined_coords, sk, ek)

    return dijk, star


def _path_for_floor(path: list[str], floor: int, multi_floor: bool) -> list[str]:
    """Extract the single-floor segment from a (possibly prefixed) path."""
    if not multi_floor:
        return path
    prefix = f"{floor}:"
    return [nid[len(prefix):] for nid in path if nid.startswith(prefix)]


def _pil_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ── session-state initialisation ─────────────────────────────────────────────

def _init_state():
    defaults = {
        "current_floor": DEFAULT_FLOOR,
        "start_floor":   None,
        "start_node":    None,
        "end_floor":     None,
        "end_node":      None,
        "selecting":     "start",    # "start" | "end"
        "dijk_result":   None,
        "star_result":   None,
        "products":      load_products(),
        "px_per_metre":  DEFAULT_PX_PER_METRE,
        "show_wpts":     False,
        "gps_lat":       None,
        "gps_lng":       None,
        "gps_checked":   False,
        "store_key":     "asda_old_kent_road",
        "tab":           DEFAULT_MODE,
        "add_floor":     DEFAULT_FLOOR,
        "add_x":         None,
        "add_y":         None,
        "add_name":      "",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ── GPS verification banner ───────────────────────────────────────────────────

def _gps_banner():
    """
    Non-blocking GPS check.  Uses streamlit-js-eval to call the browser
    Geolocation API.  Shows a status banner but never blocks navigation.
    """
    try:
        from streamlit_js_eval import get_geolocation
        if not st.session_state.gps_checked:
            with st.spinner("Checking your location…"):
                loc = get_geolocation()
            if loc and "coords" in loc:
                st.session_state.gps_lat = loc["coords"]["latitude"]
                st.session_state.gps_lng = loc["coords"]["longitude"]
                st.session_state.gps_checked = True
    except Exception:
        pass  # geolocation unavailable or denied – continue silently

    if st.session_state.gps_lat is not None:
        result = check_in_range(
            st.session_state.gps_lat,
            st.session_state.gps_lng,
            st.session_state.store_key,
        )
        if result["in_range"]:
            st.success(
                f"📍 Location verified – you are within {result['distance_m']:.0f} m "
                f"of **{result['store_name']}**."
            )
        else:
            st.warning(
                f"⚠️ You appear to be **{result['distance_m']:.0f} m** from "
                f"{result['store_name']}.  Navigation still works – GPS may be "
                "inaccurate indoors."
            )
    else:
        st.info(
            "📡 Location not detected (GPS unavailable or denied). "
            "The app works fully without location access."
        )


# ── sidebar ───────────────────────────────────────────────────────────────────

def _sidebar(graphs: dict[int, dict]):
    with st.sidebar:
        st.title("🗺️ Mall Navigator")
        st.caption("Shopping-mall navigation — Dijkstra + A*")
        st.divider()

        # Store selection
        store_options = {v["name"]: k for k, v in STORES.items()}
        store_label = st.selectbox(
            "Store",
            options=list(store_options.keys()),
            index=list(store_options.keys()).index(
                STORES[st.session_state.store_key]["name"]
            ),
        )
        st.session_state.store_key = store_options[store_label]

        st.divider()

        # Mode tabs
        for key, label in MODES.items():
            if st.button(label, use_container_width=True,
                         type="primary" if st.session_state.tab == key else "secondary"):
                st.session_state.tab = key
                st.rerun()

        st.divider()

        # Floor selector
        floor_name = st.selectbox(
            "Floor",
            options=list(FLOOR_NAMES.values()),
            index=st.session_state.current_floor,
        )
        st.session_state.current_floor = [
            k for k, v in FLOOR_NAMES.items() if v == floor_name
        ][0]

        st.divider()

        # Product search (navigate mode)
        if st.session_state.tab == "navigate":
            st.subheader("🔍 Find a product / store")
            query = st.text_input("Search", placeholder="e.g. apple, hm, leon")
            if query:
                hits = search_products(query, st.session_state.products)
                if hits:
                    for name, info in hits[:6]:
                        floor_lbl = FLOOR_NAMES[info["floor"]]
                        if st.button(
                            f"📍 {name.title()} — {floor_lbl}",
                            key=f"srch_{name}",
                            use_container_width=True,
                        ):
                            st.session_state.end_floor = info["floor"]
                            st.session_state.end_node = info["nearest_node"]
                            st.session_state.current_floor = info["floor"]
                            st.session_state.selecting = "start"
                            st.rerun()
                else:
                    st.caption("No results.")

        # Settings
        st.divider()
        with st.expander("⚙️ Settings"):
            st.session_state.px_per_metre = st.slider(
                "Scale (px per metre)",
                min_value=PX_PER_METRE_MIN, max_value=PX_PER_METRE_MAX,
                value=st.session_state.px_per_metre, step=PX_PER_METRE_STEP,
                help="Calibrate to your floor plan. Default 10 px/m is approximate.",
            )
            st.session_state.show_wpts = st.checkbox(
                "Show waypoints", value=st.session_state.show_wpts
            )

        # Start / end summary
        st.divider()
        s_lbl = "—"
        if st.session_state.start_node:
            g = graphs[st.session_state.start_floor]
            s_lbl = f"{FLOOR_NAMES[st.session_state.start_floor]}: " \
                    f"{g['nodes'][st.session_state.start_node]['label']}"
        e_lbl = "—"
        if st.session_state.end_node:
            g = graphs[st.session_state.end_floor]
            e_lbl = f"{FLOOR_NAMES[st.session_state.end_floor]}: " \
                    f"{g['nodes'][st.session_state.end_node]['label']}"
        st.markdown(f"🟢 **Start:** {s_lbl}")
        st.markdown(f"🔴 **End:** {e_lbl}")

        if st.session_state.start_node and st.session_state.end_node:
            if st.button("🔍 Find Path", type="primary", use_container_width=True):
                dijk, star = _run_pathfinding(
                    st.session_state.start_floor,
                    st.session_state.start_node,
                    st.session_state.end_floor,
                    st.session_state.end_node,
                    graphs,
                )
                st.session_state.dijk_result = dijk
                st.session_state.star_result = star
                st.rerun()

        if st.button("🔄 Reset", use_container_width=True):
            for k in ("start_node", "end_node", "start_floor", "end_floor",
                      "dijk_result", "star_result"):
                st.session_state[k] = None
            st.session_state.selecting = "start"
            st.rerun()


# ── navigate tab ─────────────────────────────────────────────────────────────

def _tab_navigate(graphs: dict[int, dict]):
    floor = st.session_state.current_floor
    g = graphs[floor]
    nodes = g["nodes"]

    # Determine which paths to draw (same-floor segments only)
    multi = (
        st.session_state.start_floor is not None
        and st.session_state.end_floor is not None
        and st.session_state.start_floor != st.session_state.end_floor
    )
    dijk_path = astar_path = None
    if st.session_state.dijk_result and st.session_state.dijk_result["found"]:
        dijk_path = _path_for_floor(
            st.session_state.dijk_result["path"],
            floor, multi,
        )
    if st.session_state.star_result and st.session_state.star_result["found"]:
        astar_path = _path_for_floor(
            st.session_state.star_result["path"],
            floor, multi,
        )

    # Determine which markers belong to this floor
    s_node = (st.session_state.start_node
              if st.session_state.start_floor == floor else None)
    e_node = (st.session_state.end_node
              if st.session_state.end_floor == floor else None)

    # Products on this floor
    floor_products = products_for_floor(floor, st.session_state.products)

    # Render overlay image
    img = render_floor_map(
        FLOORS[floor]["map"],
        nodes,
        start_node=s_node,
        end_node=e_node,
        dijkstra_path=dijk_path,
        astar_path=astar_path,
        products=floor_products,
        show_waypoints=st.session_state.show_wpts,
    )

    # ── click instructions ────────────────────────────────────────────────────
    hint = {
        "start": "🟢 Click the map to set your **start** position.",
        "end":   "🔴 Click the map to set your **end / destination** position.",
    }.get(st.session_state.selecting, "")
    if hint:
        st.info(hint)

    # ── interactive image ─────────────────────────────────────────────────────
    coords = streamlit_image_coordinates(
        img,
        key=f"map_{floor}",
        use_column_width="always",
    )

    if coords:
        click_x, click_y = coords["x"], coords["y"]
        # Coordinates from streamlit-image-coordinates match the original
        # image pixel space when use_column_width="always" is used.
        nn = nearest_node(click_x, click_y, nodes)

        if st.session_state.selecting == "start":
            st.session_state.start_node = nn
            st.session_state.start_floor = floor
            st.session_state.selecting = "end"
        else:
            st.session_state.end_node = nn
            st.session_state.end_floor = floor
            st.session_state.selecting = "start"

        # Auto-run pathfinding when both ends are set
        if st.session_state.start_node and st.session_state.end_node:
            dijk, star = _run_pathfinding(
                st.session_state.start_floor,
                st.session_state.start_node,
                st.session_state.end_floor,
                st.session_state.end_node,
                graphs,
            )
            st.session_state.dijk_result = dijk
            st.session_state.star_result = star

        st.rerun()

    st.caption(
        "🟠 Orange = Dijkstra path &nbsp;|&nbsp; "
        "🔵 Blue = A* path &nbsp;|&nbsp; "
        "🟢 S = Start &nbsp;|&nbsp; 🔴 E = End &nbsp;|&nbsp; "
        "🟣 Purple dots = cached products"
    )

    # ── results panel ─────────────────────────────────────────────────────────
    if st.session_state.dijk_result and st.session_state.star_result:
        st.divider()
        # Directions (use A* path, same optimal cost as Dijkstra)
        best = (st.session_state.star_result
                if st.session_state.star_result["found"]
                else st.session_state.dijk_result)
        if best["found"]:
            # For multi-floor, show directions for the current floor segment only
            path_here = _path_for_floor(best["path"], floor, multi)
            steps = generate_directions(
                path_here, nodes, st.session_state.px_per_metre
            )
            if steps:
                render_directions(
                    steps, path_here, nodes, st.session_state.px_per_metre
                )
            elif multi:
                st.info(
                    "Path crosses floors — switch floors to see each segment."
                )

        st.divider()
        render_comparison(
            st.session_state.dijk_result,
            st.session_state.star_result,
            st.session_state.px_per_metre,
        )


# ── add product tab ──────────────────────────────────────────────────────────

def _tab_add_product(graphs: dict[int, dict]):
    st.header("📌 Add a Product to the Cache")
    st.markdown(
        "Pin a product location on the floor plan so others can navigate to it. "
        "Enter a name, select the floor, then **click the map** where the product is."
    )

    col_form, col_map = st.columns([1, 2])

    with col_form:
        name = st.text_input("Product / store name", value=st.session_state.add_name,
                             placeholder="e.g. milk, trainers, pharmacy")
        floor_lbl = st.selectbox("Floor", list(FLOOR_NAMES.values()),
                                 index=st.session_state.add_floor)
        add_floor = [k for k, v in FLOOR_NAMES.items() if v == floor_lbl][0]
        st.session_state.add_floor = add_floor

        if st.session_state.add_x:
            g = graphs[add_floor]
            nn = nearest_node(st.session_state.add_x, st.session_state.add_y,
                              g["nodes"])
            st.success(
                f"📍 Pinned at ({int(st.session_state.add_x)}, "
                f"{int(st.session_state.add_y)}) — nearest waypoint: "
                f"**{g['nodes'][nn]['label']}**"
            )

        if st.button("💾 Save product", type="primary",
                     disabled=not (name.strip() and st.session_state.add_x)):
            g = graphs[add_floor]
            updated, nn = add_product(
                name,
                add_floor,
                st.session_state.add_x,
                st.session_state.add_y,
                g["nodes"],
            )
            st.session_state.products = updated
            st.session_state.add_x = None
            st.session_state.add_y = None
            st.session_state.add_name = ""
            st.success(f"✅ Saved **{name.lower().strip()}**!")
            st.rerun()

        st.divider()
        st.subheader("🗑️ Remove a product")
        del_name = st.selectbox(
            "Select product to delete",
            options=[""] + sorted(st.session_state.products.keys()),
        )
        if del_name and st.button("Delete", type="secondary"):
            st.session_state.products = delete_product(del_name)
            st.rerun()

    with col_map:
        g = graphs[add_floor]
        img = render_floor_map(
            FLOORS[add_floor]["map"],
            g["nodes"],
            show_waypoints=True,
            products=products_for_floor(add_floor, st.session_state.products),
        )
        st.caption("Click on the map to pin the product location.")
        coords = streamlit_image_coordinates(
            img, key=f"add_map_{add_floor}", use_column_width="always"
        )
        if coords:
            st.session_state.add_x = coords["x"]
            st.session_state.add_y = coords["y"]
            st.rerun()


# ── outdoor map tab ──────────────────────────────────────────────────────────

def _tab_outdoor():
    st.header("🌍 Outdoor Map")
    store = STORES[st.session_state.store_key]
    render_outdoor_map(
        store_lat=store["lat"],
        store_lng=store["lng"],
        store_name=store["name"],
        user_lat=st.session_state.gps_lat,
        user_lng=st.session_state.gps_lng,
        distance_m=(
            check_in_range(
                st.session_state.gps_lat,
                st.session_state.gps_lng,
                st.session_state.store_key,
            )["distance_m"]
            if st.session_state.gps_lat is not None
            else None
        ),
    )
    st.caption(
        "Map data © [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors. "
        "No API key required."
    )


# ── product list widget ───────────────────────────────────────────────────────

def _product_list_widget():
    with st.expander("📦 All cached products"):
        if not st.session_state.products:
            st.caption("No products cached yet.")
            return
        for name, info in sorted(st.session_state.products.items()):
            st.markdown(
                f"• **{name.title()}** — {FLOOR_NAMES[info['floor']]} "
                f"| {info.get('note', '')} "
                f"| _{info.get('timestamp', '')[:10]}_"
            )


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    # Generate floor-plan images if missing
    base = os.path.dirname(__file__)
    ensure_maps(os.path.join(base, "data", "maps"))

    _init_state()

    graphs = _all_graphs()

    # GPS banner (non-blocking)
    _gps_banner()

    # Sidebar
    _sidebar(graphs)

    # Main content
    if st.session_state.tab == "navigate":
        st.header("🧭 Indoor Navigation")
        _tab_navigate(graphs)
        st.divider()
        _product_list_widget()

    elif st.session_state.tab == "add_product":
        _tab_add_product(graphs)
        st.divider()
        _product_list_widget()

    elif st.session_state.tab == "outdoor":
        _tab_outdoor()


if __name__ == "__main__":
    main()
