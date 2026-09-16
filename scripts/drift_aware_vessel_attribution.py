import os
import json
import math
import pandas as pd
import numpy as np


# ============================================================
# DRIFT-AWARE VESSEL ATTRIBUTION
# ============================================================

AIS_FILE = (
    "data/results/gfw_hourly_vessel_proximity.csv"
)

BACKTRACK_FILE = (
    "data/results/environmental/"
    "oil_spill_backtracking_results.json"
)

OUTPUT_DIR = "data/results"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "drift_aware_vessel_attribution.csv"
)


# ============================================================
# CONFIGURATION
# ============================================================

ACQUISITION_HOUR = 15

# Six hours before acquisition through acquisition
SOURCE_START_HOUR = 9
SOURCE_END_HOUR = 15

# Prototype maximum meaningful source distance
MAX_SOURCE_DISTANCE_KM = 100.0


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
# HAVERSINE DISTANCE
# ============================================================

def haversine_km(
    lat1,
    lon1,
    lat2,
    lon2
):
    """
    Calculate great-circle distance between two
    latitude/longitude points.

    All input coordinates are in DEGREES.
    """

    earth_radius_km = 6371.0

    lat1_rad = math.radians(
        float(lat1)
    )

    lon1_rad = math.radians(
        float(lon1)
    )

    lat2_rad = math.radians(
        float(lat2)
    )

    lon2_rad = math.radians(
        float(lon2)
    )

    dlat = (
        lat2_rad
        -
        lat1_rad
    )

    dlon = (
        lon2_rad
        -
        lon1_rad
    )

    a = (
        math.sin(dlat / 2) ** 2
        +
        math.cos(lat1_rad)
        *
        math.cos(lat2_rad)
        *
        math.sin(dlon / 2) ** 2
    )

    a = max(
        0.0,
        min(1.0, a)
    )

    c = (
        2
        *
        math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )
    )

    return earth_radius_km * c


# ============================================================
# DISTANCE SCORE
# ============================================================

def distance_score(
    distance_km,
    max_distance=MAX_SOURCE_DISTANCE_KM
):
    """
    0 km     -> 100
    50 km    -> 50
    100+ km  -> 0
    """

    if pd.isna(distance_km):
        return 0.0

    if distance_km >= max_distance:
        return 0.0

    score = (
        100.0
        *
        (
            1.0
            -
            distance_km / max_distance
        )
    )

    return max(
        0.0,
        min(100.0, score)
    )


# ============================================================
# TEMPORAL SCORE
# ============================================================

def temporal_score(hour):
    """
    Maximum score at acquisition hour.
    Earlier hours receive progressively lower scores.
    """

    gap = abs(
        hour
        -
        ACQUISITION_HOUR
    )

    score = (
        100.0
        -
        gap * 16.0
    )

    return max(
        0.0,
        score
    )


# ============================================================
# LOAD JSON
# ============================================================

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
# LOAD DATA
# ============================================================

print()
print("=" * 70)
print("DRIFT-AWARE VESSEL ATTRIBUTION")
print("=" * 70)

print()
print("Loading AIS data...")

ais_df = pd.read_csv(
    AIS_FILE
)

print(
    "AIS records:",
    len(ais_df)
)

print()
print("Loading backtracking results...")

backtrack_data = load_json(
    BACKTRACK_FILE
)

print(
    "Backtracked candidates:",
    len(backtrack_data)
)


# ============================================================
# CLEAN AIS DATA
# ============================================================

ais_df["candidate_id"] = pd.to_numeric(
    ais_df["candidate_id"],
    errors="coerce"
)

ais_df["ais_lat"] = pd.to_numeric(
    ais_df["ais_lat"],
    errors="coerce"
)

ais_df["ais_lon"] = pd.to_numeric(
    ais_df["ais_lon"],
    errors="coerce"
)

ais_df["date"] = pd.to_datetime(
    ais_df["date"],
    errors="coerce",
    utc=True
)

ais_df["hour"] = (
    ais_df["date"].dt.hour
)

ais_df["vessel_id"] = (
    ais_df["vessel_id"]
    .fillna("")
    .astype(str)
)

ais_df["vessel_name"] = (
    ais_df["vessel_name"]
    .fillna("")
    .astype(str)
)


# ============================================================
# SOURCE WINDOW
# ============================================================

ais_window = ais_df[
    (ais_df["hour"] >= SOURCE_START_HOUR)
    &
    (ais_df["hour"] <= SOURCE_END_HOUR)
].copy()

