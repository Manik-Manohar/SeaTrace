import os
import json
import requests


# ============================================================
# TARGET: SENTINEL-1 SUSPECTED SPILL
# ============================================================

TARGET_LAT = -15.824387
TARGET_LON = 51.655060

TARGET_TIME = "2026-08-01T15:01:56Z"

# Small region around the suspected spill
# About 0.2 degrees in each direction
DELTA = 0.20

START_TIME = "2026-08-01T12:00:00Z"
END_TIME = "2026-08-01T18:00:00Z"

DATASET = "public-global-presence:latest"


# ============================================================
# GFW VESSEL WE ARE INVESTIGATING
# MSC ALBA F
# ============================================================

TARGET_VESSEL_ID = (
    "44cc78120-0aff-04a7-579d-be71a1a9d071"
)


# ============================================================
# TOKEN
# ============================================================

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    print("ERROR: GFW_API_TOKEN is not loaded.")
    raise SystemExit(1)


HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}


# ============================================================
# REGION
# ============================================================

west = TARGET_LON - DELTA
east = TARGET_LON + DELTA
south = TARGET_LAT - DELTA
north = TARGET_LAT + DELTA


polygon = [
    [west, south],
    [east, south],
    [east, north],
    [west, north],
    [west, south],
]


geojson = {
    "type": "Polygon",
    "coordinates": [polygon],
}


# ============================================================
# REPORT API
# ============================================================

url = (
    "https://gateway.api.globalfishingwatch.org"
    "/v3/4wings/report"
)


params = {
    "spatial-resolution": "HIGH",
    "temporal-resolution": "HOURLY",
    "group-by": "VESSEL_ID",
    "datasets[0]": DATASET,
    "date-range": f"{START_TIME},{END_TIME}",
    "format": "JSON",
    "spatial-aggregation": "false",
}


body = {
    "geojson": geojson,
}


# ============================================================
# PRINT REQUEST
# ============================================================

print("=" * 70)
print("GFW MSC ALBA F HISTORICAL REPORT")
print("=" * 70)

print()
print("Sentinel-1 target:")
print(f"  Latitude : {TARGET_LAT}")
print(f"  Longitude: {TARGET_LON}")
print(f"  Time     : {TARGET_TIME}")

print()
print("Investigation vessel:")
print(f"  Vessel ID: {TARGET_VESSEL_ID}")

print()
print("Search region:")
print(f"  West : {west}")
print(f"  South: {south}")
print(f"  East : {east}")
print(f"  North: {north}")

print()
print("Time window:")
print(f"  Start: {START_TIME}")
print(f"  End  : {END_TIME}")

print()
print("Sending GFW report request...")


# ============================================================
# REQUEST
# ============================================================

response = requests.post(
    url,
    params=params,
    headers=HEADERS,
    json=body,
    timeout=120,
)


print()
print("HTTP:", response.status_code)


# ============================================================
# ERROR
# ============================================================

if response.status_code != 200:

    print()
    print("GFW API returned an error:")
    print(response.text)

    raise SystemExit(1)


# ============================================================
# PARSE RESPONSE
# ============================================================

data = response.json()

print()
print("=" * 70)
print("RAW GFW RESPONSE")
print("=" * 70)
print(json.dumps(data, indent=2))


print()
print("=" * 70)
print("REPORT RESPONSE")
print("=" * 70)

print(
    "Total records:",
    data.get("total")
)


entries = data.get("entries", [])

print(
    "Entry groups:",
    len(entries)
)


# ============================================================
# EXTRACT RECORDS
# ============================================================

records = []

for entry_group in entries:

    if not isinstance(entry_group, dict):
        continue

    for dataset_name, dataset_records in entry_group.items():

        if not isinstance(dataset_records, list):
            continue

        for record in dataset_records:

            if not isinstance(record, dict):
                continue

            records.append(record)


# ============================================================
# DISPLAY ALL VESSELS
# ============================================================

print()
print("=" * 70)
print("VESSEL RECORDS")
print("=" * 70)


if not records:

    print()
    print("No vessel records were returned.")

else:

    for i, record in enumerate(records, start=1):

        print()
        print(f"Record {i}")
        print("-" * 50)

        print(
            "Vessel ID:",
            record.get("vesselId")
        )

        print(
            "Ship name:",
            record.get("shipName")
        )

        print(
            "MMSI:",
            record.get("mmsi")
        )

        print(
            "IMO:",
            record.get("imo")
        )

        print(
            "Date:",
            record.get("date")
        )

        print(
            "Latitude:",
            record.get("lat")
        )

        print(
            "Longitude:",
            record.get("lon")
        )

        print(
            "Hours:",
            record.get("hours")
        )

        print(
            "Entry:",
            record.get("entryTimestamp")
        )

        print(
            "Exit:",
            record.get("exitTimestamp")
        )


# ============================================================
# FILTER MSC ALBA F
# ============================================================

msc_records = []

for record in records:

    if record.get("vesselId") == TARGET_VESSEL_ID:
        msc_records.append(record)


print()
print("=" * 70)
print("MSC ALBA F RESULTS")
print("=" * 70)


if not msc_records:

    print()
    print(
        "MSC ALBA F was NOT returned in this "
        "small region/time window."
    )

else:

    print()
    print(
        f"Found {len(msc_records)} MSC ALBA F record(s)."
    )

    for i, record in enumerate(msc_records, start=1):

        print()
        print(f"MSC ALBA F record {i}")
        print("-" * 50)

        print(
            "Date:",
            record.get("date")
        )

        print(
            "Latitude:",
            record.get("lat")
        )

        print(
            "Longitude:",
            record.get("lon")
        )

        print(
            "Hours:",
            record.get("hours")
        )

        print(
            "Entry:",
            record.get("entryTimestamp")
        )

        print(
            "Exit:",
            record.get("exitTimestamp")
        )


# ============================================================
# SAVE
# ============================================================

output_file = (
    "data/results/"
    "gfw_msc_alba_report_2026-08-01.json"
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

            "search_region": {
                "west": west,
                "south": south,
                "east": east,
                "north": north,
            },

            "time_window": {
                "start": START_TIME,
                "end": END_TIME,
            },

            "target_vessel": {
                "vessel_id": TARGET_VESSEL_ID,
                "name": "MSC ALBA F",
                "mmsi": "636021870",
                "imo": "9499010",
            },

            "records": records,

            "msc_alba_records": msc_records,
        },
        f,
        indent=2,
    )


print()
print("=" * 70)
print("COMPLETE")
print("=" * 70)

print()
print("Saved:")
print(output_file)