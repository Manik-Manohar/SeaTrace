import os
import pandas as pd


# ============================================================
# FILES
# ============================================================

ATTRIBUTION_FILE = (
    "data/results/drift_aware_vessel_attribution.csv"
)

IDENTITY_FILE = (
    "data/results/resolved_vessel_identities.csv"
)

OUTPUT_FILE = (
    "data/results/final_attribution_evidence.csv"
)


# ============================================================
# LOAD DATA
# ============================================================

print()
print("=" * 75)
print("BUILDING FINAL ATTRIBUTION EVIDENCE")
print("=" * 75)

print()
print("Loading attribution results...")

attr = pd.read_csv(
    ATTRIBUTION_FILE
)

print(
    "Attribution rows:",
    len(attr)
)

print()
print("Loading vessel identities...")

identity = pd.read_csv(
    IDENTITY_FILE
)

print(
    "Identity rows:",
    len(identity)
)


# ============================================================
# NORMALIZE VESSEL IDS
# ============================================================

attr["vessel_id"] = (
    attr["vessel_id"]
    .fillna("")
    .astype(str)
    .str.strip()
)

identity["vessel_id"] = (
    identity["vessel_id"]
    .fillna("")
    .astype(str)
    .str.strip()
)


# ============================================================
# BUILD RESOLVED IDENTITY FIELDS
# ============================================================

identity["resolved_name"] = (
    identity["ais_name"]
    .fillna("")
    .astype(str)
    .str.strip()
)

identity.loc[
    identity["resolved_name"] == "",
    "resolved_name"
] = (
    identity["registry_name"]
    .fillna("")
    .astype(str)
    .str.strip()
)


identity["resolved_mmsi"] = (
    identity["mmsi"]
    .fillna("")
    .astype(str)
    .str.strip()
)

identity.loc[
    identity["resolved_mmsi"] == "",
    "resolved_mmsi"
] = (
    identity["registry_mmsi"]
    .fillna("")
    .astype(str)
    .str.strip()
)


identity["resolved_imo"] = (
    identity["imo"]
    .fillna("")
    .astype(str)
    .str.strip()
)

identity.loc[
    identity["resolved_imo"] == "",
    "resolved_imo"
] = (
    identity["registry_imo"]
    .fillna("")
    .astype(str)
    .str.strip()
)


identity["resolved_flag"] = (
    identity["flag"]
    .fillna("")
    .astype(str)
    .str.strip()
)

identity.loc[
    identity["resolved_flag"] == "",
    "resolved_flag"
] = (
    identity["registry_flag"]
    .fillna("")
    .astype(str)
    .str.strip()
)


# ============================================================
# KEEP IDENTITY COLUMNS
# ============================================================

identity_clean = identity[
    [
        "vessel_id",
        "resolved_name",
        "resolved_mmsi",
        "resolved_imo",
        "resolved_flag"
    ]
].copy()


# ============================================================
# MERGE IDENTITY DATA
# ============================================================

print()
print("Merging vessel identities...")

final = attr.merge(
    identity_clean,
    on="vessel_id",
    how="left"
)


# ============================================================
# FINAL VESSEL NAME
# ============================================================

existing_name = (
    final["vessel_name"]
    .fillna("")
    .astype(str)
    .str.strip()
)

resolved_name = (
    final["resolved_name"]
    .fillna("")
    .astype(str)
    .str.strip()
)


final["final_vessel_name"] = (
    existing_name
)


unknown_mask = (
    (existing_name == "")
    |
    (existing_name.str.upper() == "UNKNOWN")
)


final.loc[
    unknown_mask,
    "final_vessel_name"
] = resolved_name[
    unknown_mask
]


final.loc[
    final["final_vessel_name"] == "",
    "final_vessel_name"
] = "UNKNOWN"


# ============================================================
# NUMERIC CLEANUP
# ============================================================

numeric_columns = [
    "candidate_id",
    "candidate_lat",
    "candidate_lon",
    "ai_oil_score",
    "sar_score",
    "min_source_corridor_distance_km",
    "acquisition_source_distance_km",
    "best_matching_hour_utc",
    "observation_count",
    "source_proximity_score",
    "acquisition_source_score",
    "temporal_score",
    "coverage_score",
    "drift_aware_attribution_score",
    "rank"
]


