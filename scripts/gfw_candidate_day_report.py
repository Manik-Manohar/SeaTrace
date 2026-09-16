import os
import json
import requests


# ============================================================
# GFW CANDIDATE REGION - FULL DAY VESSEL REPORT
# ============================================================

print("=" * 75)
print("GFW CANDIDATE REGION - FULL DAY VESSEL REPORT")
print("=" * 75)


# ============================================================
# GFW SETTINGS
# ============================================================

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    print()
    print("ERROR: GFW_API_TOKEN is not loaded.")
    raise SystemExit(1)


API_URL = (
    "https://gateway.api.globalfishingwatch.org"
    "/v3/4wings/report"
)

DATASET = "public-global-presence:latest"


# ============================================================
# SENTINEL-1 CANDIDATE
# ============================================================

TARGET_LAT = -15.824387
TARGET_LON = 51.655060

TARGET_TIME = "2026-08-01T15:01:56Z"


# ============================================================
# FULL DAY
# ============================================================

START_TIME = "2026-08-01T00:00:00Z"
END_TIME = "2026-08-02T00:00:00Z"


# ============================================================
# SEARCH AREA
# ============================================================

# Approximately 55 km around the candidate
# in each direction.

DELTA = 0.5

WEST = TARGET_LON - DELTA
EAST = TARGET_LON + DELTA

SOUTH = TARGET_LAT - DELTA
NORTH = TARGET_LAT + DELTA


# ============================================================
# GEOJSON
# ============================================================

geojson = {
    "type": "Polygon",
    "coordinates": [[
        [WEST, SOUTH],
        [EAST, SOUTH],
        [EAST, NORTH],
        [WEST, NORTH],
        [WEST, SOUTH]
    ]]
}


# ============================================================
# GFW PARAMETERS
# ============================================================

