import os
import json
import math
import requests
import mapbox_vector_tile


# ============================================================
# SENTINEL-1 CANDIDATE
# ============================================================

LAT = -15.824387
LON = 51.655060

ZOOM = 7

DATE_START = "2026-08-01"
DATE_END = "2026-08-02"

DATASET = "public-global-presence:latest"


# ============================================================
# WEB MERCATOR HELPERS
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


def tile_xy_to_lonlat(x, y, zoom):
    n = 2 ** zoom

    lon = x / n * 360.0 - 180.0

    lat_rad = math.atan(
        math.sinh(
            math.pi * (1.0 - 2.0 * y / n)
        )
    )

    lat = math.degrees(lat_rad)

    return lat, lon


# ============================================================
# TOKEN
# ============================================================

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    print("ERROR: GFW_API_TOKEN is not loaded.")
    raise SystemExit(1)


# ============================================================
# FIND TILE
# ============================================================

x_float = lon_to_tile_x(LON, ZOOM)
y_float = lat_to_tile_y(LAT, ZOOM)

tile_x = int(x_float)
tile_y = int(y_float)

extent = 4096

local_x = (x_float - tile_x) * extent
local_y = (y_float - tile_y) * extent


print("=" * 70)
print("GFW INTERACTION — HISTORICAL AIS")
print("=" * 70)

print(f"Candidate latitude : {LAT}")
print(f"Candidate longitude: {LON}")
print(f"Date               : {DATE_START}")
print()
print(f"Zoom: {ZOOM}")
print(f"Tile: {tile_x}/{tile_y}")
print()
print(f"Candidate local X: {local_x:.2f}")
print(f"Candidate local Y: {local_y:.2f}")
print()


# ============================================================
# DOWNLOAD MVT TILE
# ============================================================

tile_url = (
    "https://gateway.api.globalfishingwatch.org"
    f"/v3/4wings/tile/heatmap/{ZOOM}/{tile_x}/{tile_y}"
)

tile_params = {
    "date-range": f"{DATE_START},{DATE_END}",
    "datasets[0]": DATASET,
    "format": "MVT",
    "interval": "DAY",
    "temporal-aggregation": "true",
}

headers = {
    "Authorization": f"Bearer {TOKEN}"
}


print("Downloading activity tile...")

response = requests.get(
    tile_url,
    params=tile_params,
    headers=headers,
    timeout=60
)

print("Tile HTTP status:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit(1)


tile = mapbox_vector_tile.decode(response.content)

layer = tile.get("main")

if not layer:
    print("ERROR: No 'main' layer.")
    raise SystemExit(1)

features = layer.get("features", [])

print(f"Active cells found: {len(features)}")
print()


# ============================================================
# COLLECT CELLS
# ============================================================

cells = []

for feature in features:

    properties = feature.get("properties", {})
    geometry = feature.get("geometry", {})

    cell = properties.get("cell")

    if cell is None:
        continue

    coordinates = geometry.get("coordinates", [])

    if not coordinates:
        continue

    polygon = coordinates[0]

    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]

    min_x = min(xs)
    max_x = max(xs)
    min_y = min(ys)
    max_y = max(ys)

    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2

    # Convert local tile coordinates to global tile coordinates
    global_x = tile_x + center_x / extent
    global_y = tile_y + center_y / extent

    cell_lat, cell_lon = tile_xy_to_lonlat(
        global_x,
        global_y,
        ZOOM
    )

    # Approximate distance using haversine
    R = 6371.0

    lat1 = math.radians(LAT)
    lat2 = math.radians(cell_lat)

    dlat = math.radians(cell_lat - LAT)
    dlon = math.radians(cell_lon - LON)

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1)
        * math.cos(lat2)
        * math.sin(dlon / 2) ** 2
    )

    distance_km = (
        2
        * R
        * math.asin(math.sqrt(a))
    )

    cells.append({
        "cell": int(cell),
        "id": properties.get("id"),
        "count": properties.get("count"),
        "center_lat": cell_lat,
        "center_lon": cell_lon,
        "distance_km": distance_km,
    })


# Sort nearest first
cells.sort(key=lambda c: c["distance_km"])


print("=" * 70)
print("NEAREST ACTIVE CELLS")
print("=" * 70)

for cell in cells[:10]:

    print(
        f"Cell {cell['cell']:5d} | "
        f"Distance {cell['distance_km']:7.2f} km | "
        f"Lat {cell['center_lat']:9.5f} | "
        f"Lon {cell['center_lon']:9.5f}"
    )

print()


# ============================================================
# QUERY INTERACTION API
# ============================================================

cell_list = ",".join(
    str(cell["cell"])
    for cell in cells
)

interaction_url = (
    "https://gateway.api.globalfishingwatch.org"
    f"/v3/4wings/interaction/"
    f"{ZOOM}/{tile_x}/{tile_y}/{cell_list}"
)

interaction_params = {
    "datasets[0]": DATASET,
    "date-range": f"{DATE_START},{DATE_END}",
    "limit": 1000,
}

print("=" * 70)
print("QUERYING INTERACTION API")
print("=" * 70)

print(f"Cells requested: {len(cells)}")
print()
print("Requesting vessel details...")


interaction_response = requests.get(
    interaction_url,
    params=interaction_params,
    headers=headers,
    timeout=120
)

print(
    "Interaction HTTP status:",
    interaction_response.status_code
)

if interaction_response.status_code != 200:

    print()
    print("GFW INTERACTION ERROR:")
    print(interaction_response.text)

    raise SystemExit(1)


interaction_data = interaction_response.json()


# ============================================================
# DISPLAY RESPONSE
# ============================================================

print()
print("=" * 70)
print("INTERACTION RESULT")
print("=" * 70)

print(
    json.dumps(
        interaction_data,
        indent=2
    )[:30000]
)


# ============================================================
# SAVE EVERYTHING
# ============================================================

output = {
    "candidate": {
        "latitude": LAT,
        "longitude": LON,
        "date": DATE_START
    },
    "tile": {
        "zoom": ZOOM,
        "x": tile_x,
        "y": tile_y
    },
    "cells": cells,
    "interaction": interaction_data
}

output_file = (
    "data/results/"
    "gfw_interaction_2026-08-01.json"
)

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        output,
        f,
        indent=2
    )


print()
print("=" * 70)
print("COMPLETE")
print("=" * 70)
print(f"Saved: {output_file}")