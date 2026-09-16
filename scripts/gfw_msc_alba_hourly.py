import os
import json
import math
import requests
import mapbox_vector_tile


# ============================================================
# MSC ALBA F
# ============================================================

TARGET_VESSEL_ID = (
    "44cc78120-0aff-04a7-579d-be71a1a9d071"
)

VESSEL_NAME = "MSC ALBA F"
MMSI = "636021870"
IMO = "9499010"


# ============================================================
# SENTINEL-1 TARGET
# ============================================================

TARGET_LAT = -15.824387
TARGET_LON = 51.655060
TARGET_TIME = "2026-08-01T15:01:56Z"


# ============================================================
# AIS TIME WINDOW
# ============================================================

START_TIME = "2026-08-01T14:00:00Z"
END_TIME = "2026-08-01T16:00:00Z"

DATASET = "public-global-presence:latest"


# ============================================================
# GFW TILE
# ============================================================

ZOOM = 7
TILE_X = 82
TILE_Y = 69

EXTENT = 4096


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
# MVT LOCAL COORDINATES -> LAT/LON
# ============================================================

def tile_local_to_latlon(
    local_x,
    local_y,
    zoom,
    tile_x,
    tile_y,
    extent
):

    world_size = 2 ** zoom

    global_x = tile_x + (local_x / extent)
    global_y = tile_y + (local_y / extent)

    lon = (
        global_x / world_size
    ) * 360.0 - 180.0

    mercator_y = (
        math.pi
        * (1 - 2 * global_y / world_size)
    )

    lat = math.degrees(
        math.atan(math.sinh(mercator_y))
    )

    return lat, lon


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("GFW MSC ALBA F ACQUISITION-TIME VERIFICATION")
print("=" * 70)

print()

print("Sentinel-1 candidate:")
print(f"  Latitude : {TARGET_LAT}")
print(f"  Longitude: {TARGET_LON}")
print(f"  Time     : {TARGET_TIME}")

print()

print("AIS verification window:")
print(f"  Start: {START_TIME}")
print(f"  End  : {END_TIME}")

print()

print(f"Target vessel: {VESSEL_NAME}")
print(f"MMSI: {MMSI}")
print(f"IMO : {IMO}")


# ============================================================
# DOWNLOAD GFW TILE
# ============================================================

print()
print("=" * 70)
print("DOWNLOADING GFW TILE")
print("=" * 70)

tile_url = (
    "https://gateway.api.globalfishingwatch.org"
    f"/v3/4wings/tile/heatmap/"
    f"{ZOOM}/{TILE_X}/{TILE_Y}"
)

