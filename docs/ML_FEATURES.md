# Machine Learning Features (Phase 5.3)

## Overview

The Mall Navigator now includes machine learning-powered features for smart routing recommendations. This MVP implementation uses lightweight, data-collection-focused approaches that can be upgraded to full ML models in the future.

## Features Implemented

### 1. **Popular Routes Predictor** 🔥

**What it does:**
- Tracks which routes are taken by users
- Groups data by time of day (4-hour buckets) and day of week
- Recommends trending routes based on current day/time
- Displays a heatmap of most-visited nodes (hotspots)

**How to use:**
1. Navigate through the mall and complete routes (Dijkstra or A*)
2. Each route is automatically recorded for training
3. In the "Smart Recommendations" panel, check the "Popular Routes" tab
4. See trending routes for your current time slot
5. Click "Navigate via Route" to pre-fill start/end nodes

**Data structure:**
```json
{
  "routes_by_time": {
    "08-12_Monday": {
      "node_A->node_B": 15,
      "node_C->node_D": 8
    }
  },
  "node_popularity": {
    "node_A": 45,
    "node_B": 38
  }
}
```

**Benefits:**
- Helps new users discover efficient routes
- Identifies bottlenecks (high-traffic nodes)
- Time-aware recommendations (lunch rush patterns)

---

### 2. **Nearby Recommendations** 🎯

**What it does:**
- Recommends products/stores near user's current location
- Uses content-based filtering (Euclidean distance on floor plan)
- Filters by floor to avoid cross-floor recommendations
- Shows store ratings and opening hours

**How to use:**
1. Select an end destination (your path endpoint becomes "current location")
2. Open "Smart Recommendations" → "Nearby Stores" tab
3. See products within 50m on your floor
4. Results sorted by distance (closest first)
5. Click "Go Here" to navigate to a recommended store

**Distance calculation:**
- Pixel-based Euclidean distance on current floor plan
- 50m default radius (adjustable via `max_distance` parameter)
- Excludes stores on different floors

**To add product location data:**
```python
# In product JSON schema, add x/y coordinates:
{
  "name": "Nike Store",
  "category": "Retail",
  "x": 150.0,
  "y": 200.0,
  "floor": 1,
  "opening_hours": "9-21",
  "rating": 4.5
}
```

---

### 3. **Category-Based Recommendations** 💡

**What it does:**
- Suggests products based on past search history
- Groups by category (Retail, Food, Services, etc.)
- Recommends similar categories the user has searched for

**How to use:**
- Automatically tracks search history in session
- Future: Will show category recommendations in recommendations panel

---

## Architecture

### Core Modules

#### `utils/ml_features.py`
Main ML module with three classes:

- **`PopularRoutesPredictor`**: Temporal route analysis
  - `record_route_taken(path)` - Record route for training
  - `predict_popular_routes(limit, current_time)` - Get trending routes
  - `get_node_popularity(limit)` - Get hotspot nodes

- **`NearbyRecommender`**: Content-based product recommendations
  - `get_nearby_products(current_node, nodes, max_distance, limit)` - Get nearby stores
  - `recommend_by_category(search_history, limit)` - Category-based filtering
  - `add_product_to_index(product_id, product)` - Add/update product

- **`MLFeatureFactory`**: Singleton factory for lazy initialization
  - `init_route_predictor()` - Get route predictor instance
  - `init_nearby_recommender(products)` - Get recommender instance

#### `components/ml_recommendations.py`
Streamlit UI components for displaying ML features

- `render_popular_routes_panel()` - Show trending routes
- `render_nearby_recommendations_panel()` - Show nearby stores
- `render_node_heatmap_legend()` - Show hotspots
- `render_ml_feature_panel()` - Main feature container

### Data Persistence

**Storage paths:**
```
data/ml_training_data.json       # Popular routes model data
data/recommendations_cache.json  # Nearby recommendations cache
```

Both files are JSON-backed for MVP simplicity (no database required).

---

## Integration Points

### Route Recording

Routes are automatically recorded when:
1. User completes pathfinding (both Dijkstra and A*)
2. Route is added to session state
3. `record_route_taken(path)` is called in `app.py`

**In `app.py` ≈ line 610-625:**
```python
if star.get("found"):
    analytics.track_route(star.get("path", []))
    # Record for ML popular routes prediction
    ml_factory = get_ml_features()
    route_predictor = ml_factory.init_route_predictor()
    route_predictor.record_route_taken(star.get("path", []))
```

### UI Display

