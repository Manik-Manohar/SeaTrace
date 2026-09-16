import os
import math
import requests
import mapbox_vector_tile


# ============================================================
# SENTINEL-1 CANDIDATE
# ============================================================

LAT = -15.824387
LON = 51.655060

ZOOM = 7

DATE_RANGE = "2026-08-01,2026-08-02"


# ============================================================
# TILE CALCULATION
# ============================================================

def lon_to_tile_x(lon, zoom):
    n = 2 ** zoom
    return (lon + 180.0) / 360.0 * n


def lat_to_tile_y(lat, zoom):
    lat_rad = math.radians(lat)
    n = 2 ** zoom

    return (
        (1.0 - math.asinh(math.tan(lat_rad)) / math.pi)
        / 2.0
        * n
    )


x_float = lon_to_tile_x(LON, ZOOM)
y_float = lat_to_tile_y(LAT, ZOOM)

tile_x = int(x_float)
tile_y = int(y_float)


# ============================================================
# LOCAL TILE COORDINATES
# ============================================================

extent = 4096

local_x = (x_float - tile_x) * extent
local_y = (y_float - tile_y) * extent


print("=" * 70)
print("GFW CANDIDATE CELL FINDER")
print("=" * 70)

print(f"Latitude : {LAT}")
print(f"Longitude: {LON}")
print()
print(f"Zoom: {ZOOM}")
print(f"Tile: {tile_x}/{tile_y}")
print()
print(f"Local X: {local_x:.2f}")
print(f"Local Y: {local_y:.2f}")
print()


# ============================================================
# GET TOKEN
# ============================================================

token = os.getenv("GFW_API_TOKEN")

if not token:
    print("ERROR: GFW_API_TOKEN is not loaded.")
    raise SystemExit(1)


# ============================================================
# DOWNLOAD TILE
# ============================================================

url = (
    "https://gateway.api.globalfishingwatch.org"
    f"/v3/4wings/tile/heatmap/{ZOOM}/{tile_x}/{tile_y}"
)

params = {
    "date-range": DATE_RANGE,
    "datasets[0]": "public-global-presence:latest",
    "format": "MVT",
    "interval": "DAY",
    "temporal-aggregation": "true",
}

headers = {
    "Authorization": f"Bearer {token}"
}


print("Downloading GFW tile...")

response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=60
)

print("HTTP Status:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit(1)


# ============================================================
# DECODE TILE
# ============================================================

tile = mapbox_vector_tile.decode(response.content)

layer = tile.get("main")

if not layer:
    print("ERROR: 'main' layer not found.")
    raise SystemExit(1)

features = layer.get("features", [])

print(f"Features found: {len(features)}")
print()


# ============================================================
# FIND CELL CONTAINING CANDIDATE
# ============================================================

matches = []

for feature in features:

    geometry = feature.get("geometry", {})

    if geometry.get("type") != "Polygon":
        continue

    coordinates = geometry.get("coordinates", [])

    if not coordinates:
        continue

    polygon = coordinates[0]

    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]

    min_x = min(xs)
    max_x = max(xs)

    min_y = min(ys)
    max_y = max(ys)

    if (
        min_x <= local_x <= max_x
        and
        min_y <= local_y <= max_y
    ):

        properties = feature.get("properties", {})

        matches.append({
            "cell": properties.get("cell"),
            "id": properties.get("id"),
            "count": properties.get("count"),
            "bbox": [
                min_x,
                min_y,
                max_x,
                max_y
            ]
        })


# ============================================================
# RESULT
# ============================================================

print("=" * 70)
print("CANDIDATE CELL RESULT")
print("=" * 70)

if matches:

    print("MATCH FOUND!")

    for match in matches:
        print()
        print("Cell:", match["cell"])
        print("ID:", match["id"])
        print("Count:", match["count"])
        print("Bounding box:", match["bbox"])

else:

    print("No activity cell directly contains the candidate.")

    print()
    print("Nearest activity cells will be calculated next.")


print()
print("=" * 70)