from pathlib import Path
import pandas as pd


# ============================================================
# FILES
# ============================================================

INPUT_FILE = Path(
    "data/results/ai_verified_candidates.csv"
)

OUTPUT_FILE = Path(
    "data/results/final_spill_candidates.csv"
)


# ============================================================
# LOAD
# ============================================================

print("=" * 70)
print("PREPARING FINAL SPILL CANDIDATES")
print("=" * 70)

df = pd.read_csv(INPUT_FILE)

print(f"\nInput candidates: {len(df)}")


# ============================================================
# AI FILTER
# ============================================================

spill_candidates = df[
    df["ai_prediction"].astype(str).str.lower()
    == "oil_spill"
].copy()

print(
    f"AI-positive candidates: "
    f"{len(spill_candidates)}"
)


# ============================================================
# NORMALIZE SCORES
# ============================================================

spill_candidates["ai_oil_score"] = (
    spill_candidates["ai_oil_probability"] * 100
)

spill_candidates["sar_score"] = (
    spill_candidates["score"]
)


# ============================================================
# STANDARDIZE CANDIDATE ID
# ============================================================

spill_candidates = spill_candidates.rename(
    columns={
        "rank": "candidate_id"
    }
)


# ============================================================
# KEEP IMPORTANT FIELDS
# ============================================================

columns = [
    "candidate_id",
    "latitude",
    "longitude",
    "ai_oil_score",
    "sar_score",
    "ai_oil_probability",
    "ai_prediction",
    "pixel_x",
    "pixel_y",
    "area_reduced_pixels",
    "bbox_x",
    "bbox_y",
    "bbox_width",
    "bbox_height",
    "fill_ratio",
    "aspect_ratio",
    "mean_vv_anomaly_db",
    "min_vv_anomaly_db",
    "mean_vh_anomaly_db",
    "vh_support_ratio",
]

available = [
    column
    for column in columns
    if column in spill_candidates.columns
]

spill_candidates = spill_candidates[
    available
].copy()


# ============================================================
# SORT
# ============================================================

spill_candidates = spill_candidates.sort_values(
    "ai_oil_score",
    ascending=False
)


# ============================================================
# SAVE
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

spill_candidates.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# DISPLAY
# ============================================================

print("\nFinal spill candidates:")
print("-" * 70)

for _, row in spill_candidates.iterrows():

    print(
        f"Candidate #{int(row['candidate_id'])} | "
        f"AI oil: {row['ai_oil_score']:.2f}% | "
        f"SAR: {row['sar_score']:.2f} | "
        f"Location: "
        f"{row['latitude']:.6f}, "
        f"{row['longitude']:.6f}"
    )


print("\nSaved:")
print(OUTPUT_FILE)

print("\n" + "=" * 70)
print("SPILL CANDIDATE PREPARATION COMPLETE")
print("=" * 70)