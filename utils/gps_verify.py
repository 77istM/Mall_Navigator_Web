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
from config import STORES, STORE_RADIUS_M


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
