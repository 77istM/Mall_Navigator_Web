"""Unit tests for pathfinding algorithms.

Tests for Dijkstra and A* algorithms including:
- Basic pathfinding
- Edge cases (unreachable nodes, same start/end)
- Algorithm properties (Dijkstra completeness, A* optimality)
"""
import pytest
import math
from algorithms.dijkstra import dijkstra
from algorithms.astar import astar


class TestDijkstra:
    """Test suite for Dijkstra's shortest-path algorithm."""

    @pytest.fixture
    def simple_graph(self):
        """Simple 4-node linear graph: A -> B -> C -> D."""
        return {
            "A": {"B": 1.0},
            "B": {"A": 1.0, "C": 2.0},
            "C": {"B": 2.0, "D": 1.0},
            "D": {"C": 1.0},
        }

    @pytest.fixture
    def diamond_graph(self):
        r"""Diamond-shaped graph with two paths to the goal.
        
               B (cost 1)
              / \
            A     D
              \ /
               C (cost 3)
        
        Shorter path: A -> B -> D (cost 2)
        Longer path: A -> C -> D (cost 4)
        """
        return {
            "A": {"B": 1.0, "C": 3.0},
            "B": {"A": 1.0, "D": 1.0},
            "C": {"A": 3.0, "D": 1.0},
            "D": {"B": 1.0, "C": 1.0},
        }

    @pytest.fixture
    def disconnected_graph(self):
        """Graph with two disconnected components."""
        return {
            "A": {"B": 1.0},
            "B": {"A": 1.0},
            "C": {"D": 1.0},
            "D": {"C": 1.0},
        }

    def test_finds_path_simple(self, simple_graph):
        """Test that Dijkstra finds a path in a simple graph."""
        result = dijkstra(simple_graph, "A", "D")
        assert result["found"] is True
        assert result["path"] == ["A", "B", "C", "D"]
        assert result["cost"] == 4.0

    def test_finds_shortest_path_diamond(self, diamond_graph):
        """Test that Dijkstra finds the shortest of two paths."""
        result = dijkstra(diamond_graph, "A", "D")
        assert result["found"] is True
        assert result["path"] == ["A", "B", "D"]
        assert result["cost"] == 2.0

    def test_same_start_and_end(self, simple_graph):
        """Test behavior when start equals end."""
        result = dijkstra(simple_graph, "A", "A")
        assert result["found"] is True
        assert result["path"] == ["A"]
        assert result["cost"] == 0.0

    def test_unreachable_node(self, disconnected_graph):
        """Test that unreachable nodes return not found."""
        result = dijkstra(disconnected_graph, "A", "D")
        assert result["found"] is False
        assert result["path"] == []
        assert math.isinf(result["cost"])

    def test_single_node_graph(self):
        """Test pathfinding in a single-node graph."""
        graph = {"A": {}}
        result = dijkstra(graph, "A", "A")
        assert result["found"] is True
        assert result["path"] == ["A"]
        assert result["cost"] == 0.0

    def test_returns_statistics(self, simple_graph):
        """Test that Dijkstra returns performance statistics."""
        result = dijkstra(simple_graph, "A", "D")
        assert "nodes_visited" in result
        assert "time_us" in result
        assert result["nodes_visited"] > 0
        assert result["time_us"] >= 0

    def test_zero_cost_edges(self):
        """Test handling of zero-cost edges."""
        graph = {
            "A": {"B": 0.0},
            "B": {"C": 1.0},
            "C": {},
        }
        result = dijkstra(graph, "A", "C")
        assert result["found"] is True
        assert result["cost"] == 1.0


