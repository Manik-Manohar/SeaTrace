import os
import json
import math
import requests
import mapbox_vector_tile


# ============================================================
# SENTINEL-1 SUSPECTED SPILL
# ============================================================

TARGET_LAT = -15.824387
TARGET_LON = 51.655060
TARGET_TIME = "2026-08-01T15:01:56Z"

# Examine two hours around acquisition
START_TIME = "2026-08-01T00:00:00Z"
END_TIME = "2026-08-02T00:00:00Z"
DATASET = "public-global-presence:latest"

ZOOM = 7
TILE_X = 82
TILE_Y = 69

# ============================================================
# CELLS WE PREVIOUSLY FOUND ACTIVE
# ============================================================

CELLS = [
    9877,
    9880,
    9320,
    10549,
    7521,
    7635,
    11222,
    7523,
    7072,
    11782,
]

# ============================================================
# TOKEN
# ============================================================

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    print("ERROR: GFW_API_TOKEN is not loaded.")
    raise SystemExit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}"
}


# ============================================================
# HAVERSINE
# ============================================================

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    dlat = lat2_rad - lat1_rad
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(dlon / 2) ** 2
    )

    return 2 * R * math.asin(math.sqrt(a))


# ============================================================
# MVT TILE COORDINATE -> LAT/LON
# ============================================================

def tile_local_to_latlon(local_x, local_y, zoom, tile_x, tile_y, extent):
    """
    Convert Mapbox Vector Tile local coordinates
    into geographic latitude/longitude.
    """

    world_size = 2 ** zoom

    global_x = tile_x + (local_x / extent)
    global_y = tile_y + (local_y / extent)

    lon = (global_x / world_size) * 360.0 - 180.0

    n = math.pi * (1 - 2 * global_y / world_size)

    lat = math.degrees(math.atan(math.sinh(n)))

    return lat, lon


# ============================================================
# DOWNLOAD GFW VECTOR TILE
# ============================================================

print("=" * 70)
print("GFW TIME + PROXIMITY ANALYSIS")
print("=" * 70)

print()
print("Sentinel-1 candidate:")
print(f"  Latitude : {TARGET_LAT}")
print(f"  Longitude: {TARGET_LON}")
print(f"  Time     : {TARGET_TIME}")

print()
print("AIS time window:")
print(f"  Start: {START_TIME}")
print(f"  End  : {END_TIME}")

print()
print("Downloading GFW activity tile...")


tile_url = (
    "https://gateway.api.globalfishingwatch.org"
    f"/v3/4wings/tile/heatmap/"
    f"{ZOOM}/{TILE_X}/{TILE_Y}"
)

tile_params = {
    "datasets[0]": DATASET,
    "date-range": f"{START_TIME},{END_TIME}",
    "interval": "DAY",
    "temporal-aggregation": "true",
    "format": "MVT",
}

response = requests.get(
    tile_url,
    params=tile_params,
    headers=HEADERS,
    timeout=60
)

print("Tile HTTP:", response.status_code)

if response.status_code != 200:
    print(response.text)
    raise SystemExit(1)


# ============================================================
# DECODE TILE
# ============================================================

decoded = mapbox_vector_tile.decode(response.content)

if "main" not in decoded:
    print("ERROR: GFW tile does not contain the expected 'main' layer.")
    print("Available layers:", list(decoded.keys()))
    raise SystemExit(1)

layer = decoded["main"]

features = layer["features"]

extent = layer.get("extent", 4096)

print()
print(f"GFW tile decoded successfully.")
print(f"Features found: {len(features)}")
print(f"Tile extent: {extent}")


# ============================================================
# EXTRACT CELL CENTERS
# ============================================================

cell_locations = {}

for feature in features:

    properties = feature.get("properties", {})
    geometry = feature.get("geometry", {})

    cell_id = properties.get("cell")

    if cell_id is None:
        continue

    try:
        cell_id = int(cell_id)
    except (TypeError, ValueError):
        continue

    coordinates = geometry.get("coordinates", [])

    if not coordinates:
        continue

    # Polygon geometry
    polygon = coordinates[0]

    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]

    center_x = (min(xs) + max(xs)) / 2
    center_y = (min(ys) + max(ys)) / 2

    lat, lon = tile_local_to_latlon(
        center_x,
        center_y,
        ZOOM,
        TILE_X,
        TILE_Y,
        extent
    )

    cell_locations[cell_id] = {
        "lat": lat,
        "lon": lon,
        "local_x": center_x,
        "local_y": center_y,
    }


# ============================================================
# CHECK REQUESTED CELLS
# ============================================================

