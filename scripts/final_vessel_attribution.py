import os
import math
import pandas as pd
import numpy as np


# ============================================================
# FINAL VESSEL ATTRIBUTION SCORER
# ============================================================

INPUT_FILE = "data/results/gfw_hourly_vessel_proximity.csv"
OUTPUT_FILE = "data/results/final_vessel_attribution.csv"

# Sentinel-1 acquisition time
ACQUISITION_HOUR = 15

# Main analysis window around acquisition
START_HOUR = 12
END_HOUR = 18

# Candidate information from SAR + AI analysis
CANDIDATES = {
    3: {
        "sar_score": 69.7,
        "ai_score": 98.37,
        "latitude": -16.417958,
        "longitude": 51.869334,
    },
    5: {
        "sar_score": 68.8,
        "ai_score": 67.20,
        "latitude": -15.345961,
        "longitude": 51.524552,
    },
    8: {
        "sar_score": 68.5,
        "ai_score": 80.82,
        "latitude": -16.245959,
        "longitude": 51.879733,
    },
    15: {
        "sar_score": 66.3,
        "ai_score": 85.96,
        "latitude": -14.908362,
        "longitude": 51.549351,
    },
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def normalize_inverse(value, low, high):
    """
    Converts a value where LOWER is better into 0-100,
    where 100 is best.
    """
    if pd.isna(value):
        return 0.0

    if high <= low:
        return 50.0

    value = max(low, min(high, value))

    score = 100 * (high - value) / (high - low)

    return max(0.0, min(100.0, score))


def normalize_direct(value, low, high):
    """
    Converts a value where HIGHER is better into 0-100.
    """
    if pd.isna(value):
        return 0.0

    if high <= low:
        return 50.0

    value = max(low, min(high, value))

    score = 100 * (value - low) / (high - low)

    return max(0.0, min(100.0, score))


def safe_float(value):
    try:
        return float(value)
    except Exception:
        return np.nan


# ============================================================
# LOAD DATA
# ============================================================

if not os.path.exists(INPUT_FILE):
    print()
    print("ERROR: Input file was not found:")
    print(INPUT_FILE)
    print()
    print("Make sure gfw_hourly_vessel_report.py was run successfully.")
    raise SystemExit(1)


df = pd.read_csv(INPUT_FILE)

print()
print("=" * 70)
print("FINAL VESSEL ATTRIBUTION ANALYSIS")
print("=" * 70)

print()
print("Input file:")
print(INPUT_FILE)

print()
print("Rows loaded:", len(df))

print()
print("Columns found:")
print(list(df.columns))


# ============================================================
# IDENTIFY IMPORTANT COLUMNS
# ============================================================

def find_column(possible_names):
    for name in possible_names:
        if name in df.columns:
            return name
    return None


candidate_col = find_column([
    "candidate",
    "candidate_id",
    "candidate_number",
])

vessel_id_col = find_column([
    "vessel_id",
    "vesselId",
    "id",
])

vessel_name_col = find_column([
    "vessel_name",
    "name",
])

date_col = find_column([
    "date",
    "datetime",
    "timestamp",
])

distance_col = find_column([
    "distance_km",
    "distance",
])

lat_col = find_column([
    "lat",
    "latitude",
])

lon_col = find_column([
    "lon",
    "longitude",
])


if candidate_col is None:
    print()
    print("ERROR: Could not find candidate column.")
    raise SystemExit(1)

if vessel_id_col is None:
    print()
    print("ERROR: Could not find vessel ID column.")
    raise SystemExit(1)

if date_col is None:
    print()
    print("ERROR: Could not find date/time column.")
    raise SystemExit(1)

if distance_col is None:
    print()
    print("ERROR: Could not find distance column.")
    raise SystemExit(1)


print()
print("Detected columns:")
print("Candidate :", candidate_col)
print("Vessel ID :", vessel_id_col)
print("Vessel name:", vessel_name_col)
print("Date      :", date_col)
print("Distance  :", distance_col)


# ============================================================
# CLEAN DATA
# ============================================================

df[candidate_col] = pd.to_numeric(
    df[candidate_col],
    errors="coerce"
)

df[distance_col] = pd.to_numeric(
    df[distance_col],
    errors="coerce"
)

df[date_col] = pd.to_datetime(
    df[date_col],
    errors="coerce",
    utc=True
)

df = df.dropna(
    subset=[
        candidate_col,
        vessel_id_col,
        date_col,
        distance_col
    ]
)

df["hour"] = df[date_col].dt.hour

df["candidate"] = df[candidate_col].astype(int)

df["vessel_id"] = df[vessel_id_col].astype(str)

if vessel_name_col:
    df["vessel_name_final"] = (
        df[vessel_name_col]
        .fillna("")
        .astype(str)
    )
else:
    df["vessel_name_final"] = ""


# ============================================================
# FILTER TO THE 4 IMPORTANT CANDIDATES
# ============================================================

df = df[df["candidate"].isin(CANDIDATES.keys())]

print()
print("Rows after candidate filtering:", len(df))


# ============================================================
# FILTER TO 12:00–18:00 WINDOW
# ============================================================

window_df = df[
    (df["hour"] >= START_HOUR)
    &
    (df["hour"] <= END_HOUR)
].copy()

print()
print(
    f"Analysis window: {START_HOUR:02d}:00–{END_HOUR:02d}:00 UTC"
)

print(
    "Rows inside analysis window:",
    len(window_df)
)


# ============================================================
# CALCULATE VESSEL-LEVEL FEATURES
# ============================================================

results = []


for candidate_number, candidate_info in CANDIDATES.items():

    candidate_df = window_df[
        window_df["candidate"] == candidate_number
    ].copy()

    if candidate_df.empty:
        continue

    print()
    print("-" * 70)
    print(f"CANDIDATE #{candidate_number}")
    print("-" * 70)

    grouped = candidate_df.groupby(
        ["vessel_id", "vessel_name_final"],
        dropna=False
    )

    for (vessel_id, vessel_name), vessel_df in grouped:

        vessel_df = vessel_df.sort_values("date")

        distances = vessel_df[distance_col].values

        min_distance = float(np.min(distances))

        mean_distance = float(np.mean(distances))

        observation_count = len(vessel_df)

        # ----------------------------------------------------
        # Acquisition-hour distance
        # ----------------------------------------------------

        acquisition_rows = vessel_df[
            vessel_df["hour"] == ACQUISITION_HOUR
        ]

        if not acquisition_rows.empty:
            acquisition_distance = float(
                acquisition_rows[distance_col].min()
            )
        else:
            acquisition_distance = np.nan

        # ----------------------------------------------------
        # Distances at 12, 13, 14, 15, 16, 17, 18
        # ----------------------------------------------------

        hourly_distances = {}

        for hour in range(START_HOUR, END_HOUR + 1):

            rows = vessel_df[
                vessel_df["hour"] == hour
            ]

            if not rows.empty:
                hourly_distances[hour] = float(
                    rows[distance_col].min()
                )
            else:
                hourly_distances[hour] = np.nan

        d12 = hourly_distances.get(12, np.nan)
        d13 = hourly_distances.get(13, np.nan)
        d14 = hourly_distances.get(14, np.nan)
        d15 = hourly_distances.get(15, np.nan)
        d16 = hourly_distances.get(16, np.nan)
        d17 = hourly_distances.get(17, np.nan)
        d18 = hourly_distances.get(18, np.nan)

        # ----------------------------------------------------
        # Temporal proximity
        # ----------------------------------------------------

        hours_from_acquisition = abs(
            vessel_df["hour"] - ACQUISITION_HOUR
        )

        temporal_gap = float(
            hours_from_acquisition.min()
        )

        temporal_score = normalize_inverse(
            temporal_gap,
            0,
            6
        )

        # ----------------------------------------------------
        # Acquisition proximity
        # ----------------------------------------------------

        if not pd.isna(acquisition_distance):

            proximity_score = normalize_inverse(
                acquisition_distance,
                0,
                150
            )

        else:

            proximity_score = normalize_inverse(
                min_distance,
                0,
                150
            ) * 0.5

        # ----------------------------------------------------
        # Minimum-distance score
        # ----------------------------------------------------

        min_distance_score = normalize_inverse(
            min_distance,
            0,
            150
        )

        # ----------------------------------------------------
        # Track consistency
        #
        # We look at whether the vessel gets closer toward
        # acquisition and/or moves away afterward.
        # ----------------------------------------------------

        approach_score = 50.0

        if not pd.isna(d12) and not pd.isna(d15):

            approach_change = d12 - d15

            if approach_change > 0:
                approach_score = 100.0
            elif approach_change < 0:
                approach_score = 20.0
            else:
                approach_score = 50.0

        departure_score = 50.0

        if not pd.isna(d15) and not pd.isna(d18):

            departure_change = d18 - d15

            if departure_change > 0:
                departure_score = 100.0
            elif departure_change < 0:
                departure_score = 20.0
            else:
                departure_score = 50.0

        track_consistency_score = (
            approach_score * 0.5
            +
            departure_score * 0.5
        )

        # ----------------------------------------------------
        # Observation coverage
        # ----------------------------------------------------

        coverage_score = normalize_direct(
            observation_count,
            1,
            7
        )

        # ----------------------------------------------------
        # Candidate AI/SAR scores
        # ----------------------------------------------------

        sar_score = candidate_info["sar_score"]

        ai_score = candidate_info["ai_score"]

        # ----------------------------------------------------
        # FINAL HEURISTIC ATTRIBUTION SCORE
        #
        # IMPORTANT:
        # This is NOT a probability of guilt.
        # It is only a ranking score for investigation.
        # ----------------------------------------------------

        final_score = (
            ai_score * 0.35
            +
            sar_score * 0.20
            +
            proximity_score * 0.20
            +
            temporal_score * 0.10
            +
            track_consistency_score * 0.10
            +
            coverage_score * 0.05
        )

        results.append({

            "candidate": candidate_number,

            "candidate_latitude":
                candidate_info["latitude"],

            "candidate_longitude":
                candidate_info["longitude"],

            "sar_score":
                round(sar_score, 2),

            "ai_score":
                round(ai_score, 2),

            "vessel_id":
                vessel_id,

            "vessel_name":
                vessel_name,

            "min_distance_km":
                round(min_distance, 2),

            "acquisition_distance_km":
                round(acquisition_distance, 2)
                if not pd.isna(acquisition_distance)
                else "",

            "mean_distance_km":
                round(mean_distance, 2),

            "temporal_gap_hours":
                round(temporal_gap, 2),

            "observation_count":
                observation_count,

            "distance_12h_km":
                round(d12, 2) if not pd.isna(d12) else "",

            "distance_13h_km":
                round(d13, 2) if not pd.isna(d13) else "",

            "distance_14h_km":
                round(d14, 2) if not pd.isna(d14) else "",

            "distance_15h_km":
                round(d15, 2) if not pd.isna(d15) else "",

            "distance_16h_km":
                round(d16, 2) if not pd.isna(d16) else "",

            "distance_17h_km":
                round(d17, 2) if not pd.isna(d17) else "",

            "distance_18h_km":
                round(d18, 2) if not pd.isna(d18) else "",

            "proximity_score":
                round(proximity_score, 2),

            "temporal_score":
                round(temporal_score, 2),

            "track_consistency_score":
                round(track_consistency_score, 2),

            "coverage_score":
                round(coverage_score, 2),

            "final_attribution_score":
                round(final_score, 2),

        })


# ============================================================
# CREATE OUTPUT DATAFRAME
# ============================================================

if not results:

    print()
    print("No vessel records were available in the selected window.")
    raise SystemExit(0)


result_df = pd.DataFrame(results)


# ============================================================
# RANK WITHIN EACH CANDIDATE
# ============================================================

result_df["rank"] = (
    result_df
    .groupby("candidate")["final_attribution_score"]
    .rank(
        method="first",
        ascending=False
    )
    .astype(int)
)


result_df = result_df.sort_values(
    [
        "candidate",
        "final_attribution_score"
    ],
    ascending=[
        True,
        False
    ]
)


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    os.path.dirname(OUTPUT_FILE),
    exist_ok=True
)

