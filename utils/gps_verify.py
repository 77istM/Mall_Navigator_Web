"""GPS-based location verification.

The application targets public, anonymous users (no login required).
Access control is light-touch: the app checks whether the user's device
GPS places them within STORE_RADIUS_M metres of the configured store.

Because indoor GPS is unreliable (accuracy can be 10-50 m), the check is
advisory only — users who fail the check (or deny location access) see a
warning banner but can still use the app. This is appropriate for a
prototype deployed in public.
"""

import math
from utils.coordinates import haversine_m

# ---------------------------------------------------------------------------
# Store registry (add more stores here as needed)
# ---------------------------------------------------------------------------

STORES: dict[str, dict] = {
    "asda_old_kent_road": {
        "name": "Asda Superstore – Old Kent Road",
        "lat": 51.4884,
        "lng": -0.0669,
    },
    "sainsburys_whitechapel": {
        "name": "Sainsbury's – Whitechapel",
        "lat": 51.5153,
        "lng": -0.0668,
    },
    "demo": {
        "name": "Demo Mall (any location)",
        "lat": 0.0,
        "lng": 0.0,
    },
}

# Radius within which a user is considered "at" the store.
# 500 m covers the car park and surrounding area.
STORE_RADIUS_M = 500


def check_in_range(
    user_lat: float,
    user_lng: float,
    store_key: str = "asda_old_kent_road",
) -> dict:
    """
    Return a verification result dict.

    Returns
    -------
    {
        "in_range"  : bool,
        "distance_m": float,
        "store_name": str,
        "store_lat" : float,
        "store_lng" : float,
    }
    """
    store = STORES.get(store_key, STORES["demo"])

    if store_key == "demo":
        return {
            "in_range": True,
            "distance_m": 0.0,
            "store_name": store["name"],
            "store_lat": store["lat"],
            "store_lng": store["lng"],
        }

    dist = haversine_m(user_lat, user_lng, store["lat"], store["lng"])
    return {
        "in_range": dist <= STORE_RADIUS_M,
        "distance_m": round(dist, 1),
        "store_name": store["name"],
        "store_lat": store["lat"],
        "store_lng": store["lng"],
    }
