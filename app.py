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
import time
from pathlib import Path

import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
from PIL import Image

# ── local imports ─────────────────────────────────────────────────────────────
from algorithms.dijkstra import dijkstra
from algorithms.astar import astar
from algorithms.yen_ksp import yen_k_shortest_paths
from components.live_navigation import (
    init_live_navigation_state,
    render_live_navigation_panel,
    update_live_position,
)
from components.map_view import render_floor_map, generate_directions, path_pixel_list
from components.outdoor_map import render_outdoor_map
from components.product_manager import (
    load_products, add_product, delete_product,
    search_products, products_for_floor, is_product_open,
)
from components.directions_panel import render_comparison, render_directions
from utils.coordinates import nearest_node, euclidean
from utils.analytics import AnalyticsStore
from utils.feedback import save_feedback
from utils.generate_maps import ensure_maps
from utils.gps_verify import check_in_range
from utils.health import run_health_checks
from utils.location_tracking import LocationTracker
from utils.monitoring import configure_logging, get_logger, log_event, setup_sentry
from utils.routing import build_accessible_graph, walking_time_seconds
from utils.security import InMemoryRateLimiter, sanitize_query, sanitize_text, verify_password
from utils.ux_helpers import get_instruction_message

# ── configuration imports ─────────────────────────────────────────────────────
from config import (
    PAGE_TITLE, PAGE_ICON, PAGE_LAYOUT, INITIAL_SIDEBAR_STATE,
    FLOORS, FLOOR_NAMES, INTER_FLOOR_EDGES,
    STORES, MODES, DEFAULT_FLOOR, DEFAULT_MODE, DEFAULT_PX_PER_METRE,
    PX_PER_METRE_MIN, PX_PER_METRE_MAX, PX_PER_METRE_STEP,
)

configure_logging()
LOGGER = get_logger("mall_navigator")
SENTRY_ENABLED = setup_sentry(os.getenv("SENTRY_DSN"))


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
    return {
        i: _load_graph(_resolve_floor_asset(st.session_state.store_key, i, "graph"))
        for i in FLOORS
    }


def _resolve_floor_asset(store_key: str, floor_idx: int, asset: str) -> str:
    """Resolve store-specific graph/map path with fallback to default config."""
    if asset not in {"graph", "map"}:
        raise ValueError(f"Unsupported asset type: {asset}")

    default_path = FLOORS[floor_idx][asset]
    store_cfg = STORES.get(store_key, {})
    root_key = "graph_dir" if asset == "graph" else "map_dir"
    root_dir = str(store_cfg.get(root_key, "")).strip()
    if not root_dir:
        return default_path

    candidate = str(Path(root_dir) / Path(default_path).name)
    return candidate if os.path.exists(candidate) else default_path


def _build_combined_graph(graphs: dict[int, dict]) -> tuple[dict, dict]:
    """
    Merge per-floor graphs into one for multi-floor A* / Dijkstra.

    Node ids are prefixed with the floor index: e.g. "1:apple_store".
    Returns (combined_edges, combined_node_coords).
    
    This function is called infrequently and the combined graph is relatively
    small, so caching provides modest benefits but improves responsiveness.
    """
    @st.cache_data(show_spinner=False)
    def _build_cached():
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
    
    return _build_cached()


