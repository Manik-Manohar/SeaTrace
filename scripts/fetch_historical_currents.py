import os
import json
import math
import urllib.parse
import urllib.request


# ============================================================
# HISTORICAL OCEAN CURRENT DATA
# ============================================================

OUTPUT_DIR = "data/results/environmental"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "historical_ocean_currents_candidates.json"
)

DATE = "2026-08-01"

# Sentinel-1 acquisition time
ACQUISITION_HOUR = 15

# Candidate locations
CANDIDATES = {
    3: {
        "latitude": -16.417958,
        "longitude": 51.869334,
    },

    5: {
        "latitude": -15.345961,
        "longitude": 51.524552,
    },

    8: {
        "latitude": -16.245959,
        "longitude": 51.879733,
    },

    15: {
        "latitude": -14.908362,
        "longitude": 51.549351,
    },
}


# ============================================================
# FETCH MARINE DATA
# ============================================================

def fetch_currents(latitude, longitude):

    params = {
        "latitude": latitude,
        "longitude": longitude,

        "start_date": DATE,
        "end_date": DATE,

        "hourly": (
            "ocean_current_velocity,"
            "ocean_current_direction"
        ),

        "timezone": "GMT",

        "cell_selection": "sea",
    }

    query = urllib.parse.urlencode(params)

    url = (
        "https://marine-api.open-meteo.com/v1/marine?"
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


# ============================================================
# CURRENT VECTOR
# ============================================================

def current_to_vector(
    speed_kmh,
    direction_deg
):

    """
    Ocean current direction is already the direction
    the water is flowing TOWARD.

    0°   = North
    90°  = East
    180° = South
    270° = West

    Convert speed into eastward/northward components.
    """

    if (
        speed_kmh is None
        or direction_deg is None
    ):
        return None, None

    radians = math.radians(
        float(direction_deg)
    )

    eastward = (
        float(speed_kmh)
        * math.sin(radians)
    )

    northward = (
        float(speed_kmh)
        * math.cos(radians)
    )

    return eastward, northward


# ============================================================
# ANALYZE ONE CANDIDATE
# ============================================================

def analyze_candidate(
    candidate_id,
    info
):

    data = fetch_currents(
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

    velocities = hourly.get(
        "ocean_current_velocity",
        []
    )

    directions = hourly.get(
        "ocean_current_direction",
        []
    )

    records = []

    for i in range(len(times)):

        timestamp = times[i]

        velocity = velocities[i]

        direction = directions[i]

        eastward, northward = (
            current_to_vector(
                velocity,
                direction
            )
        )

        hour = int(
            timestamp[11:13]
        )

        records.append({

            "candidate_id":
                candidate_id,

            "timestamp":
                timestamp,

            "hour_utc":
                hour,

            "current_velocity_kmh":
                velocity,

            "current_direction_to_deg":
                direction,

            "current_eastward_kmh":
                eastward,

            "current_northward_kmh":
                northward,
        })


    # ========================================================
    # ACQUISITION HOUR
    # ========================================================

    acquisition_records = [

        r for r in records

        if r["hour_utc"]
        == ACQUISITION_HOUR

    ]

    acquisition_record = (

        acquisition_records[0]

        if acquisition_records

        else None
    )


    # ========================================================
    # 12–18 UTC WINDOW
    # ========================================================

    window_records = [

        r for r in records

        if (
            12
            <= r["hour_utc"]
            <= 18
        )

    ]


    east_values = [

        r["current_eastward_kmh"]

        for r in window_records

        if (
            r["current_eastward_kmh"]
            is not None
        )

    ]

    north_values = [

        r["current_northward_kmh"]

        for r in window_records

        if (
            r["current_northward_kmh"]
            is not None
        )

    ]


    # ========================================================
    # AVERAGE CURRENT VECTOR
    # ========================================================

    if (
        east_values
        and north_values
    ):

        avg_east = (
            sum(east_values)
            / len(east_values)
        )

        avg_north = (
            sum(north_values)
            / len(north_values)
        )

        avg_speed = math.sqrt(
            avg_east ** 2
            +
            avg_north ** 2
        )

        avg_direction = (

            math.degrees(

                math.atan2(
                    avg_east,
                    avg_north
                )

            )

            + 360

        ) % 360

    else:

        avg_east = None
        avg_north = None
        avg_speed = None
        avg_direction = None


    # ========================================================
    # RETURN
    # ========================================================

    return {

        "candidate_id":
            candidate_id,

        "latitude":
            info["latitude"],

        "longitude":
            info["longitude"],

        "source":
            "Open-Meteo Marine API",

        "date":
            DATE,

        "acquisition_time_utc":
            acquisition_record,

        "average_window": {

            "start_hour_utc":
                12,

            "end_hour_utc":
                18,

            "velocity_kmh":
                avg_speed,

            "direction_to_deg":
                avg_direction,

            "eastward_kmh":
                avg_east,

            "northward_kmh":
                avg_north,
        },

        "hourly":
            records,
    }


# ============================================================
# MAIN
# ============================================================

print()

print("=" * 70)

print(
    "HISTORICAL OCEAN CURRENT ANALYSIS"
)

print("=" * 70)

print()

print(
    "Date:",
    DATE
)

print(
    "Acquisition:",
    f"{ACQUISITION_HOUR:02d}:00 UTC"
)

print(
    "Candidates:",
    len(CANDIDATES)
)


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

        all_results[
            str(candidate_id)
        ] = result


        acquisition = result[
            "acquisition_time_utc"
        ]

        average = result[
            "average_window"
        ]


        if acquisition:

            print()

            print(
                "15:00 UTC ocean current:"
            )

            print(
                "  Velocity:",
                acquisition[
                    "current_velocity_kmh"
                ],
                "km/h"
            )

            print(
                "  Direction TO:",
                acquisition[
                    "current_direction_to_deg"
                ],
                "degrees"
            )

            print(
                "  Eastward:",
                acquisition[
                    "current_eastward_kmh"
                ],
                "km/h"
            )

            print(
                "  Northward:",
                acquisition[
                    "current_northward_kmh"
                ],
                "km/h"
            )

        else:

            print(
                "15:00 UTC observation not found."
            )


        print()

        print(
            "12:00–18:00 average current:"
        )

        print(
            "  Velocity:",
            (
                round(
                    average[
                        "velocity_kmh"
                    ],
                    4
                )

                if average[
                    "velocity_kmh"
                ]
                is not None

                else "N/A"
            ),
            "km/h"
        )

        print(
            "  Direction TO:",
            (
                round(
                    average[
                        "direction_to_deg"
                    ],
                    1
                )

                if average[
                    "direction_to_deg"
                ]
                is not None

                else "N/A"
            ),
            "degrees"
        )

        print(
            "  Eastward:",
            (
                round(
                    average[
                        "eastward_kmh"
                    ],
                    4
                )

                if average[
                    "eastward_kmh"
                ]
                is not None

                else "N/A"
            ),
            "km/h"
        )

        print(
            "  Northward:",
            (
                round(
                    average[
                        "northward_kmh"
                    ],
                    4
                )

                if average[
                    "northward_kmh"
                ]
                is not None

                else "N/A"
            ),
            "km/h"
        )


    except Exception as e:

        print()

        print(
            f"ERROR for candidate #{candidate_id}:"
        )

        print(
            str(e)
        )


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

print(
    "Saved:"
)

print(
    OUTPUT_FILE
)

print()

print(
    "Ocean currents are now available"
)

print(
    "as an environmental input for"
)

print(
    "the drift-backtracking stage."
)

print()