print()
print(
    f"AIS comparison window: "
    f"{SOURCE_START_HOUR:02d}:00–"
    f"{SOURCE_END_HOUR:02d}:00 UTC"
)

print(
    "AIS records in window:",
    len(ais_window)
)


# ============================================================
# MAIN ANALYSIS
# ============================================================

results = []


for candidate_id in CANDIDATES:

    print()
    print("-" * 70)

    print(
        f"CANDIDATE #{candidate_id}"
    )

    print("-" * 70)


    candidate_key = str(
        candidate_id
    )


    if candidate_key not in backtrack_data:

        print(
            "No backtracking data available."
        )

        continue


    candidate_backtrack = (
        backtrack_data[
            candidate_key
        ]
    )


    trajectory = (
        candidate_backtrack[
            "trajectory"
        ]
    )


    # --------------------------------------------------------
    # SOURCE CORRIDOR
    # --------------------------------------------------------

    source_points = []


    for point in trajectory:

        hours_before = point.get(
            "hours_before_acquisition"
        )

        if hours_before is None:
            continue


        source_hour = (
            ACQUISITION_HOUR
            -
            int(hours_before)
        )


        if source_hour < 0:
            source_hour += 24


        if (
            SOURCE_START_HOUR
            <= source_hour
            <= SOURCE_END_HOUR
        ):

            source_points.append({

                "hour":
                    source_hour,

                "latitude":
                    float(
                        point["latitude"]
                    ),

                "longitude":
                    float(
                        point["longitude"]
                    ),

            })


    if not source_points:

        print(
            "No source corridor points."
        )

        continue


    # --------------------------------------------------------
    # AIS FOR THIS CANDIDATE
    # --------------------------------------------------------

    candidate_ais = ais_window[
        ais_window[
            "candidate_id"
        ]
        ==
        candidate_id
    ].copy()


    if candidate_ais.empty:

        print(
            "No AIS records in source window."
        )

        continue


    # --------------------------------------------------------
    # GROUP BY VESSEL
    # --------------------------------------------------------

    vessel_groups = candidate_ais.groupby(
        [
            "vessel_id",
            "vessel_name"
        ],
        dropna=False
    )


    for (
        vessel_id,
        vessel_name
    ), vessel_df in vessel_groups:

        vessel_df = (
            vessel_df
            .sort_values("date")
        )


        comparisons = []


        # ----------------------------------------------------
        # COMPARE AIS POSITION WITH SAME-HOUR SOURCE POINT
        # ----------------------------------------------------

        for _, ais_row in (
            vessel_df.iterrows()
        ):

            hour = int(
                ais_row["hour"]
            )


            vessel_lat = (
                ais_row["ais_lat"]
            )

            vessel_lon = (
                ais_row["ais_lon"]
            )


            if (
                pd.isna(vessel_lat)
                or
                pd.isna(vessel_lon)
            ):

                continue


            same_hour_points = [

                p for p in source_points

                if p["hour"] == hour

            ]


            if not same_hour_points:

                continue


            nearest_distance = min(

                haversine_km(

                    vessel_lat,
                    vessel_lon,

                    p["latitude"],
                    p["longitude"]

                )

                for p in same_hour_points

            )


            comparisons.append({

                "hour":
                    hour,

                "distance_km":
                    nearest_distance,

            })


        if not comparisons:

            continue


        # ----------------------------------------------------
        # MINIMUM SOURCE-CORRIDOR DISTANCE
        # ----------------------------------------------------

        min_source_distance = min(

            x["distance_km"]

            for x in comparisons

        )


        # ----------------------------------------------------
        # ACQUISITION-HOUR DISTANCE
        # ----------------------------------------------------

        acquisition_comparisons = [

            x for x in comparisons

            if x["hour"]
            ==
            ACQUISITION_HOUR

        ]


        if acquisition_comparisons:

            acquisition_source_distance = min(

                x["distance_km"]

                for x in acquisition_comparisons

            )

        else:

            acquisition_source_distance = np.nan


        # ----------------------------------------------------
        # BEST MATCH
        # ----------------------------------------------------

        best_comparison = min(

            comparisons,

            key=lambda x:
                x["distance_km"]

        )


        best_hour = int(
            best_comparison["hour"]
        )


        # ----------------------------------------------------
        # SCORES
        # ----------------------------------------------------

        source_proximity_score = (
            distance_score(
                min_source_distance
            )
        )


        if not pd.isna(
            acquisition_source_distance
        ):

            acquisition_source_score = (
                distance_score(
                    acquisition_source_distance
                )
            )

        else:

            acquisition_source_score = 0.0


        temporal = temporal_score(
            best_hour
        )


        observation_count = len(
            comparisons
        )


        coverage = min(
            100.0,
            observation_count
            /
            7.0
            *
            100.0
        )


        candidate_info = (
            CANDIDATES[
                candidate_id
            ]
        )


        ai_score = (
            candidate_info[
                "ai_score"
            ]
        )


        sar_score = (
            candidate_info[
                "sar_score"
            ]
        )


        # ----------------------------------------------------
        # FINAL DRIFT-AWARE SCORE
        # ----------------------------------------------------

        final_score = (

            ai_score * 0.25

            +

            sar_score * 0.15

            +

            source_proximity_score * 0.30

            +

            acquisition_source_score * 0.10

            +

            temporal * 0.10

            +

            coverage * 0.10

        )


        results.append({

            "candidate_id":
                candidate_id,

            "candidate_lat":
                candidate_info[
                    "latitude"
                ],

            "candidate_lon":
                candidate_info[
                    "longitude"
                ],

            "ai_oil_score":
                ai_score,

            "sar_score":
                sar_score,

            "vessel_id":
                vessel_id,

            "vessel_name":
                vessel_name,

            "min_source_corridor_distance_km":
                round(
                    min_source_distance,
                    2
                ),

            "acquisition_source_distance_km":
                (
                    round(
                        acquisition_source_distance,
                        2
                    )

                    if not pd.isna(
                        acquisition_source_distance
                    )

                    else ""
                ),

            "best_matching_hour_utc":
                best_hour,

            "observation_count":
                observation_count,

            "source_proximity_score":
                round(
                    source_proximity_score,
                    2
                ),

            "acquisition_source_score":
                round(
                    acquisition_source_score,
                    2
                ),

            "temporal_score":
                round(
                    temporal,
                    2
                ),

            "coverage_score":
                round(
                    coverage,
                    2
                ),

            "drift_aware_attribution_score":
                round(
                    final_score,
                    2
                ),

        })