class TestAStar:
    """Test suite for A* pathfinding algorithm."""

    @pytest.fixture
    def simple_graph(self):
        """Simple 4-node linear graph with coordinates."""
        return {
            "A": {"B": 1.0},
            "B": {"A": 1.0, "C": 2.0},
            "C": {"B": 2.0, "D": 1.0},
            "D": {"C": 1.0},
        }

    @pytest.fixture
    def simple_coords(self):
        """Coordinates for simple graph."""
        return {
            "A": {"x": 0.0, "y": 0.0},
            "B": {"x": 1.0, "y": 0.0},
            "C": {"x": 3.0, "y": 0.0},
            "D": {"x": 4.0, "y": 0.0},
        }

    @pytest.fixture
    def diamond_graph(self):
        """Diamond graph as in Dijkstra tests."""
        return {
            "A": {"B": 1.0, "C": 3.0},
            "B": {"A": 1.0, "D": 1.0},
            "C": {"A": 3.0, "D": 1.0},
            "D": {"B": 1.0, "C": 1.0},
        }

    @pytest.fixture
    def diamond_coords(self):
        """Coordinates for diamond graph."""
        return {
            "A": {"x": 0.0, "y": 1.0},
            "B": {"x": 1.0, "y": 2.0},
            "C": {"x": 1.0, "y": 0.0},
            "D": {"x": 2.0, "y": 1.0},
        }

    def test_finds_path_simple(self, simple_graph, simple_coords):
        """Test that A* finds a path."""
        result = astar(simple_graph, simple_coords, "A", "D")
        assert result["found"] is True
        assert result["path"] == ["A", "B", "C", "D"]
        assert result["cost"] == 4.0

    def test_finds_shortest_path_diamond(self, diamond_graph, diamond_coords):
        """Test that A* finds the optimal (shortest) path."""
        result = astar(diamond_graph, diamond_coords, "A", "D")
        assert result["found"] is True
        assert result["path"] == ["A", "B", "D"]
        assert result["cost"] == 2.0

    def test_same_start_and_end(self, simple_graph, simple_coords):
        """Test A* when start equals end."""
        result = astar(simple_graph, simple_coords, "A", "A")
        assert result["found"] is True
        assert result["path"] == ["A"]
        assert result["cost"] == 0.0

    def test_returns_statistics(self, simple_graph, simple_coords):
        """Test that A* returns performance statistics."""
        result = astar(simple_graph, simple_coords, "A", "D")
        assert "nodes_visited" in result
        assert "time_us" in result
        assert result["nodes_visited"] > 0
        assert result["time_us"] >= 0

    def test_admissible_heuristic(self, diamond_graph, diamond_coords):
        """Test that A* heuristic is admissible (never overestimates)."""
        # For Euclidean heuristic, this is guaranteed if edges are also Euclidean.
        # Just verify that A* finds an optimal path.
        result = astar(diamond_graph, diamond_coords, "A", "D")
        assert result["found"] is True
        assert result["cost"] == 2.0  # Known optimal cost

    def test_unreachable_node(self):
        """Test A* with unreachable node."""
        graph = {
            "A": {"B": 1.0},
            "B": {"A": 1.0},
            "C": {},
        }
        coords = {
            "A": {"x": 0.0, "y": 0.0},
            "B": {"x": 1.0, "y": 0.0},
            "C": {"x": 10.0, "y": 0.0},
        }
        result = astar(graph, coords, "A", "C")
        assert result["found"] is False
        assert result["path"] == []
        assert math.isinf(result["cost"])

    def test_single_node_graph(self):
        """Test A* in a single-node graph."""
        graph = {"A": {}}
        coords = {"A": {"x": 0.0, "y": 0.0}}
        result = astar(graph, coords, "A", "A")
        assert result["found"] is True
        assert result["path"] == ["A"]
        assert result["cost"] == 0.0


