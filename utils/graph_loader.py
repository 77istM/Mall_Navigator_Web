"""Graph management utilities for optimized loading and caching.

Provides lazy loading, caching, and memory-efficient graph handling.
"""
import json
import os
from typing import Dict, Optional

from config import FLOORS, INTER_FLOOR_EDGES


def load_graph(floor_idx: int) -> Dict:
    """Load a single floor graph (lazy loading).
    
    Uses @st.cache_data to avoid reloading the same graph.
    Only loads the requested floor, not all three.
    
    Parameters
    ----------
    floor_idx : int
        Floor index (0=Lower, 1=Ground, 2=Upper)
    
    Returns
    -------
    dict
        Floor graph with 'nodes' and 'edges' keys
    """
    if floor_idx not in FLOORS:
        raise ValueError(f"Invalid floor index: {floor_idx}")
    
    graph_path = FLOORS[floor_idx]["graph"]
    
    if not os.path.exists(graph_path):
        raise FileNotFoundError(f"Graph not found: {graph_path}")
    
    with open(graph_path, encoding="utf-8") as f:
        return json.load(f)


# Decorator for caching individual floor graphs
def get_cached_graph(floor_idx: int) -> Dict:
    """Get a cached graph for a floor.
    
    This is meant to be called from within a Streamlit context
    where @st.cache_data is available.
    """
    # This function will be wrapped with @st.cache_data in app.py
    return load_graph(floor_idx)


def load_graphs(floor_indices: Optional[list[int]] = None) -> Dict[int, Dict]:
    """Load graphs for specified floors (lazy loading).
    
    By default, loads all three floors. Specify floor_indices to load only
    certain floors (more efficient for single-floor operations).
    
    Parameters
    ----------
    floor_indices : list[int], optional
        Floor indices to load (default: [0, 1, 2])
    
    Returns
    -------
    dict[int, dict]
        Mapping of floor index to graph dict
    """
    if floor_indices is None:
        floor_indices = list(FLOORS.keys())
    
    graphs = {}
    for idx in floor_indices:
        graphs[idx] = load_graph(idx)
    
    return graphs


def load_single_graph(floor_idx: int) -> Dict:
    """Load only one floor's graph (most efficient for single floor view).
    
    Use this in the navigate tab when showing a single floor.
    
    Parameters
    ----------
    floor_idx : int
        Floor index (0=Lower, 1=Ground, 2=Upper)
    
    Returns
    -------
    dict
        Floor graph
    """
    return load_graph(floor_idx)


def build_combined_graph(graphs: Dict[int, Dict]) -> tuple[Dict, Dict]:
    """Build a combined multi-floor graph with inter-floor edges (cached).
    
    Node IDs are prefixed with floor: e.g. "1:apple_store"
    
    Parameters
    ----------
    graphs : dict[int, dict]
        Per-floor graphs (from load_graphs)
    
    Returns
    -------
    tuple[dict, dict]
        (combined_edges, combined_node_coords)
    """
    edges: Dict[str, Dict[str, float]] = {}
    coords: Dict[str, Dict] = {}
    
    # Add per-floor edges
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


def get_graph_memory_estimate(graphs: Dict[int, Dict]) -> str:
    """Estimate memory footprint of loaded graphs (for monitoring).
    
    Returns
    -------
    str
        Human-readable memory size estimate
    """
    import sys
    
    total_size = sys.getsizeof(graphs)
    for g in graphs.values():
        total_size += sys.getsizeof(g)
        total_size += sys.getsizeof(g.get("nodes", {}))
        total_size += sys.getsizeof(g.get("edges", {}))
    
    # Convert to KB
    size_kb = total_size / 1024
    if size_kb < 1000:
        return f"{size_kb:.1f} KB"
    else:
        return f"{size_kb / 1024:.1f} MB"