# ============================================================
# CHECK RESULTS
# ============================================================

if not results:

    print()
    print(
        "No drift-aware vessel matches were found."
    )

    raise SystemExit(0)


result_df = pd.DataFrame(
    results
)


# ============================================================
# RANK
# ============================================================

result_df["rank"] = (

    result_df

    .groupby(
        "candidate_id"
    )[
        "drift_aware_attribution_score"
    ]

    .rank(
        method="first",
        ascending=False
    )

    .astype(int)

)


result_df = (
    result_df
    .sort_values(
        [
            "candidate_id",
            "drift_aware_attribution_score"
        ],
        ascending=[
            True,
            False
        ]
    )
)


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


result_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# PRINT RESULTS
# ============================================================

print()
print("=" * 70)

print(
    "DRIFT-AWARE FINAL RANKING"
)

print("=" * 70)


for candidate_id in sorted(
    result_df[
        "candidate_id"
    ].unique()
):

    candidate_results = (
        result_df[
            result_df[
                "candidate_id"
            ]
            ==
            candidate_id
        ]
        .sort_values(
            "drift_aware_attribution_score",
            ascending=False
        )
    )


    print()
    print(
        f"Candidate #{candidate_id}"
    )


    for _, row in (
        candidate_results
        .head(10)
        .iterrows()
    ):

        name = (
            row["vessel_name"]
        )


        if (
            not name
            or
            name == "nan"
        ):

            name = "UNKNOWN"


        print(

            f"  Rank "
            f"{int(row['rank'])}: "

            f"{name} | "

            f"Score "
            f"{row['drift_aware_attribution_score']:.1f} | "

            f"Source distance "
            f"{row['min_source_corridor_distance_km']:.1f} km | "

            f"Best hour "
            f"{int(row['best_matching_hour_utc']):02d}:00 UTC"

        )


# ============================================================
# SCIENTIFIC NOTE
# ============================================================

print()
print("=" * 70)

print(
    "IMPORTANT SCIENTIFIC NOTE"
)

print("=" * 70)

print(
    "This is a drift-aware investigation ranking."
)

print(
    "It is NOT proof that a vessel caused an oil spill."
)

print(
    "The drift model is first-order and uses an assumed"
)

print(
    "windage factor."
)

print(
    "GFW positions are AIS grid-cell-center estimates."
)

print(
    "Higher-resolution trajectories and validated"
)

print(
    "oceanographic modeling are required for confirmation."
)

print()
print(
    "Saved:"
)

print(
    OUTPUT_FILE
)

print()
print("=" * 70)

print("DONE")

print("=" * 70)