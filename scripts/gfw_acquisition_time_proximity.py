import os
import csv
import json
import math
import requests


# ============================================================
# CONFIG
# ============================================================

API_TOKEN = os.environ.get("GFW_API_TOKEN")

if not API_TOKEN:
    raise RuntimeError(
        "GFW_API_TOKEN is not loaded."
    )


BASE_URL = (
    "https://gateway.api.globalfishingwatch.org"
)

DATASET = (
    "public-global-presence:latest"
)

# Sentinel-1 acquisition time
ACQUISITION_DATE = "2026-08-01"

ACQUISITION_HOUR = 15

ACQUISITION_TIME_TEXT = (
    "2026-08-01 15:01:56 UTC"
)


# ============================================================
# CANDIDATES
# ============================================================

CANDIDATES = [
    {
        "candidate_id": 3,
        "lat": -16.417958157423403,
        "lon": 51.86933396852679,
        "ai_oil": 98.37,
        "sar_score": 69.7,
    },
    {
        "candidate_id": 8,
        "lat": -16.245958546388568,
        "lon": 51.879733429957156,
        "ai_oil": 80.82,
        "sar_score": 68.5,
    },
    {
        "candidate_id": 15,
        "lat": -14.90836157127114,
        "lon": 51.54935053990012,
        "ai_oil": 85.96,
        "sar_score": 66.3,
    },
    {
        "candidate_id": 5,
        "lat": -15.345960581671399,
        "lon": 51.52455182418155,
        "ai_oil": 67.20,
        "sar_score": 68.8,
    },
]


# ============================================================
# GFW VESSELS ALREADY CORRELATED
# ============================================================

VESSELS = [
    {
        "vessel_id":
            "f13895c9c-c0bb-d421-3f47-7f4b6aea9c49",
        "name":
            "SERENITY",
        "mmsi":
            "211563450",
        "imo":
            "",
    },
    {
        "vessel_id":
            "5569eaa24-4cfc-0d95-a4a8-2dc99083745e",
        "name":
            "OLENA",
        "mmsi":
            "269110950",
        "imo":
            "",
    },
    {
        "vessel_id":
            "44cc78120-0aff-04a7-579d-be71a1a9d071",
        "name":
            "MSC ALBA F",
        "mmsi":
            "636021870",
        "imo":
            "9499010",
    },
    {
        "vessel_id":
            "3e6475de4-4928-e18e-89ea-61ce8e7c544a",
        "name":
            "ZHONG HANG SHENG",
        "mmsi":
            "413238570",
        "imo":
            "9243605",
    },
]


# ============================================================
# HTTP SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "Authorization":
            f"Bearer {API_TOKEN}"
    }
)


# ============================================================
# HAVERSINE
# ============================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2
):

    radius = 6371.0088

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dlat = math.radians(
        lat2 - lat1
    )

    dlon = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(p1)
        *
        math.cos(p2)
        *
        math.sin(dlon / 2) ** 2
    )

    return (
        2
        *
        radius
        *
        math.asin(
            math.sqrt(a)
        )
    )


# ============================================================
# GFW TILE CONVERSION
# ============================================================

def lonlat_to_tile(
    lon,
    lat,
    zoom
):

    lat = max(
        min(lat, 85.05112878),
        -85.05112878
    )

    n = 2 ** zoom

    x = int(
        (lon + 180)
        / 360
        * n
    )

    lat_rad = math.radians(
        lat
    )

    y = int(
        (
            1
            -
            math.asinh(
                math.tan(
                    lat_rad
                )
            )
            /
            math.pi
        )
        /
        2
        *
        n
    )

    return x, y


# ============================================================
# GET GFW TILE
# ============================================================

def get_tile(
    z,
    x,
    y
):

    url = (
        f"{BASE_URL}"
        f"/v3/4wings/tile/heatmap/"
        f"{z}/{x}/{y}"
    )

    params = {
        "format": "MVT",
        "interval": "HOUR",
        "temporal-aggregation": "true",
        "datasets[0]": DATASET,
        "date-range":
            "2026-08-01,2026-08-02",
    }

    response = session.get(
        url,
        params=params,
        timeout=60
    )

    print(
        f"Tile {z}/{x}/{y}: "
        f"HTTP {response.status_code}"
    )

    if response.status_code != 200:

        print(
            response.text[:500]
        )

        return None

    return response.content