print()
print("=" * 70)
print("CORRECTED CELL LOCATIONS")
print("=" * 70)

valid_cells = []

for cell in CELLS:

    if cell not in cell_locations:
        print(f"Cell {cell}: NOT FOUND IN TILE")
        continue

    location = cell_locations[cell]

    distance = haversine(
        TARGET_LAT,
        TARGET_LON,
        location["lat"],
        location["lon"]
    )

    location["distance_km"] = distance

    valid_cells.append(cell)

    print(
        f"Cell {cell:5d} | "
        f"{distance:8.2f} km | "
        f"Lat {location['lat']:9.5f} | "
        f"Lon {location['lon']:9.5f}"
    )


# ============================================================
# SORT CELLS BY REAL DISTANCE
# ============================================================

valid_cells.sort(
    key=lambda cell: cell_locations[cell]["distance_km"]
)

print()
print("=" * 70)
print("CELLS SORTED BY DISTANCE")
print("=" * 70)

for i, cell in enumerate(valid_cells, start=1):

    location = cell_locations[cell]

    print(
        f"{i:2d}. Cell {cell:5d} | "
        f"{location['distance_km']:8.2f} km | "
        f"{location['lat']:9.5f}, "
        f"{location['lon']:9.5f}"
    )


# ============================================================
# QUERY EACH CELL
# ============================================================

results = []

print()
print("=" * 70)
print("QUERYING HISTORICAL AIS")
print("=" * 70)

for cell in valid_cells:

    print()
    print(f"Cell {cell}")
    print("-" * 40)

    url = (
        "https://gateway.api.globalfishingwatch.org"
        f"/v3/4wings/interaction/"
        f"{ZOOM}/{TILE_X}/{TILE_Y}/{cell}"
    )

    params = {
        "datasets[0]": DATASET,
        "date-range": f"{START_TIME},{END_TIME}",
        "limit": 1000,
    }

    response = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=60
    )

    print("HTTP:", response.status_code)

    if response.status_code != 200:
        print(response.text)
        continue

    data = response.json()

    entries = data.get("entries", [])

    vessel_records = []

    for group in entries:

        if not isinstance(group, list):
            continue

        for vessel in group:

            vessel_records.append({
                "vessel_id": vessel.get("id"),
                "hours": vessel.get("hours"),
                "cell": cell,
            })

    location = cell_locations[cell]

    for record in vessel_records:

        record["cell_lat"] = location["lat"]
        record["cell_lon"] = location["lon"]
        record["distance_km"] = location["distance_km"]

        results.append(record)

    if vessel_records:

        for record in vessel_records:

            print(
                f"Vessel: {record['vessel_id']}"
            )

            print(
                f"Hours : {record['hours']}"
            )

            print(
                f"Cell distance: "
                f"{record['distance_km']:.2f} km"
            )

    else:

        print(
            "No vessels reported in this cell/time window."
        )


# ============================================================
# SORT RESULTS
# ============================================================

results.sort(
    key=lambda x: (
        x["distance_km"],
        -float(x["hours"] or 0)
    )
)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("CORRECTED TIME + PROXIMITY RESULTS")
print("=" * 70)

if not results:

    print()
    print(
        "No AIS presence found in the selected "
        "cells during the selected time window."
    )

else:

    for i, result in enumerate(results, start=1):

        print()

        print(
            f"{i}. {result['vessel_id']}"
        )

        print(
            f"   Distance to cell center: "
            f"{result['distance_km']:.2f} km"
        )

        print(
            f"   Hours: {result['hours']}"
        )

        print(
            f"   Cell: {result['cell']}"
        )

        print(
            f"   Cell location: "
            f"{result['cell_lat']:.5f}, "
            f"{result['cell_lon']:.5f}"
        )


# ============================================================
# SAVE RESULTS
# ============================================================

output_file = (
    "data/results/"
    "gfw_time_proximity_2026-08-01.json"
)

with open(
    output_file,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        {
            "target": {
                "latitude": TARGET_LAT,
                "longitude": TARGET_LON,
                "time": TARGET_TIME,
            },

            "time_window": {
                "start": START_TIME,
                "end": END_TIME,
            },

            "tile": {
                "zoom": ZOOM,
                "x": TILE_X,
                "y": TILE_Y,
            },

            "results": results,

            "cell_locations": {
                str(cell): cell_locations[cell]
                for cell in valid_cells
            },
        },
        f,
        indent=2
    )


print()
print("=" * 70)
print("COMPLETE")
print("=" * 70)

print()
print("Saved:")
print(output_file)