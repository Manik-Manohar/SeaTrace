import os
import json
import math
import pandas as pd


# ============================================================
# OIL SPILL DRIFT BACKTRACKING
# ============================================================

WIND_FILE = (
    "data/results/environmental/"
    "historical_wind_candidates.json"
)

CURRENT_FILE = (
    "data/results/environmental/"
    "historical_ocean_currents_candidates.json"
)

OUTPUT_DIR = "data/results/environmental"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "oil_spill_backtracking_results.json"
)


# ============================================================
# CONFIGURATION
# ============================================================

# Sentinel-1 acquisition time
ACQUISITION_HOUR = 15

# Backtrack from the observed slick for 6 hours
BACKTRACK_HOURS = 6

# Time step
STEP_HOURS = 1.0

# Approximate windage fraction for a first-order prototype.
#
# This is NOT an oil-specific calibrated value.
# We keep it configurable so it can later be replaced
# with an empirically validated value.
WINDAGE_FACTOR = 0.03


# ============================================================
# CANDIDATES
# ============================================================

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

def destination_point(
    latitude,
    longitude,
    east_km,
    north_km
):
    """
    Move a geographic point by east/north distances.

    Positive east_km  = east
    Negative east_km  = west

    Positive north_km = north
    Negative north_km = south
    """

    km_per_degree_lat = 111.32

    km_per_degree_lon = (
        111.32
        * math.cos(
            math.radians(latitude)
        )
    )

    new_latitude = (
        latitude
        +
        north_km / km_per_degree_lat
    )

    if abs(km_per_degree_lon) < 0.001:
        new_longitude = longitude
    else:
        new_longitude = (
            longitude
            +
            east_km / km_per_degree_lon
        )

    return (
        new_latitude,
        new_longitude
    )


def get_hour_record(
    records,
    hour
):
    """
    Find the record closest to a requested UTC hour.
    """

    if not records:
        return None

    exact = [
        r for r in records
        if r.get("hour_utc") == hour
    ]

    if exact:
        return exact[0]

    return None


def load_json(path):

    if not os.path.exists(path):

        print()
        print("ERROR: File not found:")
        print(path)

        raise SystemExit(1)

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# LOAD ENVIRONMENTAL DATA
# ============================================================

print()
print("=" * 70)
print("OIL-SPILL DRIFT BACKTRACKING")
print("=" * 70)

print()
print("Loading wind data...")

wind_data = load_json(
    WIND_FILE
)

print(
    "Loading ocean-current data..."
)

current_data = load_json(
    CURRENT_FILE
)


# ============================================================
# BACKTRACK ONE CANDIDATE
# ============================================================