tile_params = {
    "datasets[0]": DATASET,
    "date-range": f"{START_TIME},{END_TIME}",
    "interval": "HOUR",
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

decoded = mapbox_vector_tile.decode(
    response.content
)

if "main" not in decoded:

    print(
        "ERROR: GFW tile does not contain "
        "'main' layer."
    )

    print(
        "Available layers:",
        list(decoded.keys())
    )

    raise SystemExit(1)


layer = decoded["main"]

features = layer["features"]

extent = layer.get(
    "extent",
    EXTENT
)

print(
    f"Features found: {len(features)}"
)

print(
    f"Tile extent: {extent}"
)


# ============================================================
# BUILD CELL LOCATIONS FROM ACTUAL MVT GEOMETRY
# ============================================================

cell_locations = {}

for feature in features:

    properties = feature.get(
        "properties",
        {}
    )

    geometry = feature.get(
        "geometry",
        {}
    )

    cell_id = properties.get("cell")

    if cell_id is None:
        continue

    try:

        cell_id = int(cell_id)

    except (TypeError, ValueError):

        continue

    coordinates = geometry.get(
        "coordinates",
        []
    )

    if not coordinates:
        continue

    polygon = coordinates[0]

    xs = [
        point[0]
        for point in polygon
    ]

    ys = [
        point[1]
        for point in polygon
    ]

    center_x = (
        min(xs) + max(xs)
    ) / 2

    center_y = (
        min(ys) + max(ys)
    ) / 2

    lat, lon = tile_local_to_latlon(
        center_x,
        center_y,
        ZOOM,
        TILE_X,
        TILE_Y,
        extent
    )

    distance = haversine(
        TARGET_LAT,
        TARGET_LON,
        lat,
        lon
    )

    cell_locations[cell_id] = {
        "lat": lat,
        "lon": lon,
        "local_x": center_x,
        "local_y": center_y,
        "distance_km": distance,
    }


# ============================================================
# SELECT CELLS
# ============================================================

# Use every cell returned by the actual GFW tile.
cells = sorted(
    cell_locations.keys()
)

print()
print("=" * 70)
print("CELLS FROM CURRENT GFW TILE")
print("=" * 70)

print(
    f"Cells available: {len(cells)}"
)

for cell in sorted(
    cells,
    key=lambda c: cell_locations[c]["distance_km"]
):

    location = cell_locations[cell]

    print(
        f"Cell {cell:5d} | "
        f"{location['distance_km']:7.2f} km | "
        f"{location['lat']:9.5f}, "
        f"{location['lon']:9.5f}"
    )


# ============================================================
# QUERY MSC ALBA F
# ============================================================

print()
print("=" * 70)
print("SEARCHING FOR MSC ALBA F")
print("=" * 70)

results = []

request_count = 0

for cell in cells:

    request_count += 1

    url = (
        "https://gateway.api.globalfishingwatch.org"
        f"/v3/4wings/interaction/"
        f"{ZOOM}/{TILE_X}/{TILE_Y}/{cell}"
    )

    params = {
        "datasets[0]": DATASET,
        "date-range": (
            f"{START_TIME},{END_TIME}"
        ),
        "limit": 1000,
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=60
        )

    except requests.RequestException as exc:

        print(
            f"[{request_count}] "
            f"Cell {cell}: REQUEST ERROR"
        )

        print(exc)

        continue

    if response.status_code != 200:

        print(
            f"[{request_count}] "
            f"Cell {cell}: "
            f"HTTP {response.status_code}"
        )

        continue

    data = response.json()

    entries = data.get(
        "entries",
        []
    )

    found = False

    for group in entries:

        if not isinstance(group, list):
            continue

        for vessel in group:

            if not isinstance(vessel, dict):
                continue

            vessel_id = vessel.get("id")

            if vessel_id != TARGET_VESSEL_ID:
                continue

            found = True

            hours = vessel.get(
                "hours"
            )

            location = cell_locations[
                cell
            ]

            result = {

                "vessel_id":
                    TARGET_VESSEL_ID,

                "vessel_name":
                    VESSEL_NAME,

                "mmsi":
                    MMSI,

                "imo":
                    IMO,

                "cell":
                    cell,

                "hours":
                    hours,

                "start_time":
                    START_TIME,

                "end_time":
                    END_TIME,

                "cell_lat":
                    location["lat"],

                "cell_lon":
                    location["lon"],

                "distance_km":
                    location["distance_km"],
            }

            results.append(result)

            print()
            print("FOUND MSC ALBA F")
            print(
                f"  Cell     : {cell}"
            )
            print(
                f"  Hours    : {hours}"
            )
            print(
                f"  Distance : "
                f"{location['distance_km']:.2f} km"
            )
            print(
                f"  Location : "
                f"{location['lat']:.5f}, "
                f"{location['lon']:.5f}"
            )

    if not found:

        print(
            f"[{request_count}] "
            f"Cell {cell}: "
            f"MSC ALBA F not returned"
        )


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("ACQUISITION-TIME VERIFICATION RESULT")
print("=" * 70)

if not results:

    print()
    print(
        "MSC ALBA F was NOT returned by the "
        "GFW Interaction API for the selected "
        "14:00-16:00 UTC window."
    )

    print()
    print(
        "IMPORTANT: This does NOT prove that "
        "MSC ALBA F was absent."
    )

    print(
        "It means the API did not return this "
        "vessel for these cell/time queries."
    )

else:

    print()
    print(
        f"MSC ALBA F found in "
        f"{len(results)} cell/time records."
    )

    for result in results:

        print()

        print(
            f"Cell: {result['cell']}"
        )

        print(
            f"Time: "
            f"{result['start_time']} -> "
            f"{result['end_time']}"
        )

        print(
            f"Distance: "
            f"{result['distance_km']:.2f} km"
        )

        print(
            f"Hours: "
            f"{result['hours']}"
        )


# ============================================================
# SAVE
# ============================================================

output_file = (
    "data/results/"
    "gfw_msc_alba_acquisition_2026-08-01.json"
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

            "verification_window": {
                "start": START_TIME,
                "end": END_TIME,
            },

            "vessel": {
                "id": TARGET_VESSEL_ID,
                "name": VESSEL_NAME,
                "mmsi": MMSI,
                "imo": IMO,
            },

            "cells_checked": len(cells),

            "results": results,

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