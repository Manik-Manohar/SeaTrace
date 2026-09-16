import os
import json
import math
import urllib.parse
import urllib.request
from datetime import datetime


# ============================================================
# HISTORICAL WIND DATA FOR OIL-SPILL CANDIDATES
# ============================================================

OUTPUT_DIR = "data/results/environmental"
OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "historical_wind_candidates.json"
)

DATE = "2026-08-01"

# Sentinel-1 acquisition time
ACQUISITION_HOUR = 15

# Candidate locations
CANDIDATES = {
    3: {
        "latitude": -16.417958,
        "longitude": 51.869334,
        "ai_score": 98.37,
        "sar_score": 69.7,
    },

    5: {
        "latitude": -15.345961,
        "longitude": 51.524552,
        "ai_score": 67.20,
        "sar_score": 68.8,
    },

    8: {
        "latitude": -16.245959,
        "longitude": 51.879733,
        "ai_score": 80.82,
        "sar_score": 68.5,
    },

    15: {
        "latitude": -14.908362,
        "longitude": 51.549351,
        "ai_score": 85.96,
        "sar_score": 66.3,
    },
}


# ============================================================
# FUNCTIONS
# ============================================================

def fetch_wind(latitude, longitude):

    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": DATE,
        "end_date": DATE,
        "hourly": "wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "ms",
        "timezone": "GMT",
        "cell_selection": "sea",
    }

    query = urllib.parse.urlencode(params)

    url = (
        "https://archive-api.open-meteo.com/v1/archive?"
        + query
    )

    print()
    print("Requesting:")
    print(url)

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                "Maritime-Oil-Spill-Research/1.0"
        }
    )

    with urllib.request.urlopen(
        request,
        timeout=60
    ) as response:

        data = json.loads(
            response.read().decode("utf-8")
        )

    return data


def wind_to_vector(speed_ms, direction_deg):

    """
    Meteorological wind direction means the direction
    FROM which the wind is blowing.

    For drift approximation, we need the direction
    TOWARD which the air is moving.

    Therefore we add 180 degrees.
    """

    if speed_ms is None or direction_deg is None:
        return None, None

    direction_to = (
        float(direction_deg) + 180.0
    ) % 360.0

    radians = math.radians(direction_to)

    eastward = (
        float(speed_ms) *
        math.sin(radians)
    )

    northward = (
        float(speed_ms) *
        math.cos(radians)
    )

    return eastward, northward


def analyze_candidate(candidate_id, info):

    data = fetch_wind(
        info["latitude"],
        info["longitude"]
    )

    hourly = data.get(
        "hourly",
        {}
    )

    times = hourly.get(
        "time",
        []
    )

    wind_speed = hourly.get(
        "wind_speed_10m",
        []
    )

    wind_direction = hourly.get(
        "wind_direction_10m",
        []
    )

    records = []

    for i in range(len(times)):

        timestamp = times[i]

        speed = wind_speed[i]

        direction = wind_direction[i]

        eastward, northward = wind_to_vector(
            speed,
            direction
        )

        hour = int(
            timestamp[11:13]
        )

        records.append({
            "candidate_id": candidate_id,
            "timestamp": timestamp,
            "hour_utc": hour,
            "wind_speed_ms": speed,
            "wind_direction_from_deg": direction,
            "wind_direction_to_deg":
                (
                    (float(direction) + 180.0) % 360.0
                    if direction is not None
                    else None
                ),
            "wind_eastward_ms": eastward,
            "wind_northward_ms": northward,
        })

    # --------------------------------------------------------
    # Find acquisition-hour observation
    # --------------------------------------------------------

    acquisition_records = [
        r for r in records
        if r["hour_utc"] == ACQUISITION_HOUR
    ]

    acquisition_record = (
        acquisition_records[0]
        if acquisition_records
        else None
    )

    # --------------------------------------------------------
    # Calculate average vector from 12:00–18:00
    # --------------------------------------------------------

    window_records = [
        r for r in records
        if 12 <= r["hour_utc"] <= 18
    ]

    east_values = [
        r["wind_eastward_ms"]
        for r in window_records
        if r["wind_eastward_ms"] is not None
    ]

    north_values = [
        r["wind_northward_ms"]
        for r in window_records
        if r["wind_northward_ms"] is not None
    ]

    if east_values and north_values:

        avg_east = sum(east_values) / len(
            east_values
        )

        avg_north = sum(north_values) / len(
            north_values
        )

        avg_speed = math.sqrt(
            avg_east ** 2 +
            avg_north ** 2
        )

        avg_direction_to = (
            math.degrees(
                math.atan2(
                    avg_east,
                    avg_north
                )
            ) + 360
        ) % 360

    else:

        avg_east = None
        avg_north = None
        avg_speed = None
        avg_direction_to = None

    return {
        "candidate_id": candidate_id,

        "latitude": info["latitude"],
        "longitude": info["longitude"],

        "ai_score": info["ai_score"],
        "sar_score": info["sar_score"],

        "source": "Open-Meteo Historical API",

        "date": DATE,

        "acquisition_time_utc":
            (
                acquisition_record
                if acquisition_record
                else None
            ),

        "average_window": {
            "start_hour_utc": 12,
            "end_hour_utc": 18,
            "eastward_ms": avg_east,
            "northward_ms": avg_north,
            "speed_ms": avg_speed,
            "direction_to_deg": avg_direction_to,
        },

        "hourly": records,
    }