for column in numeric_columns:

    if column in final.columns:

        final[column] = pd.to_numeric(
            final[column],
            errors="coerce"
        )


# ============================================================
# RE-CALCULATE RANK
# ============================================================

print()
print("Calculating vessel rankings...")

final["rank"] = (
    final
    .groupby("candidate_id")[
        "drift_aware_attribution_score"
    ]
    .rank(
        ascending=False,
        method="dense"
    )
    .astype(int)
)


# ============================================================
# INVESTIGATION STATUS
# ============================================================

final["investigation_status"] = (
    "Candidate vessel"
)


final.loc[
    final["rank"] == 1,
    "investigation_status"
] = (
    "Highest-ranked potential source vessel"
)


# ============================================================
# EVIDENCE STRENGTH
# ============================================================

def classify_score(score):

    if pd.isna(score):

        return "Unknown"

    if score >= 70:

        return "Strong"

    if score >= 55:

        return "Moderate"

    if score >= 40:

        return "Weak"

    return "Low"


final["evidence_strength"] = (
    final[
        "drift_aware_attribution_score"
    ].apply(
        classify_score
    )
)


# ============================================================
# SOURCE MATCH QUALITY
# ============================================================

def classify_distance(distance):

    if pd.isna(distance):

        return "Unknown"

    if distance <= 50:

        return "Very close"

    if distance <= 100:

        return "Close"

    if distance <= 150:

        return "Moderate"

    return "Far"


final["source_proximity_class"] = (
    final[
        "min_source_corridor_distance_km"
    ].apply(
        classify_distance
    )
)


# ============================================================
# CREATE FINAL CLEAN DATASET
# ============================================================

preferred_columns = [

    # Candidate
    "candidate_id",
    "candidate_lat",
    "candidate_lon",

    # Vessel identity
    "final_vessel_name",
    "vessel_id",
    "resolved_mmsi",
    "resolved_imo",
    "resolved_flag",

    # Main scores
    "drift_aware_attribution_score",
    "rank",
    "evidence_strength",

    # Satellite evidence
    "ai_oil_score",
    "sar_score",

    # Drift evidence
    "min_source_corridor_distance_km",
    "source_proximity_class",
    "acquisition_source_distance_km",
    "best_matching_hour_utc",

    # AIS evidence
    "observation_count",

    # Component scores
    "source_proximity_score",
    "acquisition_source_score",
    "temporal_score",
    "coverage_score",

    # Interpretation
    "investigation_status"
]


available_columns = [
    column
    for column in preferred_columns
    if column in final.columns
]


final_clean = final[
    available_columns
].copy()


# ============================================================
# SORT
# ============================================================

final_clean = final_clean.sort_values(
    [
        "candidate_id",
        "rank"
    ]
)


# ============================================================
# SAVE
# ============================================================

os.makedirs(
    os.path.dirname(
        OUTPUT_FILE
    ),
    exist_ok=True
)


final_clean.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# DISPLAY RESULTS
# ============================================================

print()
print("=" * 75)
print("FINAL ATTRIBUTION SUMMARY")
print("=" * 75)

print()


for candidate_id, group in (
    final_clean.groupby(
        "candidate_id"
    )
):

    top = group.iloc[0]

    print(
        f"Candidate #{int(candidate_id)}"
    )

    print(
        f"  Highest-ranked vessel: "
        f"{top['final_vessel_name']}"
    )

    print(
        f"  Attribution score: "
        f"{top['drift_aware_attribution_score']:.1f}"
    )

    print(
        f"  Source corridor distance: "
        f"{top['min_source_corridor_distance_km']:.1f} km"
    )

    print(
        f"  Best matching hour: "
        f"{top['best_matching_hour_utc']}"
    )

    print(
        f"  Evidence strength: "
        f"{top['evidence_strength']}"
    )

    print()


# ============================================================
# FINAL FILE INFORMATION
# ============================================================

print("=" * 75)
print("FINAL EVIDENCE DATASET CREATED")
print("=" * 75)

print()

print(
    "Rows:",
    len(final_clean)
)

print()

print(
    "Columns:",
    len(final_clean.columns)
)

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
    "This is an investigation-ranking dataset."
)

print(
    "It does NOT establish legal or causal responsibility."
)

print()
print("=" * 75)
print("DONE")
print("=" * 75)