result_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# DISPLAY RESULTS
# ============================================================

print()
print("=" * 70)
print("FINAL RANKING")
print("=" * 70)


for candidate_number in sorted(
    result_df["candidate"].unique()
):

    candidate_results = result_df[
        result_df["candidate"] == candidate_number
    ].sort_values(
        "final_attribution_score",
        ascending=False
    )

    print()
    print(f"Candidate #{candidate_number}")

    for _, row in candidate_results.iterrows():

        vessel_name = row["vessel_name"]

        if not vessel_name or vessel_name == "nan":
            vessel_name = "UNKNOWN"

        acquisition_distance = row[
            "acquisition_distance_km"
        ]

        if acquisition_distance == "":
            acquisition_distance_text = "N/A"
        else:
            acquisition_distance_text = (
                f"{float(acquisition_distance):.1f} km"
            )

        print(
            f"  Rank {int(row['rank'])}: "
            f"{vessel_name} | "
            f"Score {row['final_attribution_score']:.1f} | "
            f"15:00 distance {acquisition_distance_text} | "
            f"Min {row['min_distance_km']:.1f} km"
        )


# ============================================================
# IMPORTANT SCIENTIFIC WARNING
# ============================================================

print()
print("=" * 70)
print("IMPORTANT")
print("=" * 70)

print(
    "This score ranks vessels for further investigation."
)

print(
    "It is NOT a probability that a vessel caused the spill."
)

print(
    "GFW report coordinates represent AIS grid-cell centers,"
)

print(
    "so the reported distances are approximate."
)

print(
    "A scientifically stronger attribution requires ocean"
)

print(
    "current/wind drift-backtracking and higher-resolution"
)

print(
    "vessel trajectory data."
)

print()
print("Saved:")
print(OUTPUT_FILE)

print()
print("=" * 70)
print("DONE")
print("=" * 70)