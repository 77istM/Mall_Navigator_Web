"""Streamlit UI component for ML recommendations (Phase 5.3)."""

from __future__ import annotations

from typing import Any
import streamlit as st

from utils.ml_features import PopularRoutesPredictor, NearbyRecommender


def render_popular_routes_panel(
    route_predictor: PopularRoutesPredictor,
    current_floor: int,
) -> None:
    """Render popular routes recommendations panel."""
    st.subheader("🔥 Popular Routes Right Now")

    with st.spinner("Analyzing traffic patterns..."):
        popular = route_predictor.predict_popular_routes(limit=3)

    if not popular:
        st.info("📊 Not enough data yet. Routes will appear as more users navigate.")
        return

    for i, route in enumerate(popular, 1):
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(f"**#{i}** {route.route_key}")
            with col2:
                st.metric("Users", route.count)
            with col3:
                st.metric("Score", f"{route.score:.2f}")

            # Show time context
            st.caption(
                f"📍 Popular {route.time_of_day} on {route.day_of_week}"
            )

            # "Take this route" button
            if st.button(
                f"Navigate via Route {i}",
                key=f"popular_route_{i}",
                use_container_width=True,
            ):
                start_raw, end_raw = route.route_key.split("->", maxsplit=1)

                def _parse_route_point(value: str) -> tuple[int, str]:
                    if ":" in value:
                        floor_text, node_id = value.split(":", maxsplit=1)
                        if floor_text.isdigit() and node_id:
                            return int(floor_text), node_id
                    return current_floor, value

                start_floor, start_node = _parse_route_point(start_raw)
                end_floor, end_node = _parse_route_point(end_raw)

                st.session_state.start_floor = start_floor
                st.session_state.start_node = start_node
                st.session_state.end_floor = end_floor
                st.session_state.end_node = end_node
                st.session_state.current_floor = end_floor
                st.session_state.selecting = "start"

                # Route results are recalculated only when Find Path is pressed.
                st.session_state.dijk_result = None
                st.session_state.star_result = None
                st.session_state.alt_routes = []

                st.success(f"✅ Route set: {start_node} → {end_node}. Press Find Path to run navigation.")


def render_nearby_recommendations_panel(
    recommender: NearbyRecommender,
    current_node: str,
    nodes: dict[str, dict[str, Any]],
    max_distance: float = 50.0,
) -> None:
    """Render nearby product recommendations panel."""
    st.subheader("🎯 Nearby Recommendations")

    with st.spinner("Finding nearby stores..."):
        nearby = recommender.get_nearby_products(
            current_node,
            nodes,
            max_distance=max_distance,
            limit=5,
            exclude_categories=["Closed"],
        )

    if not nearby:
        st.info(f"No nearby products within {max_distance}m on this floor.")
        return

    st.markdown(f"**Found {len(nearby)} nearby:**")

    for product in nearby:
        with st.container(border=True):
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                rating_stars = "⭐" * int(product.get("rating", 0))
                st.markdown(
                    f"**{product['name']}** {rating_stars}\n"
                    f"_{product['category']}_"
                )
            with col2:
                distance = product.get("distance", 0)
                st.metric("Distance", f"{distance:.0f}m")
            with col3:
                hours = product.get("opening_hours", "Unknown")
                st.caption(f"⏰ {hours}")

            # "Navigate to" button
            if st.button(
                "📍 Go Here",
                key=f"nearby_{product['product_id']}",
                use_container_width=True,
            ):
                product_node = min(
                    nodes,
                    key=lambda nid: (
                        (float(nodes[nid]["x"]) - float(recommender.products[product["product_id"]]["x"])) ** 2
                        + (float(nodes[nid]["y"]) - float(recommender.products[product["product_id"]]["y"])) ** 2
                    ),
                )

                st.session_state.end_node = product_node
                st.session_state.end_floor = int(product.get("floor", st.session_state.get("current_floor", 0)))
                st.session_state.current_floor = st.session_state.end_floor
                st.session_state.selecting = "start"
                st.session_state.selected_product = product["product_id"]

                st.session_state.dijk_result = None
                st.session_state.star_result = None
                st.session_state.alt_routes = []

                st.success(f"✅ Destination set to {product['name']}. Press Find Path to run navigation.")


def render_category_recommendations_panel(
    recommender: NearbyRecommender,
    search_history: list[str] = None,
) -> None:
    """Render category-based recommendations based on search history."""
    if not search_history:
        return

    st.subheader("💡 Based on Your Interests")

    with st.spinner("Finding recommendations..."):
        recommendations = recommender.recommend_by_category(
            search_history,
            limit=5,
            exclude_categories=["Closed"],
        )

    if not recommendations:
        return

    for product in recommendations:
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])

            with col1:
                rating_stars = "⭐" * int(product.get("rating", 0))
                st.markdown(
                    f"**{product['name']}** {rating_stars}\n"
                    f"_{product['category']}_"
                )
            with col2:
                st.caption(f"⏰ {product.get('opening_hours', 'Unknown')}")

            if st.button(
                "🔍 View",
                key=f"recommend_{product['product_id']}",
                use_container_width=True,
            ):
                st.session_state.selected_product = product["product_id"]
                st.info(f"Selected: {product['name']}")


def render_node_heatmap_legend(
    route_predictor: PopularRoutesPredictor,
) -> None:
    """Render legend for node popularity heatmap."""
    st.subheader("🔴 Hotspot Areas")

    with st.spinner("Computing hotspots..."):
        hotspots = route_predictor.get_node_popularity(limit=5)

    if not hotspots:
        st.info("No traffic data yet.")
        return

    st.markdown("**Most visited areas:**")
    for i, (node_id, visits) in enumerate(hotspots, 1):
        st.write(f"{i}. Node `{node_id}` — {visits} visits")


def render_ml_feature_panel(
    route_predictor: PopularRoutesPredictor | None,
    recommender: NearbyRecommender | None,
    current_node: str | None = None,
    nodes: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Main panel to render all ML features (for sidebar or main area)."""
    st.markdown("---")
    st.header("🤖 Smart Recommendations (ML)")

    col1, col2 = st.columns(2)

    with col1:
        if st.checkbox("Popular Routes", value=True, key="show_popular_routes"):
            if route_predictor:
                render_popular_routes_panel(route_predictor)
            else:
                st.warning("Route predictor not initialized")

    with col2:
        if st.checkbox("Hotspot Areas", value=False, key="show_hotspots"):
            if route_predictor:
                render_node_heatmap_legend(route_predictor)
            else:
                st.warning("Route predictor not initialized")

    if current_node and nodes and recommender:
        if st.checkbox("Nearby Stores", value=True, key="show_nearby"):
            render_nearby_recommendations_panel(recommender, current_node, nodes)


def init_ml_session_state() -> None:
    """Initialize ML-related session state."""
    if "selected_product" not in st.session_state:
        st.session_state.selected_product = None
