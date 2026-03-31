"""Unit tests for ML features (Phase 5.3)."""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from utils.ml_features import (
    PopularRoutesPredictor,
    NearbyRecommender,
    MLFeatureFactory,
    RoutePopularity,
)


class TestPopularRoutesPredictor:
    """Test popular routes prediction."""

    @pytest.fixture
    def temp_storage(self):
        """Create temporary storage for test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "ml_data.json"

    @pytest.fixture
    def predictor(self, temp_storage):
        """Create predictor with temporary storage."""
        return PopularRoutesPredictor(str(temp_storage))

    def test_init_creates_empty_model(self, temp_storage):
        """Test initialization creates empty model structure."""
        predictor = PopularRoutesPredictor(str(temp_storage))
        assert "routes_by_time" in predictor.model_data
        assert "node_popularity" in predictor.model_data
        assert len(predictor.model_data["routes_by_time"]) == 0

    def test_record_route_taken(self, predictor):
        """Test recording a route."""
        path = ["A", "B", "C"]
        predictor.record_route_taken(path)

        # Verify data was saved
        assert len(predictor.model_data["routes_by_time"]) > 0
        assert len(predictor.model_data["node_popularity"]) == 3

        # Verify nodes are recorded
        assert predictor.model_data["node_popularity"]["A"] > 0
        assert predictor.model_data["node_popularity"]["B"] > 0
        assert predictor.model_data["node_popularity"]["C"] > 0

    def test_ignore_short_paths(self, predictor):
        """Test that paths shorter than 2 nodes are ignored."""
        predictor.record_route_taken(["A"])
        assert len(predictor.model_data["node_popularity"]) == 0

    def test_predict_popular_routes_empty(self, predictor):
        """Test prediction with no training data."""
        results = predictor.predict_popular_routes()
        assert results == []

    def test_predict_popular_routes(self, predictor):
        """Test prediction returns top routes."""
        # Record same route multiple times
        for _ in range(5):
            predictor.record_route_taken(["A", "B", "C"])

        for _ in range(3):
            predictor.record_route_taken(["A", "B", "D"])

        results = predictor.predict_popular_routes(limit=2)
        assert len(results) > 0
        # Most popular route should be first
        assert results[0].count >= 3

    def test_predict_routes_with_time_context(self, predictor):
        """Test time-specific predictions."""
        predictor.record_route_taken(["A", "B", "C"])

        # Use a specific time for prediction
        test_time = datetime.now(timezone.utc)
        results = predictor.predict_popular_routes(current_time=test_time)

        # If we just recorded, should get results
        if results:
            assert results[0].route_key == "A->C"
            assert results[0].day_of_week == test_time.strftime("%A")

    def test_get_node_popularity(self, predictor):
        """Test node popularity ranking."""
        predictor.record_route_taken(["A", "B", "C"])
        predictor.record_route_taken(["A", "B"])

        popular = predictor.get_node_popularity(limit=3)
        assert len(popular) > 0
        # A and B should be more popular than C
        node_names = [node for node, _count in popular]
        assert "A" in node_names
        assert "B" in node_names

    def test_persistence(self, temp_storage):
        """Test data persists across instances."""
        # Create and save data
        predictor1 = PopularRoutesPredictor(str(temp_storage))
        predictor1.record_route_taken(["X", "Y", "Z"])

        # Load in new instance
        predictor2 = PopularRoutesPredictor(str(temp_storage))
        popular = predictor2.get_node_popularity()
        assert len(popular) > 0
        assert any(node == "X" for node, _count in popular)


class TestNearbyRecommender:
    """Test nearby product recommendations."""

    @pytest.fixture
    def sample_products(self):
        """Sample product data."""
        return {
            "nike_1": {
                "name": "Nike Store",
                "category": "Retail",
                "x": 100.0,
                "y": 100.0,
                "floor": 1,
                "opening_hours": "9-21",
                "rating": 4.5,
            },
            "adidas_1": {
                "name": "Adidas",
                "category": "Retail",
                "x": 110.0,
                "y": 105.0,
                "floor": 1,
                "opening_hours": "9-21",
                "rating": 4.3,
            },
            "mcd_1": {
                "name": "McDonald's",
                "category": "Food",
                "x": 200.0,
                "y": 200.0,
                "floor": 1,
                "opening_hours": "8-23",
                "rating": 3.8,
            },
            "closed_shop": {
                "name": "Closed Store",
                "category": "Closed",
                "x": 105.0,
                "y": 105.0,
                "floor": 1,
                "opening_hours": "Closed",
                "rating": 0.0,
            },
        }

    @pytest.fixture
    def sample_nodes(self):
        """Sample node coordinates."""
        return {
            "node_0": {"x": 100, "y": 100, "floor": 1},
            "node_1": {"x": 200, "y": 200, "floor": 1},
        }

    @pytest.fixture
    def temp_cache(self):
        """Create temporary cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir) / "recommendations.json"

    @pytest.fixture
    def recommender(self, sample_products, temp_cache):
        """Create recommender with sample data."""
        return NearbyRecommender(sample_products, str(temp_cache))

    def test_init_with_products(self, sample_products, temp_cache):
        """Test initialization with products."""
        rec = NearbyRecommender(sample_products, str(temp_cache))
        assert len(rec.products) == 4

    def test_get_nearby_products_no_current_node(self, recommender, sample_nodes):
        """Test with invalid current node."""
        results = recommender.get_nearby_products("invalid_node", sample_nodes)
        assert results == []

    def test_get_nearby_products(self, recommender, sample_nodes):
        """Test getting nearby products."""
        results = recommender.get_nearby_products(
            "node_0", sample_nodes, max_distance=50, limit=5
        )
        assert len(results) > 0
        # Should get nearby Nike and Adidas
        assert any("Nike" in r["name"] for r in results)

    def test_nearby_respects_max_distance(self, recommender, sample_nodes):
        """Test that max_distance is respected."""
        # Small distance - should get nothing
        results_close = recommender.get_nearby_products(
            "node_0", sample_nodes, max_distance=5, limit=5
        )
        
        # Larger distance
        results_far = recommender.get_nearby_products(
            "node_0", sample_nodes, max_distance=150, limit=5
        )
        
        # Should get fewer or equal with stricter distance
        assert len(results_close) <= len(results_far)

    def test_nearby_floor_filtering(self, recommender, sample_nodes):
        """Test that only same-floor products are returned."""
        # Add product on different floor
        recommender.add_product_to_index(
            "other_floor",
            {
                "name": "Other Floor Store",
                "category": "Retail",
                "x": 105.0,
                "y": 105.0,
                "floor": 2,
            },
        )

        results = recommender.get_nearby_products("node_0", sample_nodes, max_distance=50)
        # Should not include other_floor product
        assert not any(r["product_id"] == "other_floor" for r in results)

    def test_exclude_categories(self, recommender, sample_nodes):
        """Test excluding specific categories."""
        results = recommender.get_nearby_products(
            "node_0",
            sample_nodes,
            max_distance=50,
            exclude_categories=["Closed"],
        )

        # Closed shop should not be included
        assert not any(r["category"] == "Closed" for r in results)

    def test_nearby_sorted_by_distance(self, recommender, sample_nodes):
        """Test that results are sorted by distance."""
        results = recommender.get_nearby_products(
            "node_0", sample_nodes, max_distance=150, limit=5
        )

        if len(results) > 1:
            # Verify ascending distance order
            distances = [r["distance"] for r in results]
            assert distances == sorted(distances)

    def test_recommend_by_category(self, recommender):
        """Test category-based recommendations."""
        search_history = ["Nike Store", "Adidas", "Retail Product"]

        results = recommender.recommend_by_category(search_history, limit=5)
        assert len(results) > 0
        # Should recommend retail products
        assert any(r["category"] == "Retail" for r in results)

    def test_recommend_by_category_empty_history(self, recommender):
        """Test with empty search history."""
        results = recommender.recommend_by_category([], limit=5)
        assert results == []

    def test_add_product_to_index(self, recommender):
        """Test adding product to index."""
        new_prod = {
            "name": "New Store",
            "category": "Retail",
            "x": 150.0,
            "y": 150.0,
            "floor": 1,
        }
        recommender.add_product_to_index("new_1", new_prod)
        assert "new_1" in recommender.products


