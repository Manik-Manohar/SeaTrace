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

DATE_RANGE = (
    "2026-08-01,2026-08-02"
)

TARGET_HOUR = "2026-08-01 15:00"

# Search radius around each candidate.
# This is a screening radius, NOT a claim that vessels
# inside it caused the spill.
RADIUS_KM = 150


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
# KNOWN GFW VESSELS
# ============================================================

KNOWN_VESSELS = {
    "f13895c9c-c0bb-d421-3f47-7f4b6aea9c49":
        {
            "name": "SERENITY",
            "mmsi": "211563450",
            "imo": "",
        },

    "5569eaa24-4cfc-0d95-a4a8-2dc99083745e":
        {
            "name": "OLENA",
            "mmsi": "269110950",
            "imo": "",
        },

    "44cc78120-0aff-04a7-579d-be71a1a9d071":
        {
            "name": "MSC ALBA F",
            "mmsi": "636021870",
            "imo": "9499010",
        },

    "3e6475de4-4928-e18e-89ea-61ce8e7c544a":
        {
            "name": "ZHONG HANG SHENG",
            "mmsi": "413238570",
            "imo": "9243605",
        },
}


# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "Authorization":
            f"Bearer {API_TOKEN}",
        "Content-Type":
            "application/json",
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

    r = 6371.0088

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
        * r
        * math.asin(
            math.sqrt(a)
        )
    )


# ============================================================
# BUILD SMALL BOUNDING BOX
# ============================================================

def make_bbox(
    lat,
    lon,
    radius_km
):

    # Approximate degrees.
    lat_delta = radius_km / 111.32

    lon_delta = (
        radius_km
        /
        (
            111.32
            *
            math.cos(
                math.radians(lat)
            )
        )
    )

    min_lat = lat - lat_delta
    max_lat = lat + lat_delta

    min_lon = lon - lon_delta
    max_lon = lon + lon_delta

    return (
        min_lat,
        min_lon,
        max_lat,
        max_lon
    )


# ============================================================
# REPORT REQUEST
# ============================================================

def request_report(
    candidate
):

    lat = candidate["lat"]
    lon = candidate["lon"]

    min_lat, min_lon, max_lat, max_lon = (
        make_bbox(
            lat,
            lon,
            RADIUS_KM
        )
    )

    url = (
        f"{BASE_URL}"
        "/v3/4wings/report"
    )

    params = {
        "spatial-resolution": "HIGH",
        "temporal-resolution": "HOURLY",
        "spatial-aggregation": "false",
        "group-by": "VESSEL_ID",
        "datasets[0]": DATASET,
        "date-range": DATE_RANGE,
        "format": "JSON",
    }

    # Bounding rectangle around candidate.
    geojson = {
        "type": "Polygon",
        "coordinates": [[
            [min_lon, min_lat],
            [max_lon, min_lat],
            [max_lon, max_lat],
            [min_lon, max_lat],
            [min_lon, min_lat],
        ]]
    }

    body = {
        "geojson": geojson
    }

    print()
    print(
        f"Candidate #{candidate['candidate_id']}"
    )

    print(
        f"Search radius: "
        f"{RADIUS_KM} km"
    )

    print(
        f"Bounding box:"
    )

    print(
        f"  {min_lat:.4f}, "
        f"{min_lon:.4f}"
    )

    print(
        f"  {max_lat:.4f}, "
        f"{max_lon:.4f}"
    )

    response = session.post(
        url,
        params=params,
        json=body,
        timeout=120
    )

    print(
        f"HTTP {response.status_code}"
    )

    if response.status_code != 200:

        print(
            response.text[:2000]
        )

        return None

    try:

        return response.json()

    except Exception as e:

        print(
            f"JSON error: {e}"
        )

        return None


# ============================================================
# EXTRACT REPORT RECORDS
# ============================================================

def extract_records(
    data
):

    records = []

    if not data:
        return records

    def walk(obj):

        if isinstance(obj, dict):

            # A report vessel record normally has
            # vesselId, lat/lon, date and hours.

            if (
                obj.get("vesselId")
                and
                (
                    obj.get("lat") is not None
                    or
                    obj.get("lon") is not None
                )
            ):

                records.append(obj)

            for value in obj.values():

                walk(value)

        elif isinstance(obj, list):

            for item in obj:

                walk(item)

    walk(data)

    return records


# ============================================================
# MAIN
# ============================================================

