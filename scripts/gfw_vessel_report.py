import os
import json
import requests


# ============================================================
# SENTINEL-1 SUSPECTED SPILL CANDIDATE
# ============================================================

LAT = -15.824387
LON = 51.655060

# ~0.5 degree around candidate
DELTA = 0.5

START_DATE = "2026-08-01T00:00:00Z"
END_DATE = "2026-08-02T00:00:00Z"

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    print("ERROR: GFW_API_TOKEN is not loaded.")
    raise SystemExit(1)


# ============================================================
# CUSTOM GEOJSON POLYGON
# ============================================================

west = LON - DELTA
east = LON + DELTA
south = LAT - DELTA
north = LAT + DELTA

geojson = {
    "type": "Polygon",
    "coordinates": [[
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south]
    ]]
}


# ============================================================
# GFW 4WINGS REPORT
# ============================================================

url = (
    "https://gateway.api.globalfishingwatch.org"
    "/v3/4wings/report"
)

params = {
    "spatial-resolution": "HIGH",
    "temporal-resolution": "HOURLY",
    "spatial-aggregation": "false",
    "group-by": "VESSEL_ID",
    "datasets[0]": "public-global-presence:latest",
    "date-range": f"{START_DATE},{END_DATE}",
    "format": "JSON",
}

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

body = {
    "geojson": geojson
}


print("=" * 70)
print("GFW HISTORICAL AIS — VESSEL DISCOVERY")
print("=" * 70)

print(f"Candidate: {LAT}, {LON}")
print(f"Region: {west}, {south} → {east}, {north}")
print(f"Time: {START_DATE} → {END_DATE}")
print()
print("Requesting report...")
print()


response = requests.post(
    url,
    params=params,
    headers=headers,
    json=body,
    timeout=180
)

print("HTTP Status:", response.status_code)
print()


if response.status_code != 200:
    print("GFW ERROR:")
    print(response.text)
    raise SystemExit(1)


data = response.json()

print("SUCCESS")
print()
print(json.dumps(data, indent=2)[:20000])


# ============================================================
# SAVE RESULT
# ============================================================

output_file = (
    "data/results/"
    "gfw_vessel_presence_2026-08-01.json"
)

with open(output_file, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print()
print("=" * 70)
print("Saved:")
print(output_file)
print("=" * 70)