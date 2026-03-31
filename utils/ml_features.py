"""Machine Learning features for smart routing recommendations (Phase 5.3).

This module provides ML-powered recommendations:
1. Popular routes: Predict trending routes based on time of day/day of week
2. Nearby recommendations: Suggest products near user location using content-based filtering

MVP approach: Lightweight sklearn-based models with data collection scaffolding.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
import logging

import numpy as np
from datetime import datetime as dt

DEFAULT_ML_DATA_PATH = "data/ml_training_data.json"
DEFAULT_RECOMMENDATIONS_PATH = "data/recommendations_cache.json"

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RoutePopularity:
    """Popularity score for a route at a given time."""

    route_key: str
    score: float
    time_of_day: str
    day_of_week: str
    count: int


class PopularRoutesPredictor:
    """Predicts popular routes based on temporal patterns (time of day, day of week)."""

    def __init__(self, storage_path: str = DEFAULT_ML_DATA_PATH) -> None:
        self.storage_path = Path(storage_path)
        self.model_data: dict[str, Any] = {}
        self._load_or_init()

    def _load_or_init(self) -> None:
        """Load existing training data or initialize empty."""
        if self.storage_path.exists():
            try:
                raw = self.storage_path.read_text(encoding="utf-8")
                self.model_data = json.loads(raw)
                logger.info(f"Loaded ML training data from {self.storage_path}")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to load ML data, initializing empty: {e}")
                self._init_empty()
        else:
            self._init_empty()

    def _init_empty(self) -> None:
        """Initialize empty training data structure."""
        self.model_data = {
            "routes_by_time": {},  # (time_of_day, day_of_week) -> {route_key -> count}
            "node_popularity": {},  # node_id -> count across all times
        }

    def _save(self) -> None:
        """Persist training data to disk."""
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.storage_path.write_text(
            json.dumps(self.model_data, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def record_route_taken(self, path: list[str]) -> None:
        """Record a route being taken (for training)."""
        if len(path) < 2:
            return

        now = datetime.now(timezone.utc)
        hour = now.hour
        day_name = now.strftime("%A")  # e.g., "Monday"

        # Bucket time into 4-hour windows (0-4, 4-8, 8-12, 12-16, 16-20, 20-24)
        time_bucket = f"{(hour // 4) * 4:02d}-{((hour // 4) + 1) * 4:02d}"
        time_key = f"{time_bucket}_{day_name}"

        route_key = f"{path[0]}->{path[-1]}"

        # Update route popularity for this time slot
        if time_key not in self.model_data["routes_by_time"]:
            self.model_data["routes_by_time"][time_key] = {}

        routes_at_time = self.model_data["routes_by_time"][time_key]
        routes_at_time[route_key] = routes_at_time.get(route_key, 0) + 1

        # Update node popularity
        for node in path:
            self.model_data["node_popularity"][node] = (
                self.model_data["node_popularity"].get(node, 0) + 1
            )

        self._save()

    def predict_popular_routes(
        self, limit: int = 3, current_time: datetime | None = None
    ) -> list[RoutePopularity]:
        """
        Predict top N popular routes for current time slot.

        Returns list of RoutePopularity sorted by score (descending).
        """
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        hour = current_time.hour
        day_name = current_time.strftime("%A")
        time_bucket = f"{(hour // 4) * 4:02d}-{((hour // 4) + 1) * 4:02d}"
        time_key = f"{time_bucket}_{day_name}"

        # Get routes for this time slot
        routes_at_time = self.model_data.get("routes_by_time", {}).get(time_key, {})

        if not routes_at_time:
            logger.debug(f"No training data for time slot {time_key}")
            return []

        # Sort by count (popularity)
        sorted_routes = sorted(
            routes_at_time.items(), key=lambda x: x[1], reverse=True
        )[:limit]

        results = []
        for route_key, count in sorted_routes:
            score = float(count) / max(1, len(self.model_data["node_popularity"]))
            results.append(
                RoutePopularity(
                    route_key=route_key,
                    score=score,
                    time_of_day=time_bucket,
                    day_of_week=day_name,
                    count=count,
                )
            )

        return results

    def get_node_popularity(self, limit: int = 5) -> list[tuple[str, int]]:
        """Get top N most visited nodes (heatmap data)."""
        node_pop = self.model_data.get("node_popularity", {})
        sorted_nodes = sorted(node_pop.items(), key=lambda x: x[1], reverse=True)[:limit]
        return sorted_nodes


class NearbyRecommender:
    """Content-based recommender for products nearby user location."""

    def __init__(
        self,
        products: dict[str, dict[str, Any]] | None = None,
        cache_path: str = DEFAULT_RECOMMENDATIONS_PATH,
    ) -> None:
        self.products = products or {}
        self.cache_path = Path(cache_path)
        self.recommendation_cache: dict[str, list[dict[str, Any]]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cached recommendations if available."""
        if self.cache_path.exists():
            try:
                raw = self.cache_path.read_text(encoding="utf-8")
                self.recommendation_cache = json.loads(raw)
                logger.info(f"Loaded recommendation cache from {self.cache_path}")
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to load recommendation cache, starting fresh")
                self.recommendation_cache = {}

    def _save_cache(self) -> None:
        """Persist recommendation cache to disk."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(
            json.dumps(self.recommendation_cache, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def add_product_to_index(self, product_id: str, product: dict[str, Any]) -> None:
        """Add/update a product in the recommendation index."""
        self.products[product_id] = product

    def get_nearby_products(
        self,
        current_node: str,
        nodes: dict[str, dict[str, Any]],
        max_distance: float = 50.0,
        limit: int = 5,
        exclude_categories: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recommend products near current node (content-based filtering).

        Args:
            current_node: Current node ID
            nodes: Node coordinate dictionary {node_id -> {x, y, floor}}
            max_distance: Max pixel distance to consider "nearby" (roughly metres)
            limit: Max recommendations to return
            exclude_categories: Product categories to exclude (e.g., ["Closed"])

        Returns:
            List of recommended products with distance info
        """
        if current_node not in nodes:
            return []

        exclude_cats = set(exclude_categories or [])

        current_coords = nodes[current_node]
        current_x = float(current_coords.get("x", 0))
        current_y = float(current_coords.get("y", 0))
        current_floor = current_coords.get("floor", 0)

        recommendations = []
        for product_id, product in self.products.items():
            # Skip excluded categories
            category = product.get("category", "")
            if category in exclude_cats:
                continue

            # Product must be on same floor for "nearby" to make sense
            product_floor = product.get("floor")
            if product_floor != current_floor:
                continue

            # Calculate distance (simple Euclidean for MVP)
            product_x = product.get("x")
            product_y = product.get("y")
            if product_x is None or product_y is None:
                continue

            distance = ((current_x - product_x) ** 2 + (current_y - product_y) ** 2) ** 0.5

            if distance <= max_distance:
                recommendations.append(
                    {
                        "product_id": product_id,
                        "name": product.get("name", "Unknown"),
                        "category": category,
                        "distance": float(distance),
                        "floor": current_floor,
                        "opening_hours": product.get("opening_hours", "Unknown"),
                        "rating": product.get("rating", 0.0),
                    }
                )

        # Sort by distance and return top N
        recommendations.sort(key=lambda x: x["distance"])
        return recommendations[:limit]

    def recommend_by_category(
        self,
        user_search_history: list[str],
        limit: int = 5,
        exclude_categories: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Recommend products based on past search history (collaborative filtering MVP).

        Args:
            user_search_history: List of product names user has searched
            limit: Max recommendations
            exclude_categories: Categories to skip

        Returns:
            List of product recommendations
        """
        exclude_cats = set(exclude_categories or [])

        # Count category frequency in search history
        category_counts: dict[str, int] = {}
        for search_term in user_search_history:
            search_lower = search_term.lower()
            for prod_id, prod in self.products.items():
                if search_lower in prod.get("name", "").lower():
                    cat = prod.get("category", "unknown")
                    if cat not in exclude_cats:
                        category_counts[cat] = category_counts.get(cat, 0) + 1

        # Get products from top categories
        if not category_counts:
            return []

        top_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        recommendations = []

        for category, _count in top_categories:
            for prod_id, prod in self.products.items():
                if prod.get("category") == category:
                    recommendations.append(
                        {
                            "product_id": prod_id,
                            "name": prod.get("name", "Unknown"),
                            "category": category,
                            "rating": prod.get("rating", 0.0),
                            "opening_hours": prod.get("opening_hours", "Unknown"),
                        }
                    )

            if len(recommendations) >= limit:
                break

        return recommendations[:limit]


class MLFeatureFactory:
    """Factory to initialize and manage ML features."""

    def __init__(self) -> None:
        self.route_predictor: PopularRoutesPredictor | None = None
        self.nearby_recommender: NearbyRecommender | None = None

    def init_route_predictor(self, storage_path: str = DEFAULT_ML_DATA_PATH) -> PopularRoutesPredictor:
        """Lazy-initialize popular routes predictor."""
        if self.route_predictor is None:
            self.route_predictor = PopularRoutesPredictor(storage_path)
        return self.route_predictor

    def init_nearby_recommender(
        self,
        products: dict[str, dict[str, Any]] | None = None,
        cache_path: str = DEFAULT_RECOMMENDATIONS_PATH,
    ) -> NearbyRecommender:
        """Lazy-initialize nearby recommender."""
        if self.nearby_recommender is None:
            self.nearby_recommender = NearbyRecommender(products, cache_path)
        return self.nearby_recommender


# Global factory instance (Streamlit-safe with @st.cache_resource)
_ml_factory = MLFeatureFactory()


def get_ml_features() -> MLFeatureFactory:
    """Get singleton ML features factory."""
    return _ml_factory
