"""Phase 5 operator dashboard for admin tooling and operations."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st
from PIL import Image
from streamlit_image_coordinates import streamlit_image_coordinates

from components.map_view import render_floor_map
from components.product_manager import delete_product, load_products, save_products
from config import FLOOR_NAMES, STORES
from utils.analytics import AnalyticsStore
from utils.operator_tools import (
    FLOOR_FILE_NAMES,
    generate_graph_from_image_size,
    load_json,
    save_json,
    scaffold_store,
)
from utils.security import verify_password

st.set_page_config(page_title="Admin Dashboard", page_icon="🛠️", layout="wide")


def _auth_gate() -> bool:
    st.title("🛠️ Operator Admin Dashboard")
    st.caption("Phase 5 tools for products, graphs, analytics, and store onboarding.")

    expected_hash = st.secrets.get("ADMIN_PASSWORD_HASH", "") if hasattr(st, "secrets") else ""
    expected_hash = (expected_hash or "").strip().lower() or st.session_state.get("_env_admin_hash", "")
    salt = st.secrets.get("ADMIN_PASSWORD_SALT", "") if hasattr(st, "secrets") else ""
    salt = (salt or "").strip() or st.session_state.get("_env_admin_salt", "")

    if not expected_hash or not salt:
        # Fallback to environment variables loaded by config import path in app runtime.
        import os

        expected_hash = os.getenv("ADMIN_PASSWORD_HASH", "").strip().lower()
        salt = os.getenv("ADMIN_PASSWORD_SALT", "").strip()

    if not expected_hash or not salt:
        st.error("Admin authentication is not configured. Set ADMIN_PASSWORD_HASH and ADMIN_PASSWORD_SALT.")
        return False

    with st.form("admin_login_form"):
        password = st.text_input("Admin password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)

    if submitted:
        st.session_state["admin_dashboard_authenticated"] = verify_password(password, salt, expected_hash)

    if not st.session_state.get("admin_dashboard_authenticated", False):
        st.info("Sign in to continue.")
        return False

    st.success("Authenticated")
    return True


def _store_selector() -> tuple[str, dict]:
    store_labels = {f"{cfg['name']} ({key})": key for key, cfg in STORES.items()}
    selected_label = st.selectbox("Store", options=list(store_labels.keys()))
    selected_key = store_labels[selected_label]
    return selected_key, STORES[selected_key]


def _resolve_floor_paths(store_cfg: dict, floor_idx: int) -> tuple[Path, Path]:
    floor_key = FLOOR_FILE_NAMES[list(FLOOR_FILE_NAMES.keys())[floor_idx]]
    map_dir = Path(store_cfg.get("map_dir", "data/maps"))
    graph_dir = Path(store_cfg.get("graph_dir", "data/graphs"))
    return map_dir / f"{floor_key}.png", graph_dir / f"{floor_key}.json"


def _product_editor() -> None:
    st.subheader("📦 Product and Shop Editor")
    products = load_products()
    if not products:
        st.info("No products are currently stored.")
        return

    names = sorted(products.keys())
    selected = st.selectbox("Select product", options=names)
    payload = dict(products[selected])

    col1, col2, col3 = st.columns(3)
    with col1:
        floor = st.selectbox("Floor", options=list(FLOOR_NAMES.keys()), index=int(payload.get("floor", 1)))
        x = st.number_input("X", value=float(payload.get("x", 0.0)))
        y = st.number_input("Y", value=float(payload.get("y", 0.0)))
    with col2:
        nearest_node = st.text_input("Nearest node", value=str(payload.get("nearest_node", "")))
        opening_hours = st.text_input("Opening hours", value=str(payload.get("opening_hours", "")))
        category = st.text_input("Category", value=str(payload.get("category", "")))
    with col3:
        note = st.text_input("Note", value=str(payload.get("note", "")))
        rating = st.number_input("Rating", min_value=0.0, max_value=5.0, step=0.5, value=float(payload.get("rating") or 0.0))

    save_col, delete_col = st.columns(2)
    with save_col:
        if st.button("Save product changes", use_container_width=True, type="primary"):
            updated = {
                "floor": int(floor),
                "x": float(x),
                "y": float(y),
                "nearest_node": nearest_node.strip(),
                "note": note.strip(),
                "opening_hours": opening_hours.strip(),
                "category": category.strip(),
                "timestamp": payload.get("timestamp", ""),
                "rating": float(rating),
            }
            save_products({selected: updated})
            st.success("Product updated")
            st.rerun()

    with delete_col:
        if st.button("Delete product", use_container_width=True):
            delete_product(selected)
            st.warning("Product deleted")
            st.rerun()


def _upload_floor_plan_and_autograph(store_cfg: dict) -> None:
    st.subheader("🗺️ Floor Plan Upload and Graph Auto-Generation")
    floor_idx = st.selectbox("Floor for upload", options=list(FLOOR_NAMES.keys()), format_func=lambda x: FLOOR_NAMES[x], key="upload_floor")
    map_path, graph_path = _resolve_floor_paths(store_cfg, floor_idx)

    upload = st.file_uploader("Upload floor plan image", type=["png", "jpg", "jpeg"], key="floor_upload")
    auto_generate = st.checkbox("Auto-generate starter graph from image", value=True)

    if upload and st.button("Save floor plan", type="primary"):
        map_path.parent.mkdir(parents=True, exist_ok=True)
        graph_path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.open(upload)
        image.save(map_path)

        if auto_generate:
            graph = generate_graph_from_image_size(image.width, image.height, FLOOR_NAMES[floor_idx])
            save_json(graph_path, graph)
            st.success(f"Saved map and auto-generated graph at {graph_path}")
        else:
            st.success(f"Saved map at {map_path}")


def _graph_editor(store_cfg: dict) -> None:
    st.subheader("🧩 Graph Editor")
    floor_idx = st.selectbox("Floor", options=list(FLOOR_NAMES.keys()), format_func=lambda x: FLOOR_NAMES[x], key="graph_floor")
    map_path, graph_path = _resolve_floor_paths(store_cfg, floor_idx)

    if not map_path.exists():
        st.warning("Upload a floor plan first to use graph editor.")
        return

    graph = load_json(graph_path, default={"nodes": {}, "edges": {}})
    graph.setdefault("nodes", {})
    graph.setdefault("edges", {})

    map_img = render_floor_map(
        str(map_path),
        graph["nodes"],
        show_waypoints=True,
        products={},
    )
    coords = streamlit_image_coordinates(map_img, key=f"graph_editor_map_{floor_idx}", use_column_width="always")
    if coords:
        st.session_state["graph_click_x"] = int(coords["x"])
        st.session_state["graph_click_y"] = int(coords["y"])

    click_x = int(st.session_state.get("graph_click_x", 0))
    click_y = int(st.session_state.get("graph_click_y", 0))
    st.caption(f"Selected position: x={click_x}, y={click_y}")

    st.markdown("### Node editing")
    node_id = st.text_input("Node id", value="")
    node_label = st.text_input("Node label", value="")
    node_type = st.selectbox("Node type", options=["corridor", "entrance", "stairs", "service", "store"])

    add_col, remove_col = st.columns(2)
    with add_col:
        if st.button("Add or update node", use_container_width=True):
            if not node_id.strip():
                st.error("Node id is required")
            else:
                graph["nodes"][node_id.strip()] = {
                    "x": click_x,
                    "y": click_y,
                    "label": node_label.strip() or node_id.strip(),
                    "type": node_type,
                }
                graph["edges"].setdefault(node_id.strip(), {})
                save_json(graph_path, graph)
                st.success("Node saved")
                st.rerun()

    with remove_col:
        if st.button("Remove node", use_container_width=True):
            target = node_id.strip()
            if target in graph["nodes"]:
                graph["nodes"].pop(target, None)
                graph["edges"].pop(target, None)
                for neighbours in graph["edges"].values():
                    neighbours.pop(target, None)
                save_json(graph_path, graph)
                st.success("Node removed")
                st.rerun()
            else:
                st.warning("Node not found")

    st.markdown("### Edge editing")
    node_options = sorted(graph["nodes"].keys())
    if len(node_options) < 2:
        st.info("Add at least two nodes before creating edges.")
        return

    from_node = st.selectbox("From", options=node_options, key="edge_from")
    to_node = st.selectbox("To", options=node_options, key="edge_to")
    auto_weight = st.checkbox("Auto-calc weight from coordinates", value=True)
    weight_default = 1.0
    if auto_weight and from_node in graph["nodes"] and to_node in graph["nodes"]:
        ax, ay = graph["nodes"][from_node]["x"], graph["nodes"][from_node]["y"]
        bx, by = graph["nodes"][to_node]["x"], graph["nodes"][to_node]["y"]
        weight_default = float(((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5)

    weight = st.number_input("Weight", min_value=0.1, value=float(weight_default), step=1.0)
    undirected = st.checkbox("Add reverse edge", value=True)

    edge_add_col, edge_remove_col = st.columns(2)
    with edge_add_col:
        if st.button("Add or update edge", use_container_width=True):
            graph["edges"].setdefault(from_node, {})[to_node] = float(weight)
            if undirected:
                graph["edges"].setdefault(to_node, {})[from_node] = float(weight)
            save_json(graph_path, graph)
            st.success("Edge saved")
            st.rerun()

    with edge_remove_col:
        if st.button("Remove edge", use_container_width=True):
            graph["edges"].setdefault(from_node, {}).pop(to_node, None)
            if undirected:
                graph["edges"].setdefault(to_node, {}).pop(from_node, None)
            save_json(graph_path, graph)
            st.success("Edge removed")
            st.rerun()


def _analytics_and_logs() -> None:
    st.subheader("📈 Analytics and Error Logs")
    analytics = AnalyticsStore()

    top_search = analytics.top_search_terms(limit=10)
    top_routes = analytics.top_routes(limit=10)
    summary = analytics.algorithm_summary()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Top Searches")
        if top_search:
            st.dataframe([{"term": t, "count": c} for t, c in top_search], use_container_width=True)
        else:
            st.caption("No search data yet")

        st.markdown("#### Top Routes")
        if top_routes:
            st.dataframe([{"route": r, "count": c} for r, c in top_routes], use_container_width=True)
        else:
            st.caption("No route data yet")

    with col2:
        st.markdown("#### Algorithm Summary")
        if summary:
            rows = []
            for algo, stats in summary.items():
                rows.append(
                    {
                        "algorithm": algo,
                        "runs": int(stats["runs"]),
                        "avg_time_us": round(float(stats["avg_time_us"]), 2),
                        "avg_nodes_visited": round(float(stats["avg_nodes_visited"]), 2),
                        "success_rate": round(float(stats["success_rate"]) * 100.0, 1),
                    }
                )
            st.dataframe(rows, use_container_width=True)
        else:
            st.caption("No algorithm data yet")

    log_path = Path("data/app.log")
    st.markdown("#### Recent Log Lines")
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8").splitlines()
        st.code("\n".join(lines[-120:]), language="text")
    else:
        st.caption("Log file not found")


def _onboarding_tools() -> None:
    st.subheader("🚀 One-Click Store Onboarding")
    with st.form("onboard_store_form"):
        store_id = st.text_input("Store id", placeholder="my_new_mall")
        store_name = st.text_input("Store name", placeholder="My New Mall")
        lat = st.number_input("Latitude", value=0.0, format="%.6f")
        lng = st.number_input("Longitude", value=0.0, format="%.6f")
        template_store = st.text_input("Template store key", value="demo")
        submitted = st.form_submit_button("Scaffold store")

    if submitted:
        created = scaffold_store(
            store_id=store_id,
            store_name=store_name,
            lat=float(lat),
            lng=float(lng),
            template_store=template_store,
            stores_json_path=Path("data/stores.json"),
            stores_root=Path("data/stores"),
        )
        st.success("Store scaffold created")
        st.code("\n".join(created), language="text")


if _auth_gate():
    selected_store_key, selected_store_cfg = _store_selector()
    st.caption(f"Managing store: {selected_store_key}")

    tabs = st.tabs(
        [
            "Products",
            "Floor Upload",
            "Graph Editor",
            "Analytics & Logs",
            "Onboarding",
        ]
    )

    with tabs[0]:
        _product_editor()
    with tabs[1]:
        _upload_floor_plan_and_autograph(selected_store_cfg)
    with tabs[2]:
        _graph_editor(selected_store_cfg)
    with tabs[3]:
        _analytics_and_logs()
    with tabs[4]:
        _onboarding_tools()
