"""Outdoor OpenStreetMap component using Folium.

Displayed when the user is outside the mall (GPS-based) or when they want to
see the store's location on a real-world map.  Uses OpenStreetMap tiles — no
API key or billing required.
"""
import math
import folium
from streamlit_folium import st_folium


def render_outdoor_map(
    store_lat: float,
    store_lng: float,
    store_name: str,
    user_lat: float | None = None,
    user_lng: float | None = None,
    distance_m: float | None = None,
) -> None:
    """
    Render a Folium map centred on the store with:
      - A red store marker
      - An optional blue 'you are here' marker
      - A dashed line between them when both positions are known

    All map tiles come from OpenStreetMap (free, open-source, no key needed).
    """
    centre_lat = store_lat
    centre_lng = store_lng
    zoom = 16

    # If we know the user's position, centre between them and the store
    if user_lat is not None and user_lng is not None:
        centre_lat = (store_lat + user_lat) / 2
        centre_lng = (store_lng + user_lng) / 2
        # rough zoom: pull back if far away
        if distance_m and distance_m > 2000:
            zoom = 13
        elif distance_m and distance_m > 500:
            zoom = 15

    m = folium.Map(
        location=[centre_lat, centre_lng],
        zoom_start=zoom,
        tiles="OpenStreetMap",
        control_scale=True,
    )

    # Store marker
    folium.Marker(
        [store_lat, store_lng],
        popup=folium.Popup(f"<b>{store_name}</b>", max_width=200),
        tooltip=store_name,
        icon=folium.Icon(color="red", icon="shopping-cart", prefix="fa"),
    ).add_to(m)

    # User marker
    if user_lat is not None and user_lng is not None:
        dist_text = f"{distance_m:.0f} m away" if distance_m is not None else ""
        folium.Marker(
            [user_lat, user_lng],
            popup=folium.Popup(f"<b>You are here</b><br>{dist_text}", max_width=200),
            tooltip="Your location",
            icon=folium.Icon(color="blue", icon="user", prefix="fa"),
        ).add_to(m)

        # Dashed line store ↔ user
        folium.PolyLine(
            locations=[[user_lat, user_lng], [store_lat, store_lng]],
            color="#FF6600",
            weight=3,
            opacity=0.7,
            dash_array="8 6",
            tooltip=dist_text,
        ).add_to(m)

    # 500-m radius circle around the store
    folium.Circle(
        [store_lat, store_lng],
        radius=500,
        color="#3388FF",
        fill=True,
        fill_opacity=0.05,
        weight=1,
        tooltip="500 m access zone",
    ).add_to(m)

    st_folium(m, width=720, height=460, returned_objects=[])
