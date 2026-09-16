import os
import json
import requests


# ============================================================
# GFW CANDIDATE REGION VESSEL REPORT
# ============================================================

print("=" * 75)
print("GFW CANDIDATE REGION VESSEL REPORT")
print("=" * 75)


# ============================================================
# GFW SETTINGS
# ============================================================

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    print()
    print("ERROR: GFW_API_TOKEN is not loaded.")
    print()
    print("Load your GFW token in PowerShell first.")
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

# Sentinel-1 acquisition time
TARGET_TIME = "2026-08-01T15:01:56Z"


# ============================================================
# SEARCH TIME WINDOW
# ============================================================

# Two-hour window around the Sentinel-1 acquisition.

START_TIME = "2026-08-01T14:00:00Z"
END_TIME = "2026-08-01T16:00:00Z"


# ============================================================
# SEARCH AREA
# ============================================================

# Approximately 55 km in each direction from the
# suspected Sentinel-1 candidate.

DELTA = 0.5

WEST = TARGET_LON - DELTA
EAST = TARGET_LON + DELTA

SOUTH = TARGET_LAT - DELTA
NORTH = TARGET_LAT + DELTA


# ============================================================
# GEOJSON POLYGON
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
        "HOURLY",

    "spatial-resolution":
        "HIGH",

    "spatial-aggregation":
        "false",

    "group-by":
        "VESSEL_ID",
}


# ============================================================
# HTTP HEADERS
# ============================================================

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
    "Content-Language": "en-EN",
}


# ============================================================
# DISPLAY REQUEST INFORMATION
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

print("Dataset:")
print(DATASET)

print()

print("=" * 75)
print("REQUESTING GFW")
print("=" * 75)


# ============================================================
# REQUEST BODY
# ============================================================

# IMPORTANT:
# GFW expects GeoJSON as an actual JSON object.

body = {
    "geojson": geojson
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
    print("=" * 75)
    print("REQUEST ERROR")
    print("=" * 75)

    print()
    print(e)

    raise SystemExit(1)


# ============================================================
# HTTP STATUS
# ============================================================

print()

print("HTTP Status:", response.status_code)


# ============================================================
# HANDLE API ERROR
# ============================================================

if response.status_code != 200:

    print()

    print("=" * 75)
    print("GFW API ERROR")
    print("=" * 75)

    print()

    print(response.text)

    print()

    print(
        "The request was rejected by the GFW API."
    )

    raise SystemExit(1)


# ============================================================
# PARSE RESPONSE
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
# DISPLAY RAW RESPONSE
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
    )[:40000]
)


# ============================================================
# SAVE RAW RESPONSE
# ============================================================

OUTPUT_FILE = (
    "data/results/"
    "gfw_candidate_region_report_2026-08-01.json"
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
# EXTRACT VESSEL ENTRIES
# ============================================================

entries = []


if isinstance(data, dict):

    # --------------------------------------------------------
    # Format 1:
    # {"entries": [...]}
    # --------------------------------------------------------

    if isinstance(
        data.get("entries"),
        list
    ):

        entries = data["entries"]


    # --------------------------------------------------------
    # Format 2:
    # Dataset-keyed response
    # --------------------------------------------------------

    else:

        for key, value in data.items():

            if not isinstance(
                value,
                dict
            ):
                continue


            possible_entries = value.get(
                "entries"
            )


            if isinstance(
                possible_entries,
                list
            ):

                entries = possible_entries

                print()
                print(
                    "Dataset response detected:"
                )

                print(key)

                break


# ============================================================
# VESSEL ANALYSIS
# ============================================================

print()

print("=" * 75)
print("VESSEL ANALYSIS")
print("=" * 75)

print()

print(
    "Vessel records returned:",
    len(entries)
)


# ============================================================
# DISPLAY VESSELS
# ============================================================

if entries:

    for i, vessel in enumerate(
        entries,
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


else:

    print()

    print(
        "No vessel records were returned."
    )


# ============================================================
# CHECK OUR EXISTING CANDIDATE VESSELS
# ============================================================

KNOWN_CANDIDATES = {

    "MSC ALBA F",

    "OLENA",

    "SERENITY",

    "ZHONG HANG SHENG",

    "CHEM MELBOURNE",

    "C.EARNEST",
}


matched_candidates = []


for vessel in entries:

    ship_name = str(
        vessel.get(
            "shipName",
            ""
        )
    ).strip().upper()


    if ship_name in KNOWN_CANDIDATES:

        matched_candidates.append(
            vessel
        )


# ============================================================
# DISPLAY CANDIDATE MATCHES
# ============================================================

print()

print("=" * 75)
print("EXISTING CANDIDATE VESSEL MATCHES")
print("=" * 75)

print()

print(
    "Known candidate vessels matched:",
    len(matched_candidates)
)


for vessel in matched_candidates:

    print()

    print(
        vessel.get(
            "shipName",
            "UNKNOWN"
        )
    )

    print(
        "  Vessel ID:",
        vessel.get("vesselId")
    )

    print(
        "  MMSI:",
        vessel.get("mmsi")
    )

    print(
        "  IMO:",
        vessel.get("imo")
    )

    print(
        "  Hours:",
        vessel.get("hours")
    )

    print(
        "  Latitude:",
        vessel.get("lat")
    )

    print(
        "  Longitude:",
        vessel.get("lon")
    )


# ============================================================
# CHECK MSC ALBA F
# ============================================================

msc_found = False


for vessel in entries:

    ship_name = str(
        vessel.get(
            "shipName",
            ""
        )
    ).strip().upper()


    if ship_name == "MSC ALBA F":

        msc_found = True

        print()

        print("=" * 75)
        print("MSC ALBA F FOUND")
        print("=" * 75)

        print()

        print(
            json.dumps(
                vessel,
                indent=2
            )
        )

        break


# ============================================================
# FINAL INTERPRETATION
# ============================================================

print()

print("=" * 75)
print("FINAL RESULT")
print("=" * 75)


if msc_found:

    print()

    print(
        "MSC ALBA F appears in the "
        "acquisition-time candidate region."
    )

    print()

    print(
        "This provides useful "
        "spatial-temporal correlation evidence."
    )

    print()

    print(
        "IMPORTANT:"
    )

    print(
        "This does NOT prove that MSC ALBA F "
        "caused the oil spill."
    )


elif entries:

    print()

    print(
        "MSC ALBA F was not among the vessels "
        "returned for this region and time window."
    )

    print()

    print(
        "Other vessels were detected."
    )

    print()

    print(
        "This does NOT prove MSC ALBA F was absent."
    )


else:

    print()

    print(
        "No vessels were returned for this "
        "region and time window."
    )

    print()

    print(
        "This does NOT prove that no vessel "
        "was present."
    )


# ============================================================
# SAVE LOCATION
# ============================================================

print()

print("=" * 75)
print("RESULT SAVED")
print("=" * 75)

print()

print(
    OUTPUT_FILE
)

print()

print("=" * 75)
print("TEST COMPLETE")
print("=" * 75)