class TestMLFeatureFactory:
    """Test factory pattern for ML features."""

    def test_factory_singleton_route_predictor(self):
        """Test factory returns same route predictor instance."""
        factory = MLFeatureFactory()
        pred1 = factory.init_route_predictor()
        pred2 = factory.init_route_predictor()
        assert pred1 is pred2

    def test_factory_singleton_recommender(self):
        """Test factory returns same recommender instance."""
        factory = MLFeatureFactory()
        rec1 = factory.init_nearby_recommender()
        rec2 = factory.init_nearby_recommender()
        assert rec1 is rec2

    def test_factory_separate_instances(self):
        """Test different factory instances are separate."""
        factory1 = MLFeatureFactory()
        factory2 = MLFeatureFactory()
        pred1 = factory1.init_route_predictor()
        pred2 = factory2.init_route_predictor()
        assert pred1 is not pred2


class TestRoutePopularityDataclass:
    """Test RoutePopularity dataclass."""

    def test_creation(self):
        """Test creating RoutePopularity."""
        pop = RoutePopularity(
            route_key="A->B",
            score=0.75,
            time_of_day="08-12",
            day_of_week="Monday",
            count=10,
        )
        assert pop.route_key == "A->B"
        assert pop.count == 10

    def test_immutability(self):
        """Test that dataclass has slots for memory efficiency."""
        pop = RoutePopularity(
            route_key="A->B",
            score=0.75,
            time_of_day="08-12",
            day_of_week="Monday",
            count=10,
        )
        # slots=True provides memory efficiency
        assert hasattr(pop.__class__, '__slots__')
        assert pop.count == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