ML recommendations shown in:
- **Main navigate tab**: Expandable "🤖 Smart Recommendations" panel
- **Tabs**: Popular Routes / Nearby Stores / Hotspots
- **Buttons**: Quick navigation buttons to recommended routes/stores

---

## Testing

Run tests with:
```bash
python -m pytest tests/test_ml_features.py -v
```

**Test coverage (23 tests):**
- ✅ PopularRoutesPredictor (8 tests)
- ✅ NearbyRecommender (10 tests)
- ✅ MLFeatureFactory (3 tests)
- ✅ RoutePopularity dataclass (2 tests)

**Key test scenarios:**
- Route recording and persistence
- Time-based predictions
- Nearby filtering by floor and distance
- Category-based recommendations
- Singleton factory pattern

---

## Future Enhancements

### Immediate (Post-MVP)

1. **Machine Learning Models**
   - Replace heuristics with sklearn RandomForest/XGBoost
   - Train on temporal patterns (rush hours, weekend vs weekdays)
   - Cross-validate for prediction accuracy

2. **Crowd-Sourced Routing**
   - Real-time location heatmap overlaid on floor plan
   - Detect congestion and suggest alternative routes
   - Privacy-first: aggregate anonymous locations

3. **Personalized Routing**
   - Learn per-user preferences (avoid stairs, prefer food hall)
   - Accessibility filtering already integrated in `utils/routing.py`
   - Store preferences in session or SQLite DB

### Long-Term (6+ months)

1. **Deep Learning**
   - LSTM networks for temporal pattern recognition
   - Computer vision for foot traffic from security cameras (opt-in)
   - Graph neural networks for route optimization

2. **Collaborative Filtering**
   - "Users who searched for Nike also searched for Adidas"
   - Matrix factorization for product recommendations
   - Requires user ID tracking (optional privacy setting)

3. **Mobile Integration**
   - Export ML models to on-device inference (TensorFlow Lite)
   - Real-time recommendations without server round-trip
   - Reduce latency for AR navigation

---

## Configuration & Tuning

### Popular Routes

Default parameters in `utils/ml_features.py`:
```python
# Time buckets: 4-hour windows
# Day of week: Monday, Tuesday, ..., Sunday
# Top N routes returned: 3
# Node popularity limit: 5
```

### Nearby Recommendations

Adjustable parameters:
```python
max_distance = 50.0  # pixels (roughly meters)
limit = 5            # max products to show
exclude_categories = ["Closed", "Maintenance"]  # skip these
```

### Model Storage

Change storage paths via:
```python
# In app initialization
route_predictor = ml_factory.init_route_predictor(
    storage_path="custom/path/ml_data.json"
)
recommender = ml_factory.init_nearby_recommender(
    products=products_dict,
    cache_path="custom/path/recommendations.json"
)
```

---

## Privacy & Compliance

✅ **Route data**: Anonymized (only path taken, no user ID)
✅ **Product interactions**: Stored in browser session only (no server tracking)
✅ **No personal data**: ML features don't collect user IDs or demographics

**Opt-out:**
- Users can disable route recording (Future: add toggle in privacy settings)
- Recommendations shown only if user consents in sidebar

---

## Performance

**Typical latency:**
- Route prediction: < 10ms (in-memory JSON lookup)
- Nearby recommendations: < 20ms (distance calculations)
- UI rendering: Streamlit handles (200-500ms typical)

**Scalability:**
- Current: Single-mall data (fits in memory)
- Future: Multi-mall support requires SQLite + indexing

---

## Troubleshooting

### No recommendations appearing
1. Check `data/ml_training_data.json` exists
2. Ensure at least 1 route has been completed
3. Verify current time matches time bucket in data

### ML features seem slow
1. Large product dataset? Consider SQLite migration
2. Too many nodes? Implement R-tree spatial indexing
3. Profile with: `python -m cProfile app.py`

### Data not persisting
1. Check file permissions on `data/` directory
2. Verify JSON files aren't corrupted: `python -m json.tool data/ml_training_data.json`
3. Clear cache: `streamlit cache clear`

---

## Contributing

To extend ML features:

1. **Add a new recommender**: Inherit from base class pattern
2. **Integrate with app**: Import in `app.py`, call in appropriate flow
3. **Add tests**: Create test class in `tests/test_ml_features.py`
4. **Document**: Update this file with new feature

---

**Last Updated**: April 1, 2026  
**Status**: MVP (Phase 5.3 start)  
**Next Phase**: Upgrade heuristics to ML models (4+ weeks effort)