print("=" * 70)

print(
    "GFW HOURLY VESSEL-PRESENCE REPORT"
)

print("=" * 70)

print()

print(
    "Sentinel-1 acquisition:"
)

print(
    "2026-08-01 15:01:56 UTC"
)

print()

print(
    "Target AIS hour:"
)

print(
    TARGET_HOUR
)

print()

print(
    "Important:"
)

print(
    "Distances are calculated from GFW report "
    "grid-cell coordinates when available."
)

print(
    "They are NOT guaranteed raw AIS transmitter "
    "coordinates."
)


all_results = []


# ============================================================
# PROCESS CANDIDATES
# ============================================================

for candidate in CANDIDATES:

    data = request_report(
        candidate
    )

    if data is None:

        continue

    cid = candidate[
        "candidate_id"
    ]

    raw_file = (
        f"data/results/"
        f"gfw_hourly_report_candidate_"
        f"{cid}.json"
    )

    with open(
        raw_file,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=2
        )

    print(
        f"Raw report saved: "
        f"{raw_file}"
    )

    records = extract_records(
        data
    )

    print(
        f"Records found: "
        f"{len(records)}"
    )


    # --------------------------------------------------------
    # PROCESS RECORDS
    # --------------------------------------------------------

    for record in records:

        vessel_id = record.get(
            "vesselId"
        )

        record_lat = record.get(
            "lat"
        )

        record_lon = record.get(
            "lon"
        )

        date = record.get(
            "date"
        )

        hours = record.get(
            "hours"
        )


        if (
            record_lat is None
            or
            record_lon is None
        ):

            continue


        try:

            distance = haversine_km(
                candidate["lat"],
                candidate["lon"],
                float(record_lat),
                float(record_lon)
            )

        except (
            ValueError,
            TypeError
        ):

            continue


        identity = (
            KNOWN_VESSELS.get(
                vessel_id,
                {}
            )
        )


        result = {
            "candidate_id":
                cid,

            "candidate_lat":
                candidate["lat"],

            "candidate_lon":
                candidate["lon"],

            "ai_oil_score":
                candidate["ai_oil"],

            "sar_score":
                candidate["sar_score"],

            "vessel_id":
                vessel_id,

            "vessel_name":
                identity.get(
                    "name",
                    ""
                ),

            "mmsi":
                identity.get(
                    "mmsi",
                    ""
                ),

            "imo":
                identity.get(
                    "imo",
                    ""
                ),

            "date":
                date,

            "hours":
                hours,

            "ais_lat":
                record_lat,

            "ais_lon":
                record_lon,

            "distance_km":
                distance,
        }


        all_results.append(
            result
        )


        print()

        print(
            f"  Vessel ID: "
            f"{vessel_id}"
        )

        if identity.get("name"):

            print(
                f"  Vessel: "
                f"{identity['name']}"
            )

        print(
            f"  Date: "
            f"{date}"
        )

        print(
            f"  Hours: "
            f"{hours}"
        )

        print(
            f"  Position: "
            f"{float(record_lat):.4f}, "
            f"{float(record_lon):.4f}"
        )

        print(
            f"  Distance: "
            f"{distance:.2f} km"
        )


# ============================================================
# SORT
# ============================================================

all_results.sort(
    key=lambda x: (
        x["candidate_id"],
        x["distance_km"]
    )
)


# ============================================================
# SAVE
# ============================================================

output_file = (
    "data/results/"
    "gfw_hourly_vessel_proximity.csv"
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
    "date",
    "hours",
    "ais_lat",
    "ais_lon",
    "distance_km",
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
        all_results
    )


# ============================================================
# FINAL
# ============================================================

print()

print("=" * 70)

print(
    "HOURLY VESSEL PROXIMITY ANALYSIS COMPLETE"
)

print("=" * 70)

print()

print(
    f"Total records: "
    f"{len(all_results)}"
)

print()

print(
    "Saved:"
)

print(
    output_file
)

print()

if all_results:

    print(
        "Closest records:"
    )

    for row in all_results[:20]:

        name = (
            row["vessel_name"]
            if row["vessel_name"]
            else row["vessel_id"]
        )

        print(
            f"  Candidate #{row['candidate_id']} "
            f"→ {name} "
            f"→ {row['distance_km']:.2f} km "
            f"→ {row['date']}"
        )

else:

    print(
        "No vessel-position records were returned."
    )