params = {
    "format": "JSON",

    "datasets[0]":
        DATASET,

    "date-range":
        f"{START_TIME},{END_TIME}",

    "temporal-resolution":
        "DAILY",

    "spatial-resolution":
        "HIGH",

    "spatial-aggregation":
        "false",

    "group-by":
        "VESSEL_ID",
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

print()

print("Sentinel-1 candidate:")
print(f"Latitude : {TARGET_LAT}")
print(f"Longitude: {TARGET_LON}")

print()

print("Sentinel-1 acquisition:")
print(TARGET_TIME)

print()

print("GFW search window:")
print(START_TIME)
print("to")
print(END_TIME)

print()

print("Search bounds:")
print(f"West : {WEST}")
print(f"South: {SOUTH}")
print(f"East : {EAST}")
print(f"North: {NORTH}")

print()

print("Temporal resolution:")
print("DAILY")

print()

print("=" * 75)
print("REQUESTING GFW")
print("=" * 75)


# ============================================================
# REQUEST BODY
# ============================================================

body = {
    "geojson": geojson
}


# ============================================================
# REQUEST
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
    print("=" * 75)
    print("REQUEST ERROR")
    print("=" * 75)

    print()
    print(e)

    raise SystemExit(1)


# ============================================================
# STATUS
# ============================================================

print()

print(
    "HTTP Status:",
    response.status_code
)


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

try:

    data = response.json()

except ValueError:

    print()
    print("ERROR: GFW returned invalid JSON.")

    print()
    print(response.text)

    raise SystemExit(1)


# ============================================================
# RAW RESPONSE
# ============================================================

print()

print("=" * 75)
print("RAW GFW RESPONSE")
print("=" * 75)

print()

print(
    json.dumps(
        data,
        indent=2
    )[:50000]
)


# ============================================================
# SAVE RAW RESULT
# ============================================================

OUTPUT_FILE = (
    "data/results/"
    "gfw_candidate_day_report_2026-08-01.json"
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
# EXTRACT REAL RECORDS
# ============================================================

records = []


if isinstance(data, dict):

    top_entries = data.get(
        "entries",
        []
    )

    if isinstance(
        top_entries,
        list
    ):

        for entry in top_entries:

            if not isinstance(
                entry,
                dict
            ):
                continue


            # -----------------------------------------------
            # Dataset-keyed response
            # -----------------------------------------------

            for key, value in entry.items():

                if (
                    "global-presence"
                    in str(key).lower()
                ):

                    if isinstance(
                        value,
                        list
                    ):

                        records.extend(
                            value
                        )


            # -----------------------------------------------
            # Direct entries response
            # -----------------------------------------------

            if not any(
                "global-presence"
                in str(k).lower()
                for k in entry.keys()
            ):

                if (
                    "vesselId"
                    in entry
                    or "vessel_id"
                    in entry
                ):

                    records.append(
                        entry
                    )


# ============================================================
# ANALYSIS
# ============================================================

print()

print("=" * 75)
print("VESSEL PRESENCE ANALYSIS")
print("=" * 75)

print()

print(
    "Actual vessel records returned:",
    len(records)
)


# ============================================================
# DISPLAY RECORDS
# ============================================================

if not records:

    print()

    print(
        "No actual vessel-presence records "
        "were returned."
    )

else:

    for i, vessel in enumerate(
        records,
        start=1
    ):

        print()

        print(
            f"{i}. "
            f"{vessel.get('shipName', 'UNKNOWN')}"
        )

        print(
            "   Vessel ID:",
            vessel.get("vesselId")
        )

        print(
            "   MMSI:",
            vessel.get("mmsi")
        )

        print(
            "   IMO:",
            vessel.get("imo")
        )

        print(
            "   Vessel type:",
            vessel.get("vesselType")
        )

        print(
            "   Date:",
            vessel.get("date")
        )

        print(
            "   Hours:",
            vessel.get("hours")
        )

        print(
            "   Latitude:",
            vessel.get("lat")
        )

        print(
            "   Longitude:",
            vessel.get("lon")
        )

        print(
            "   Entry:",
            vessel.get("entryTimestamp")
        )

        print(
            "   Exit:",
            vessel.get("exitTimestamp")
        )


# ============================================================
# FIND OUR PREVIOUS CANDIDATES
# ============================================================

KNOWN_CANDIDATES = {
    "MSC ALBA F",
    "OLENA",
    "SERENITY",
    "ZHONG HANG SHENG",
    "CHEM MELBOURNE",
    "C.EARNEST",
}


matches = []


for vessel in records:

    name = str(
        vessel.get(
            "shipName",
            ""
        )
    ).strip().upper()

    if name in KNOWN_CANDIDATES:

        matches.append(
            vessel
        )


# ============================================================
# DISPLAY MATCHES
# ============================================================

print()

print("=" * 75)
print("PREVIOUS CANDIDATE VESSEL MATCHES")
print("=" * 75)

print()

print(
    "Matches:",
    len(matches)
)


for vessel in matches:

    print()

    print(
        "Ship:",
        vessel.get(
            "shipName",
            "UNKNOWN"
        )
    )

    print(
        "Vessel ID:",
        vessel.get("vesselId")
    )

    print(
        "MMSI:",
        vessel.get("mmsi")
    )

    print(
        "IMO:",
        vessel.get("imo")
    )

    print(
        "Hours:",
        vessel.get("hours")
    )

    print(
        "Latitude:",
        vessel.get("lat")
    )

    print(
        "Longitude:",
        vessel.get("lon")
    )


# ============================================================
# MSC ALBA F
# ============================================================

msc_alba = None


for vessel in records:

    name = str(
        vessel.get(
            "shipName",
            ""
        )
    ).strip().upper()

    if name == "MSC ALBA F":

        msc_alba = vessel

        break


# ============================================================
# FINAL INTERPRETATION
# ============================================================

print()

print("=" * 75)
print("FINAL INTERPRETATION")
print("=" * 75)

print()

if msc_alba:

    print(
        "MSC ALBA F appears in the full-day "
        "candidate region."
    )

    print()

    print(
        "This is historical spatial evidence "
        "for August 1, 2026."
    )

    print()

    print(
        "However, this does NOT establish that "
        "MSC ALBA F was present at the exact "
        "Sentinel-1 acquisition time."
    )

    print()

    print(
        "It also does NOT establish that the vessel "
        "caused the suspected spill."
    )

elif records:

    print(
        "GFW returned vessel records for the "
        "full-day candidate region."
    )

    print()

    print(
        "MSC ALBA F was not among those records."
    )

    print()

    print(
        "This is useful for comparing the other "
        "vessels against our previous candidates."
    )

else:

    print(
        "GFW returned no actual vessel records "
        "for the full-day candidate region."
    )

    print()

    print(
        "This means the current GFW presence "
        "report cannot provide vessel correlation "
        "for this region/date."
    )

    print()

    print(
        "It does NOT prove that the ocean area "
        "had no vessels."
    )


# ============================================================
# SAVE
# ============================================================

print()

print("=" * 75)
print("RESULT SAVED")
print("=" * 75)

print()

print(OUTPUT_FILE)

print()

print("=" * 75)
print("TEST COMPLETE")
print("=" * 75)