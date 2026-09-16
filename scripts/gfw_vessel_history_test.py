import os
import json
import requests


# ============================================================
# GFW VESSEL-SPECIFIC HISTORICAL PRESENCE TEST
# ============================================================

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    print("ERROR: GFW_API_TOKEN is not loaded.")
    raise SystemExit(1)


API_URL = (
    "https://gateway.api.globalfishingwatch.org"
    "/v3/4wings/report"
)


# ============================================================
# VESSEL
# ============================================================

VESSEL_NAME = "MSC ALBA F"

VESSEL_ID = (
    "44cc78120-0aff-04a7-579d-be71a1a9d071"
)


# ============================================================
# SENTINEL-1 TARGET
# ============================================================

TARGET_LAT = -15.824387
TARGET_LON = 51.655060

TARGET_TIME = "2026-08-01T15:01:56Z"


# ============================================================
# TIME WINDOW
# ============================================================

START_TIME = "2026-08-01T14:00:00Z"
END_TIME   = "2026-08-01T16:00:00Z"


# ============================================================
# SEARCH AREA
# ============================================================

# Approximately 55 km in each direction.

DELTA = 0.5

WEST = TARGET_LON - DELTA
EAST = TARGET_LON + DELTA
SOUTH = TARGET_LAT - DELTA
NORTH = TARGET_LAT + DELTA


# ============================================================
# GEOJSON
# ============================================================

geojson = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [WEST, SOUTH],
                    [EAST, SOUTH],
                    [EAST, NORTH],
                    [WEST, NORTH],
                    [WEST, SOUTH]
                ]]
            }
        }
    ]
}


# ============================================================
# PARAMETERS
# ============================================================

params = {

    "spatial-resolution": "HIGH",

    "format": "JSON",

    "group-by": "VESSEL_ID",

    "temporal-resolution": "HOURLY",

    "datasets[0]":
        "public-global-presence:latest",

    "date-range":
        f"{START_TIME},{END_TIME}",

    "spatial-aggregation":
        "false",

    # IMPORTANT:
    # Filter specifically for this GFW vessel.
    "filters[0]":
        f"vessel_id = '{VESSEL_ID}'",
}


# ============================================================
# HEADERS
# ============================================================

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Content-Language": "en-EN",
}


# ============================================================
# DISPLAY
# ============================================================

print("=" * 75)
print("GFW VESSEL-SPECIFIC HISTORICAL PRESENCE TEST")
print("=" * 75)

print()
print("Vessel:")
print(VESSEL_NAME)

print()
print("GFW Vessel ID:")
print(VESSEL_ID)

print()
print("Sentinel-1 acquisition:")
print(TARGET_TIME)

print()
print("Search time:")
print(START_TIME)
print("to")
print(END_TIME)

print()
print("Target coordinate:")
print(f"Latitude : {TARGET_LAT}")
print(f"Longitude: {TARGET_LON}")

print()
print("Search bounds:")
print(f"West : {WEST}")
print(f"South: {SOUTH}")
print(f"East : {EAST}")
print(f"North: {NORTH}")

print()
print("=" * 75)
print("REQUESTING GFW")
print("=" * 75)


# ============================================================
# REQUEST BODY
# ============================================================

# GFW expects the GeoJSON as a STRING in the "geojson" field.

body = {
    "geojson": json.dumps(geojson)
}


# ============================================================
# SEND REQUEST
# ============================================================

try:

    response = requests.post(
        API_URL,
        params=params,
        headers=headers,
        json=body,
        timeout=180
    )

except requests.RequestException as e:

    print()
    print("REQUEST ERROR:")
    print(e)

    raise SystemExit(1)


# ============================================================
# STATUS
# ============================================================

print()
print("HTTP Status:", response.status_code)


# ============================================================
# ERROR
# ============================================================

if response.status_code != 200:

    print()
    print("=" * 75)
    print("GFW API ERROR")
    print("=" * 75)

    print()
    print(response.text)

    raise SystemExit(1)


# ============================================================
# PARSE
# ============================================================

data = response.json()


# ============================================================
# DISPLAY RESPONSE
# ============================================================

print()
print("=" * 75)
print("GFW RESPONSE")
print("=" * 75)

print()

print(
    json.dumps(
        data,
        indent=2
    )[:30000]
)


# ============================================================
# SAVE
# ============================================================

OUTPUT_FILE = (
    "data/results/"
    "gfw_msc_alba_vessel_history_2026-08-01.json"
)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        data,
        f,
        indent=2
    )


# ============================================================
# ANALYZE RESULT
# ============================================================

entries = data.get("entries", [])


print()
print("=" * 75)
print("ANALYSIS")
print("=" * 75)

print()
print("Entries returned:", len(entries))


if entries:

    print()

    for i, entry in enumerate(entries, start=1):

        print(f"Record {i}")
        print("-" * 50)

        print(
            "Vessel ID:",
            entry.get("vesselId")
        )

        print(
            "Ship name:",
            entry.get("shipName")
        )

        print(
            "MMSI:",
            entry.get("mmsi")
        )

        print(
            "Date:",
            entry.get("date")
        )

        print(
            "Hours:",
            entry.get("hours")
        )

        print(
            "Latitude:",
            entry.get("lat")
        )

        print(
            "Longitude:",
            entry.get("lon")
        )

        print(
            "Entry:",
            entry.get("entryTimestamp")
        )

        print(
            "Exit:",
            entry.get("exitTimestamp")
        )

        print()


else:

    print()
    print(
        "MSC ALBA F was NOT returned for this "
        "specific vessel/time/region query."
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This does NOT prove that MSC ALBA F was absent."
    )

    print(
        "It only means the GFW report returned no "
        "matching record for this request."
    )


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 75)
print("RESULT SAVED")
print("=" * 75)

print()
print(OUTPUT_FILE)

print()
print("TEST COMPLETE")
print("=" * 75)