def _run_pathfinding(
    start_floor: int,
    start_node: str,
    end_floor: int,
    end_node: str,
    graphs: dict[int, dict],
    *,
    accessible_mode: bool,
    k_routes: int,
) -> tuple[dict, dict, list[dict[str, object]]]:
    """
    Run both Dijkstra and A* between start and end (possibly on different floors).
    Returns (dijkstra_result, astar_result) with prefixed node-id paths.
    """
    alternatives: list[dict[str, object]] = []
    started = time.perf_counter()

    if start_floor == end_floor:
        g = graphs[start_floor]
        node_coords = g["nodes"]
        edge_dict = build_accessible_graph(
            g["edges"],
            g["nodes"],
            prefer_accessible=accessible_mode,
        )
        dijk = dijkstra(edge_dict, start_node, end_node)
        star = astar(edge_dict, node_coords, start_node, end_node)
        if star.get("found"):
            alternatives = yen_k_shortest_paths(edge_dict, start_node, end_node, k=k_routes)
    else:
        combined_edges, combined_coords = _build_combined_graph(graphs)
        combined_edges = build_accessible_graph(
            combined_edges,
            combined_coords,
            prefer_accessible=accessible_mode,
        )
        sk = f"{start_floor}:{start_node}"
        ek = f"{end_floor}:{end_node}"
        dijk = dijkstra(combined_edges, sk, ek)
        star = astar(combined_edges, combined_coords, sk, ek)
        if star.get("found"):
            alternatives = yen_k_shortest_paths(combined_edges, sk, ek, k=k_routes)

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    log_event(
        LOGGER,
        event="pathfinding_run",
        start_floor=start_floor,
        end_floor=end_floor,
        accessible_mode=accessible_mode,
        k_routes=k_routes,
        graph_nodes=sum(len(g.get("nodes", {})) for g in graphs.values()),
        graph_edges=sum(len(nbrs) for g in graphs.values() for nbrs in g.get("edges", {}).values()),
        elapsed_ms=round(elapsed_ms, 2),
        dijkstra_found=bool(dijk.get("found")),
        astar_found=bool(star.get("found")),
    )

    return dijk, star, alternatives


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
        "accessible_mode": False,
        "k_routes":      3,
        "gps_lat":       None,
        "gps_lng":       None,
        "gps_checked":   False,
        "store_key":     "asda_old_kent_road",
        "tab":           DEFAULT_MODE,
        "add_floor":     DEFAULT_FLOOR,
        "add_x":         None,
        "add_y":         None,
        "add_name":      "",
        "alt_routes":    [],
        "gps_disabled": False,
        "privacy_policy_ack": False,
        "admin_authenticated": False,
        "report_message": "",
        "report_contact": "",
        "rate_limiters": {
            "search": InMemoryRateLimiter(max_requests=20, window_seconds=60),
            "add_product": InMemoryRateLimiter(max_requests=10, window_seconds=60),
            "report_issue": InMemoryRateLimiter(max_requests=5, window_seconds=300),
        },
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
    if st.session_state.gps_disabled:
        st.info("📡 GPS is disabled for this session. You can re-enable it from Privacy settings.")
        return

    if not st.session_state.privacy_policy_ack:
        st.info(
            "🔐 GPS is disabled by default. Open Privacy settings in the sidebar and consent "
            "if you want location-aware guidance."
        )
        return

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
        LOGGER.exception("GPS geolocation call failed")

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
    analytics = AnalyticsStore()

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
                clean_query = sanitize_query(query, max_len=80)
                search_limit = st.session_state.rate_limiters["search"].allow("search")
                if not search_limit.allowed:
                    st.warning(
                        f"Too many search requests. Try again in about {int(search_limit.retry_after_seconds) + 1}s."
                    )
                    hits = []
                else:
                    analytics.track_search(clean_query)
                    hits = search_products(clean_query, st.session_state.products)
                if hits:
                    for name, info in hits[:6]:
                        floor_lbl = FLOOR_NAMES[info["floor"]]
                        open_state = is_product_open(info)
                        status = ""
                        if open_state is True:
                            status = " | Open"
                        elif open_state is False:
                            status = " | Closed"
                        if st.button(
                            f"📍 {name.title()} — {floor_lbl}{status}",
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
            st.session_state.accessible_mode = st.checkbox(
                "Accessibility mode (avoid stairs/escalators)",
                value=st.session_state.accessible_mode,
            )
            st.session_state.k_routes = st.slider(
                "Alternative routes",
                min_value=1,
                max_value=5,
                value=st.session_state.k_routes,
            )

        with st.expander("🔐 Privacy"):
            st.session_state.privacy_policy_ack = st.checkbox(
                "I consent to GPS processing for navigation assistance",
                value=bool(st.session_state.privacy_policy_ack),
                help=(
                    "Location data stays local to this app session unless you explicitly consent "
                    "to live-navigation history storage."
                ),
            )
            st.session_state.gps_disabled = st.checkbox(
                "Disable GPS for this session",
                value=bool(st.session_state.gps_disabled),
            )
            if st.session_state.gps_disabled:
                st.session_state.gps_lat = None
                st.session_state.gps_lng = None
                st.session_state.gps_checked = False

        with st.expander("🛠️ Admin Access"):
            expected_hash = os.getenv("ADMIN_PASSWORD_HASH", "").strip().lower()
            salt = os.getenv("ADMIN_PASSWORD_SALT", "").strip()
            if not expected_hash or not salt:
                st.caption("Admin authentication not configured. Set ADMIN_PASSWORD_HASH and ADMIN_PASSWORD_SALT.")
                st.session_state.admin_authenticated = False
            else:
                admin_password = st.text_input("Admin password", type="password")
                if st.button("Sign in", use_container_width=True):
                    st.session_state.admin_authenticated = verify_password(admin_password, salt, expected_hash)
                    if st.session_state.admin_authenticated:
                        st.success("Admin authenticated.")
                        log_event(LOGGER, event="admin_login_success")
                    else:
                        st.error("Invalid admin password.")
                        log_event(LOGGER, event="admin_login_failure")

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
                dijk, star, alternatives = _run_pathfinding(
                    st.session_state.start_floor,
                    st.session_state.start_node,
                    st.session_state.end_floor,
                    st.session_state.end_node,
                    graphs,
                    accessible_mode=st.session_state.accessible_mode,
                    k_routes=st.session_state.k_routes,
                )
                st.session_state.dijk_result = dijk
                st.session_state.star_result = star
                st.session_state.alt_routes = alternatives
                analytics.track_algorithm_result("dijkstra", dijk)
                analytics.track_algorithm_result("astar", star)
                if star.get("found"):
                    analytics.track_route(star.get("path", []))
                elif dijk.get("found"):
                    analytics.track_route(dijk.get("path", []))
                st.rerun()

        if st.button("🔄 Reset", use_container_width=True):
            for k in ("start_node", "end_node", "start_floor", "end_floor",
                      "dijk_result", "star_result", "alt_routes"):
                st.session_state[k] = None
            st.session_state.selecting = "start"
            st.rerun()


# ── navigate tab ─────────────────────────────────────────────────────────────

def _tab_navigate(graphs: dict[int, dict]):
    floor = st.session_state.current_floor
    g = graphs[floor]
    nodes = g["nodes"]
    tracker = LocationTracker()
    analytics = AnalyticsStore()

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
        _resolve_floor_asset(st.session_state.store_key, floor, "map"),
        nodes,
        start_node=s_node,
        end_node=e_node,
        dijkstra_path=dijk_path,
        astar_path=astar_path,
        products=floor_products,
        show_waypoints=st.session_state.show_wpts,
    )

    # ── click instructions ────────────────────────────────────────────────────
    col_l, col_r = st.columns([3, 1])
    with col_l:
        has_route = bool(
            st.session_state.star_result and st.session_state.star_result.get("found")
        )
        if st.session_state.live_nav_enabled and st.session_state.live_nav_capture_click and has_route:
            st.info("📡 Live mode: click the map to update your current position.")
        else:
            instruction = get_instruction_message(st.session_state.selecting)
            if instruction:
                st.info(instruction)
            elif not st.session_state.start_node and not st.session_state.end_node:
                st.info("👆 **Click on the map** to set your start location, then your destination.")

    # ── interactive image ─────────────────────────────────────────────────────
    coords = streamlit_image_coordinates(
        img,
        key=f"map_{floor}",
        use_column_width="always",
    )

    if coords:
        click_x, click_y = coords["x"], coords["y"]

        # In live mode, map clicks update current position instead of start/end.
        if st.session_state.live_nav_enabled and st.session_state.live_nav_capture_click and has_route:
            update_live_position(
                tracker=tracker,
                floor=floor,
                x=click_x,
                y=click_y,
                nodes=nodes,
                source="map_click",
            )
            st.rerun()

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
            dijk, star, alternatives = _run_pathfinding(
                st.session_state.start_floor,
                st.session_state.start_node,
                st.session_state.end_floor,
                st.session_state.end_node,
                graphs,
                accessible_mode=st.session_state.accessible_mode,
                k_routes=st.session_state.k_routes,
            )
            st.session_state.dijk_result = dijk
            st.session_state.star_result = star
            st.session_state.alt_routes = alternatives
            analytics.track_algorithm_result("dijkstra", dijk)
            analytics.track_algorithm_result("astar", star)
            if star.get("found"):
                analytics.track_route(star.get("path", []))
            elif dijk.get("found"):
                analytics.track_route(dijk.get("path", []))

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
        if st.session_state.star_result["found"]:
            if multi:
                _, combined_nodes = _build_combined_graph(graphs)
                walk_seconds = walking_time_seconds(
                    st.session_state.star_result["path"],
                    combined_nodes,
                    st.session_state.px_per_metre,
                )
            else:
                walk_seconds = walking_time_seconds(
                    st.session_state.star_result["path"],
                    nodes,
                    st.session_state.px_per_metre,
                )
            st.metric("Estimated walking time", f"{walk_seconds} sec")

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

            render_live_navigation_panel(
                tracker=tracker,
                floor=floor,
                nodes=nodes,
                path=path_here,
                steps=steps,
                px_per_metre=st.session_state.px_per_metre,
            )

            if steps:
                with st.expander("📋 Step-by-step directions", expanded=True):
                    render_directions(
                        steps, path_here, nodes, st.session_state.px_per_metre
                    )
            elif multi:
                st.info(
                    "🏢 **Multi-floor path** — Switch floors in the sidebar to see "
                    "each segment of your route."
                )

        st.divider()
        with st.expander("🔬 Algorithm Comparison", expanded=False):
            render_comparison(
                st.session_state.dijk_result,
                st.session_state.star_result,
                st.session_state.px_per_metre,
            )

        if st.session_state.alt_routes:
            st.divider()
            with st.expander("🛣️ Alternative routes", expanded=False):
                for idx, route in enumerate(st.session_state.alt_routes, start=1):
                    metres = float(route["cost"]) / st.session_state.px_per_metre
                    st.markdown(
                        f"{idx}. Distance: **{metres:.1f} m** ({route['cost']:.1f} px), "
                        f"steps: **{len(route['path']) - 1}**"
                    )

        st.divider()
        with st.expander("📈 Phase 3 Analytics", expanded=False):
            if not st.session_state.admin_authenticated:
                st.info("Admin sign-in required to view analytics.")
            else:
                st.markdown("**Popular routes**")
                top_routes = analytics.top_routes(limit=5)
                if top_routes:
                    for key, count in top_routes:
                        st.caption(f"• {key} — {count} runs")
                else:
                    st.caption("No route history yet.")

                st.markdown("**Slow areas (high traffic waypoints)**")
                slow_areas = analytics.slow_areas(limit=5)
                if slow_areas:
                    for node_id, visits in slow_areas:
                        st.caption(f"• {node_id} — {visits} visits")
                else:
                    st.caption("No waypoint traffic yet.")

                st.markdown("**Search trends**")
                top_searches = analytics.top_search_terms(limit=5)
                if top_searches:
                    for term, count in top_searches:
                        st.caption(f"• {term} — {count} searches")
                else:
                    st.caption("No search data yet.")

                st.markdown("**Pathfinding comparison summary**")
                summary = analytics.algorithm_summary()
                if summary:
                    for algorithm, stats in summary.items():
                        st.caption(
                            f"• {algorithm}: runs={int(stats['runs'])}, "
                            f"avg time={stats['avg_time_us']:.1f} us, "
                            f"avg nodes={stats['avg_nodes_visited']:.1f}, "
                            f"success={stats['success_rate'] * 100:.0f}%"
                        )
                else:
                    st.caption("No algorithm run data yet.")

        with st.expander("🩺 Health Checks", expanded=False):
            if not st.session_state.admin_authenticated:
                st.info("Admin sign-in required to run health checks.")
            elif st.button("Run health checks", key="run_health_checks"):
                graph_paths = [
                    _resolve_floor_asset(st.session_state.store_key, idx, "graph")
                    for idx in FLOORS
                ]
                health = run_health_checks(
                    graph_paths=graph_paths,
                    products_path="data/products.json",
                )
                if health["ok"]:
                    st.success("All health checks passed.")
                else:
                    st.error("One or more health checks failed.")
                for check in health["checks"]:
                    icon = "✅" if check.get("ok") else "❌"
                    st.caption(
                        f"{icon} {check.get('kind')} {check.get('path')} "
                        f"(reason={check.get('reason')})"
                    )
                log_event(LOGGER, event="health_check_run", success=health["ok"])

        with st.expander("📝 Report Issue", expanded=False):
            report_message = st.text_area(
                "Describe the issue",
                key="report_message",
                max_chars=600,
                placeholder="What happened? What did you expect?",
            )
            report_contact = st.text_input(
                "Contact (optional)",
                key="report_contact",
                placeholder="email@example.com",
            )
            if st.button("Submit report", use_container_width=True, key="submit_report"):
                report_limit = st.session_state.rate_limiters["report_issue"].allow("report")
                if not report_limit.allowed:
                    st.warning(
                        f"Report limit reached. Try again in about {int(report_limit.retry_after_seconds) + 1}s."
                    )
                else:
                    entry = save_feedback(
                        message=report_message,
                        contact=report_contact,
                        context={
                            "store": st.session_state.store_key,
                            "floor": floor,
                            "tab": st.session_state.tab,
                        },
                    )
                    st.success("Thanks, your report has been saved.")
                    log_event(LOGGER, event="issue_reported", has_contact=bool(entry.get("contact")))


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
        opening_hours = st.text_input(
            "Opening hours",
            placeholder="e.g. 09:00-21:00",
            help="Simple daily format supported in this phase: HH:MM-HH:MM",
        )
        category = st.selectbox(
            "Category",
            options=["", "Food", "Retail", "Services"],
        )
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
            add_limit = st.session_state.rate_limiters["add_product"].allow("add_product")
            if not add_limit.allowed:
                st.warning(
                    f"Add-product rate limit reached. Try again in about {int(add_limit.retry_after_seconds) + 1}s."
                )
            else:
                g = graphs[add_floor]
                try:
                    updated, _ = add_product(
                        sanitize_text(name, max_len=80),
                        add_floor,
                        st.session_state.add_x,
                        st.session_state.add_y,
                        g["nodes"],
                        opening_hours=sanitize_text(opening_hours, max_len=32),
                        category=sanitize_text(category, max_len=32),
                    )
                except ValueError as exc:
                    st.error(str(exc))
                    log_event(LOGGER, event="add_product_validation_error", reason=str(exc))
                else:
                    st.session_state.products = updated
                    st.session_state.add_x = None
                    st.session_state.add_y = None
                    st.session_state.add_name = ""
                    st.success(f"✅ Saved **{sanitize_text(name, max_len=80).lower().strip()}**!")
                    log_event(LOGGER, event="product_saved", floor=add_floor)
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
            _resolve_floor_asset(st.session_state.store_key, add_floor, "map"),
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

    if "app_started_logged" not in st.session_state:
        log_event(LOGGER, event="app_session_started", sentry_enabled=SENTRY_ENABLED)
        st.session_state.app_started_logged = True

    _init_state()
    init_live_navigation_state()

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
    try:
        main()
    except Exception:
        LOGGER.exception("Unhandled application error")
        raise