# ============================================================
# MAIN
# ============================================================

print()
print("=" * 70)
print("HISTORICAL WIND ENVIRONMENT ANALYSIS")
print("=" * 70)

print()
print("Date:", DATE)
print("Acquisition hour:", f"{ACQUISITION_HOUR:02d}:00 UTC")
print("Candidates:", len(CANDIDATES))

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)

all_results = {}

for candidate_id, info in CANDIDATES.items():

    print()
    print("-" * 70)
    print(
        f"Candidate #{candidate_id}"
    )
    print("-" * 70)

    try:

        result = analyze_candidate(
            candidate_id,
            info
        )

        all_results[str(candidate_id)] = result

        acquisition = result[
            "acquisition_time_utc"
        ]

        average = result[
            "average_window"
        ]

        if acquisition:

            print()
            print("15:00 UTC wind:")

            print(
                "  Speed:",
                acquisition[
                    "wind_speed_ms"
                ],
                "m/s"
            )

            print(
                "  Direction FROM:",
                acquisition[
                    "wind_direction_from_deg"
                ],
                "degrees"
            )

            print(
                "  Direction TO:",
                acquisition[
                    "wind_direction_to_deg"
                ],
                "degrees"
            )

        print()
        print("12:00–18:00 average vector:")

        print(
            "  Speed:",
            (
                round(
                    average["speed_ms"],
                    3
                )
                if average["speed_ms"]
                is not None
                else "N/A"
            ),
            "m/s"
        )

        print(
            "  Direction TO:",
            (
                round(
                    average["direction_to_deg"],
                    1
                )
                if average["direction_to_deg"]
                is not None
                else "N/A"
            ),
            "degrees"
        )

        print(
            "  Eastward component:",
            (
                round(
                    average["eastward_ms"],
                    3
                )
                if average["eastward_ms"]
                is not None
                else "N/A"
            ),
            "m/s"
        )

        print(
            "  Northward component:",
            (
                round(
                    average["northward_ms"],
                    3
                )
                if average["northward_ms"]
                is not None
                else "N/A"
            ),
            "m/s"
        )

    except Exception as e:

        print()
        print(
            f"ERROR for candidate #{candidate_id}:"
        )

        print(str(e))


# ============================================================
# SAVE
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        all_results,
        f,
        indent=2
    )


print()
print("=" * 70)
print("DONE")
print("=" * 70)

print()
print("Saved:")
print(OUTPUT_FILE)

print()
print(
    "These wind vectors are an environmental input,"
)

print(
    "not yet a final oil-spill drift calculation."
)

print()