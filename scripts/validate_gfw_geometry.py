import math
import json
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

TIME_FILE = BASE / "data" / "results" / "gfw_time_proximity_2026-08-01.json"

with open(TIME_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

target = data["target"]
tile = data["tile"]

target_lat = target["latitude"]
target_lon = target["longitude"]

z = tile["zoom"]
tile_x = tile["x"]
tile_y = tile["y"]

EXTENT = 4096


# ------------------------------------------------------------
# Web Mercator: latitude/longitude -> global tile coordinates
# ------------------------------------------------------------

def lonlat_to_global_pixel(lon, lat, zoom):

    n = 2 ** zoom

    x = (lon + 180.0) / 360.0 * n

    lat_rad = math.radians(lat)

    y = (
        1.0
        - math.asinh(math.tan(lat_rad)) / math.pi
    ) / 2.0 * n

    return x, y


# ------------------------------------------------------------
# Global tile coordinates -> latitude/longitude
# ------------------------------------------------------------

def global_pixel_to_lonlat(x, y, zoom):

    n = 2 ** zoom

    lon = x / n * 360.0 - 180.0

    mercator_y = math.pi * (1.0 - 2.0 * y / n)

    lat = math.degrees(
        math.atan(math.sinh(mercator_y))
    )

    return lat, lon


# ------------------------------------------------------------
# Haversine distance
# ------------------------------------------------------------

def haversine(lat1, lon1, lat2, lon2):

    R = 6371.0

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return 2 * R * math.asin(math.sqrt(a))


# ------------------------------------------------------------
# Target position inside MVT tile
# ------------------------------------------------------------

global_x, global_y = lonlat_to_global_pixel(
    target_lon,
    target_lat,
    z
)

local_x = (global_x - tile_x) * EXTENT
local_y = (global_y - tile_y) * EXTENT


print()
print("=" * 70)
print("GFW GEOMETRY VALIDATION")
print("=" * 70)

print()
print("TARGET")
print(f"Latitude  : {target_lat}")
print(f"Longitude : {target_lon}")

print()
print("TILE")
print(f"Zoom : {z}")
print(f"X    : {tile_x}")
print(f"Y    : {tile_y}")

print()
print("TARGET MVT LOCAL POSITION")
print(f"Local X : {local_x:.2f}")
print(f"Local Y : {local_y:.2f}")


# ------------------------------------------------------------
# Validate every cell currently used
# ------------------------------------------------------------

print()
print("=" * 70)
print("CELL VALIDATION")
print("=" * 70)

for cell_id, cell in data["cell_locations"].items():

    old_lat = cell["lat"]
    old_lon = cell["lon"]

    cell_x = cell["local_x"]
    cell_y = cell["local_y"]

    # Convert MVT local coordinates back to global tile coordinates
    cell_global_x = tile_x + cell_x / EXTENT
    cell_global_y = tile_y + cell_y / EXTENT

    # Convert to geographic coordinates
    corrected_lat, corrected_lon = global_pixel_to_lonlat(
        cell_global_x,
        cell_global_y,
        z
    )

    corrected_distance = haversine(
        target_lat,
        target_lon,
        corrected_lat,
        corrected_lon
    )

    old_distance = cell["distance_km"]

    print()
    print(f"Cell {cell_id}")
    print(f"  MVT local : ({cell_x:.1f}, {cell_y:.1f})")

    print(
        f"  OLD       : "
        f"{old_lat:.6f}, {old_lon:.6f}"
    )

    print(
        f"  CORRECTED : "
        f"{corrected_lat:.6f}, {corrected_lon:.6f}"
    )

    print(
        f"  OLD DIST  : "
        f"{old_distance:.2f} km"
    )

    print(
        f"  NEW DIST  : "
        f"{corrected_distance:.2f} km"
    )

print()
print("=" * 70)
print("Validation complete.")
print("=" * 70)