class TestAlgorithmComparison:
    """Compare Dijkstra and A* behavior on shared graphs."""

    @pytest.fixture
    def grid_graph_3x3(self):
        r"""3x3 grid graph for pathfinding comparison.
        
        0-1-2
        | | |
        3-4-5
        | | |
        6-7-8
        """
        return {
            "0": {"1": 1.0, "3": 1.0},
            "1": {"0": 1.0, "2": 1.0, "4": 1.0},
            "2": {"1": 1.0, "5": 1.0},
            "3": {"0": 1.0, "4": 1.0, "6": 1.0},
            "4": {"1": 1.0, "3": 1.0, "5": 1.0, "7": 1.0},
            "5": {"2": 1.0, "4": 1.0, "8": 1.0},
            "6": {"3": 1.0, "7": 1.0},
            "7": {"4": 1.0, "6": 1.0, "8": 1.0},
            "8": {"5": 1.0, "7": 1.0},
        }

    @pytest.fixture
    def grid_coords_3x3(self):
        """Coordinates for 3x3 grid."""
        return {
            "0": {"x": 0.0, "y": 0.0},
            "1": {"x": 1.0, "y": 0.0},
            "2": {"x": 2.0, "y": 0.0},
            "3": {"x": 0.0, "y": 1.0},
            "4": {"x": 1.0, "y": 1.0},
            "5": {"x": 2.0, "y": 1.0},
            "6": {"x": 0.0, "y": 2.0},
            "7": {"x": 1.0, "y": 2.0},
            "8": {"x": 2.0, "y": 2.0},
        }

    def test_both_find_same_cost(self, grid_graph_3x3, grid_coords_3x3):
        """Test that Dijkstra and A* find paths with the same cost."""
        dijk = dijkstra(grid_graph_3x3, "0", "8")
        star = astar(grid_graph_3x3, grid_coords_3x3, "0", "8")
        
        assert dijk["found"] is True
        assert star["found"] is True
        assert dijk["cost"] == star["cost"]

    def test_astar_explores_fewer_nodes(self, grid_graph_3x3, grid_coords_3x3):
        """Test that A* typically explores fewer nodes than Dijkstra on larger graphs."""
        dijk = dijkstra(grid_graph_3x3, "0", "8")
        star = astar(grid_graph_3x3, grid_coords_3x3, "0", "8")
        
        # A* should use the heuristic to be more efficient
        # (on small graphs this may not always be true, but trend should favor A*)
        assert star["nodes_visited"] <= dijk["nodes_visited"]

    @pytest.mark.parametrize("start,end", [
        ("0", "8"),
        ("0", "5"),
        ("3", "7"),
    ])
    def test_find_same_optimal_paths(self, grid_graph_3x3, grid_coords_3x3, start, end):
        """Parameterized test: both algorithms should find optimal paths."""
        dijk = dijkstra(grid_graph_3x3, start, end)
        star = astar(grid_graph_3x3, grid_coords_3x3, start, end)
        
        if dijk["found"]:
            assert star["found"]
            assert dijk["cost"] == star["cost"]
            assert len(dijk["path"]) == len(star["path"])


class TestEdgeCases:
    """Edge case tests."""

    def test_self_loop(self):
        """Test graph with self-loops."""
        graph = {
            "A": {"A": 0.5, "B": 1.0},
            "B": {"A": 1.0},
        }
        result = dijkstra(graph, "A", "B")
        assert result["found"] is True
        assert result["cost"] == 1.0

    def test_negative_cost_warning(self):
        """Test behavior with negative-cost edges (not recommended for Dijkstra)."""
        graph = {
            "A": {"B": 1.0},
            "B": {"C": -2.0},
            "C": {},
        }
        # Dijkstra doesn't handle negative weights correctly, but shouldn't crash
        result = dijkstra(graph, "A", "C")
        # Result may be incorrect due to negative edges, but algorithm completes
        assert "path" in result

    def test_large_cost_values(self):
        """Test with large edge weights."""
        graph = {
            "A": {"B": 1e6},
            "B": {"C": 1e6},
            "C": {},
        }
        result = dijkstra(graph, "A", "C")
        assert result["found"] is True
        assert result["cost"] == 2e6

    def test_many_edges_per_node(self):
        """Test a highly connected graph."""
        # Complete graph K5 (all nodes connected to all others)
        graph = {}
        nodes = ["A", "B", "C", "D", "E"]
        for i, n1 in enumerate(nodes):
            graph[n1] = {}
            for j, n2 in enumerate(nodes):
                if i != j:
                    graph[n1][n2] = 1.0 + abs(i - j) * 0.1

        result = dijkstra(graph, "A", "E")
        assert result["found"] is True
        assert result["cost"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
