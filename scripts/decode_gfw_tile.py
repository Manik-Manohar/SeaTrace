import os
import math
import requests
import mapbox_vector_tile


# ============================================================
# SENTINEL-1 CANDIDATE
# ============================================================

LAT = -15.824387
LON = 51.655060

DATE_RANGE = "2026-08-01,2026-08-02"

ZOOM = 7


# ============================================================
# WEB MERCATOR TILE
# ============================================================

def lon_to_tile_x(lon, zoom):
    return int((lon + 180.0) / 360.0 * (2 ** zoom))


def lat_to_tile_y(lat, zoom):
    lat_rad = math.radians(lat)

    return int(
        (
            1.0
            - math.asinh(math.tan(lat_rad)) / math.pi
        )
        / 2.0
        * (2 ** zoom)
    )


x = lon_to_tile_x(LON, ZOOM)
y = lat_to_tile_y(LAT, ZOOM)


print("=" * 70)
print("GFW MVT TILE DECODER")
print("=" * 70)

print(f"Candidate latitude : {LAT}")
print(f"Candidate longitude: {LON}")
print(f"Date range         : {DATE_RANGE}")
print(f"Zoom               : {ZOOM}")
print(f"Tile               : {x}/{y}")
print()


# ============================================================
# DOWNLOAD TILE
# ============================================================

url = (
    "https://gateway.api.globalfishingwatch.org"
    f"/v3/4wings/tile/heatmap/{ZOOM}/{x}/{y}"
)

params = {
    "date-range": DATE_RANGE,
    "datasets[0]": "public-global-presence:latest",
    "format": "MVT",
    "interval": "DAY",
    "temporal-aggregation": "true",
}

token = os.getenv("GFW_API_TOKEN")

if not token:
    print("ERROR: GFW_API_TOKEN is not loaded.")
    raise SystemExit(1)

headers = {
    "Authorization": f"Bearer {token}"
}


print("Requesting tile...")

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=60
)

print("HTTP Status:", response.status_code)
print("Tile size:", len(response.content), "bytes")
print()


if response.status_code != 200:
    print("GFW ERROR:")
    print(response.text)
    raise SystemExit(1)


# ============================================================
# DECODE MVT
# ============================================================

print("Decoding MVT...")

tile = mapbox_vector_tile.decode(response.content)

print()
print("Layers found:")
print(list(tile.keys()))
print()


# ============================================================
# PRINT FEATURES
# ============================================================

feature_count = 0

for layer_name, layer in tile.items():

    print("=" * 70)
    print("LAYER:", layer_name)
    print("=" * 70)

    features = layer.get("features", [])

    print("Features:", len(features))
    print()

    for i, feature in enumerate(features):

        feature_count += 1

        print(f"FEATURE {i + 1}")

        print("ID:")
        print(feature.get("id"))

        print("Properties:")
        print(feature.get("properties"))

        print("Geometry type:")
        geometry = feature.get("geometry", {})
        print(geometry.get("type"))

        print("Geometry:")
        print(geometry)

        print("-" * 70)


print()
print("=" * 70)
print("TOTAL FEATURES:", feature_count)
print("=" * 70)