# ============================================================
# MAIN
# ============================================================

print("=" * 70)

print(
    "GFW ACQUISITION-TIME AIS ANALYSIS"
)

print("=" * 70)

print()

print(
    "Sentinel-1 acquisition:"
)

print(
    ACQUISITION_TIME_TEXT
)

print()

print(
    "Target acquisition hour:"
)

print(
    f"{ACQUISITION_DATE} "
    f"{ACQUISITION_HOUR:02d}:00 UTC"
)


# ============================================================
# IMPORTANT
# ============================================================

print()
print(
    "NOTE:"
)

print(
    "This stage checks GFW AIS presence "
    "during the acquisition hour."
)

print(
    "It does NOT prove that a vessel caused "
    "the detected anomaly."
)

print()


# ============================================================
# PROCESS CANDIDATES
# ============================================================

results = []


for candidate in CANDIDATES:

    cid = candidate[
        "candidate_id"
    ]

    lat = candidate[
        "lat"
    ]

    lon = candidate[
        "lon"
    ]

    print("-" * 70)

    print(
        f"Candidate #{cid}"
    )

    print(
        f"Location: "
        f"{lat:.6f}, {lon:.6f}"
    )

    print(
        f"AI oil score: "
        f"{candidate['ai_oil']:.2f}%"
    )

    print(
        f"SAR score: "
        f"{candidate['sar_score']:.1f}"
    )

    x, y = lonlat_to_tile(
        lon,
        lat,
        7
    )

    print(
        f"GFW tile: "
        f"7/{x}/{y}"
    )

    tile = get_tile(
        7,
        x,
        y
    )

    if tile is None:

        print(
            "Could not retrieve tile."
        )

        continue

    print(
        "Hourly GFW tile retrieved."
    )

    print(
        "Candidate acquisition-time "
        "analysis prepared."
    )

    print()

    # --------------------------------------------------------
    # At this stage we record the candidate and the vessels
    # that were already associated with it.
    #
    # The exact geographic position of each vessel is NOT
    # assumed from the cell center.
    # --------------------------------------------------------

    for vessel in VESSELS:

        results.append(
            {
                "candidate_id":
                    cid,

                "candidate_lat":
                    lat,

                "candidate_lon":
                    lon,

                "ai_oil_score":
                    candidate[
                        "ai_oil"
                    ],

                "sar_score":
                    candidate[
                        "sar_score"
                    ],

                "vessel_id":
                    vessel[
                        "vessel_id"
                    ],

                "vessel_name":
                    vessel[
                        "name"
                    ],

                "mmsi":
                    vessel[
                        "mmsi"
                    ],

                "imo":
                    vessel[
                        "imo"
                    ],

                "acquisition_date":
                    ACQUISITION_DATE,

                "acquisition_hour":
                    ACQUISITION_HOUR,

                "status":
                    "requires_hourly_track_position",
            }
        )


# ============================================================
# SAVE RESULTS
# ============================================================

output_file = (
    "data/results/"
    "gfw_acquisition_time_analysis.csv"
)


fieldnames = [
    "candidate_id",
    "candidate_lat",
    "candidate_lon",
    "ai_oil_score",
    "sar_score",
    "vessel_id",
    "vessel_name",
    "mmsi",
    "imo",
    "acquisition_date",
    "acquisition_hour",
    "status",
]


with open(
    output_file,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames
    )

    writer.writeheader()

    writer.writerows(
        results
    )


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)

print(
    "ACQUISITION-TIME ANALYSIS COMPLETE"
)

print("=" * 70)

print()

print(
    "Saved:"
)

print(
    output_file
)

print()

print(
    f"Candidate-vessel records: "
    f"{len(results)}"
)

print()

print(
    "Next stage:"
)

print(
    "Resolve hourly AIS positions for these "
    "candidate-vessel pairs and calculate "
    "actual vessel-to-candidate distance."
)