def backtrack_candidate(
    candidate_id,
    info
):

    latitude = info["latitude"]

    longitude = info["longitude"]

    wind_candidate = wind_data.get(
        str(candidate_id)
    )

    current_candidate = current_data.get(
        str(candidate_id)
    )

    if (
        wind_candidate is None
        or current_candidate is None
    ):

        return None


    wind_records = wind_candidate.get(
        "hourly",
        []
    )

    current_records = current_candidate.get(
        "hourly",
        []
    )


    # --------------------------------------------------------
    # Start at detected slick
    # --------------------------------------------------------

    current_lat = latitude
    current_lon = longitude


    trajectory = []

    trajectory.append({

        "step": 0,

        "hours_before_acquisition": 0,

        "latitude":
            current_lat,

        "longitude":
            current_lon,

        "description":
            "Detected slick location"

    })


    # --------------------------------------------------------
    # Backtrack hour by hour
    # --------------------------------------------------------

    for step in range(
        1,
        BACKTRACK_HOURS + 1
    ):

        target_hour = (
            ACQUISITION_HOUR
            - step
        )

        # Handle midnight crossing
        if target_hour < 0:
            target_hour += 24


        wind = get_hour_record(
            wind_records,
            target_hour
        )

        current = get_hour_record(
            current_records,
            target_hour
        )


        if wind is None:
            print(
                f"WARNING Candidate #{candidate_id}: "
                f"No wind data for hour {target_hour}"
            )

            continue


        if current is None:
            print(
                f"WARNING Candidate #{candidate_id}: "
                f"No current data for hour {target_hour}"
            )

            continue


        # ----------------------------------------------------
        # WIND
        # ----------------------------------------------------

        wind_east_ms = (
            wind.get(
                "wind_eastward_ms"
            )
        )

        wind_north_ms = (
            wind.get(
                "wind_northward_ms"
            )
        )


        if (
            wind_east_ms is None
            or wind_north_ms is None
        ):

            continue


        # ----------------------------------------------------
        # CURRENT
        # ----------------------------------------------------

        current_east_kmh = (
            current.get(
                "current_eastward_kmh"
            )
        )

        current_north_kmh = (
            current.get(
                "current_northward_kmh"
            )
        )


        if (
            current_east_kmh is None
            or current_north_kmh is None
        ):

            continue


        # ----------------------------------------------------
        # Convert wind m/s → km/h
        # ----------------------------------------------------

        wind_east_kmh = (
            wind_east_ms
            * 3.6
        )

        wind_north_kmh = (
            wind_north_ms
            * 3.6
        )


        # ----------------------------------------------------
        # Surface drift
        #
        # current + windage × wind
        # ----------------------------------------------------

        drift_east_kmh = (

            current_east_kmh

            +

            WINDAGE_FACTOR
            * wind_east_kmh
        )


        drift_north_kmh = (

            current_north_kmh

            +

            WINDAGE_FACTOR
            * wind_north_kmh
        )


        # ----------------------------------------------------
        # BACKTRACK
        #
        # We move opposite to the forward drift vector.
        # ----------------------------------------------------

        current_lat, current_lon = (
            destination_point(

                current_lat,

                current_lon,

                -drift_east_kmh
                * STEP_HOURS,

                -drift_north_kmh
                * STEP_HOURS
            )
        )


        drift_speed = math.sqrt(

            drift_east_kmh ** 2

            +

            drift_north_kmh ** 2

        )


        drift_direction = (

            math.degrees(

                math.atan2(

                    drift_east_kmh,

                    drift_north_kmh
                )

            )

            + 360

        ) % 360


        trajectory.append({

            "step":
                step,

            "hours_before_acquisition":
                step,

            "source_hour_utc":
                target_hour,

            "latitude":
                current_lat,

            "longitude":
                current_lon,

            "drift_speed_kmh":
                drift_speed,

            "drift_direction_to_deg":
                drift_direction,

            "current_eastward_kmh":
                current_east_kmh,

            "current_northward_kmh":
                current_north_kmh,

            "wind_eastward_kmh":
                wind_east_kmh,

            "wind_northward_kmh":
                wind_north_kmh,

            "windage_factor":
                WINDAGE_FACTOR

        })


    # --------------------------------------------------------
    # Calculate total backtracked displacement
    # --------------------------------------------------------

    final_point = trajectory[-1]

    final_lat = final_point["latitude"]

    final_lon = final_point["longitude"]


    displacement_km = (
        math.sqrt(

            (
                (
                    final_lat
                    - latitude
                )
                * 111.32
            ) ** 2

            +

            (
                (
                    final_lon
                    - longitude
                )
                * 111.32
                *
                math.cos(
                    math.radians(
                        latitude
                    )
                )
            ) ** 2

        )
    )


    return {

        "candidate_id":
            candidate_id,

        "detected_location": {

            "latitude":
                latitude,

            "longitude":
                longitude,

        },

        "ai_score":
            info["ai_score"],

        "sar_score":
            info["sar_score"],

        "backtrack_hours":
            BACKTRACK_HOURS,

        "windage_factor":
            WINDAGE_FACTOR,

        "estimated_source_region": {

            "latitude":
                final_lat,

            "longitude":
                final_lon,

        },

        "backtracked_displacement_km":
            displacement_km,

        "trajectory":
            trajectory,

    }


# ============================================================
# RUN ALL CANDIDATES
# ============================================================

results = {}


for candidate_id, info in CANDIDATES.items():

    print()
    print("-" * 70)

    print(
        f"Candidate #{candidate_id}"
    )

    print("-" * 70)

    result = backtrack_candidate(
        candidate_id,
        info
    )

    if result is None:

        print(
            "Could not calculate trajectory."
        )

        continue


    results[
        str(candidate_id)
    ] = result


    source = result[
        "estimated_source_region"
    ]


    print()

    print(
        "Detected slick:"
    )

    print(
        f"  {latitude if False else info['latitude']:.6f}, "
        f"{info['longitude']:.6f}"
    )


    print()

    print(
        "Estimated 6-hour backtracked source:"
    )

    print(
        f"  Latitude : "
        f"{source['latitude']:.6f}"
    )

    print(
        f"  Longitude: "
        f"{source['longitude']:.6f}"
    )


    print()

    print(
        "Backtracked displacement:"
    )

    print(
        f"  "
        f"{result['backtracked_displacement_km']:.2f} km"
    )


    print()

    print(
        "Trajectory:"
    )


    for point in result[
        "trajectory"
    ]:

        print(

            f"  "
            f"{point['hours_before_acquisition']:>2}h before "
            f"→ "
            f"{point['latitude']:.5f}, "
            f"{point['longitude']:.5f}"

        )


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        results,
        f,
        indent=2
    )


# ============================================================
# FINISH
# ============================================================

print()
print("=" * 70)

print(
    "BACKTRACKING COMPLETE"
)

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
    "IMPORTANT:"
)

print(
    "This is a first-order drift model."
)

print(
    "The estimated source is a plausible"
)

print(
    "backtracked region, not a confirmed"
)

print(
    "spill origin."
)

print()