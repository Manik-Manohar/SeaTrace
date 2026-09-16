import json
from pathlib import Path


BASE = Path(__file__).resolve().parents[1]

TIME_FILE = BASE / "data" / "results" / "gfw_time_proximity_2026-08-01.json"
IDENTITY_FILE = BASE / "data" / "results" / "gfw_vessel_identities_2026-08-01.json"
OUTPUT_FILE = BASE / "data" / "results" / "vessel_attribution_scores_2026-08-01.json"


# ============================================================
# LOAD FILES
# ============================================================

with open(TIME_FILE, "r", encoding="utf-8") as f:
    time_data = json.load(f)

with open(IDENTITY_FILE, "r", encoding="utf-8") as f:
    identity_data = json.load(f)


# ============================================================
# BUILD IDENTITY LOOKUP
# ============================================================

identity_lookup = {}

for entry in identity_data.get("entries", []):

    combined = entry.get("combinedSourcesInfo", [])

    if not combined:
        continue

    vessel_id = combined[0].get("vesselId")

    if not vessel_id:
        continue

    info = {
        "vessel_id": vessel_id,
        "name": None,
        "mmsi": None,
        "imo": None,
        "flag": None,
        "callsign": None,
        "shiptype": None,
    }

    # AIS self-reported identity
    self_reported = entry.get("selfReportedInfo", [])

    if self_reported:

        vessel = self_reported[0]

        info["name"] = vessel.get("shipname")
        info["mmsi"] = vessel.get("ssvid")
        info["imo"] = vessel.get("imo")
        info["flag"] = vessel.get("flag")
        info["callsign"] = vessel.get("callsign")

    # Combined inferred vessel type
    shiptypes = combined[0].get("shiptypes", [])

    if shiptypes:
        info["shiptype"] = shiptypes[0].get("name")

    identity_lookup[vessel_id] = info


# ============================================================
# READ TIME-PROXIMITY RESULTS
# ============================================================

rows = time_data.get("results", [])


# ============================================================
# GROUP OBSERVATIONS BY VESSEL
# ============================================================

vessels = {}

for row in rows:

    vessel_id = row.get("vessel_id")

    if not vessel_id:
        continue

    if vessel_id not in vessels:

        vessels[vessel_id] = {
            "vessel_id": vessel_id,
            "hours": 0,
            "cells": [],
            "nearest_distance_km": float("inf"),
            "nearest_cell": None,
        }

    vessel = vessels[vessel_id]

    # Sum observed hours
    vessel["hours"] += row.get("hours", 0)

    # Track unique cells
    cell = row.get("cell")

    if cell is not None and cell not in vessel["cells"]:
        vessel["cells"].append(cell)

    # Find nearest observed cell
    distance = row.get("distance_km")

    if distance is not None and distance < vessel["nearest_distance_km"]:

        vessel["nearest_distance_km"] = distance
        vessel["nearest_cell"] = cell


# ============================================================
# SCORING
# ============================================================

def spatial_score(distance):

    if distance <= 5:
        return 40

    if distance <= 15:
        return 30

    if distance <= 30:
        return 20

    if distance <= 50:
        return 10

    return 0


def presence_score(hours):

    if hours >= 4:
        return 25

    if hours >= 2:
        return 20

    if hours >= 1:
        return 15

    return 0


def consistency_score(cell_count):

    if cell_count >= 4:
        return 15

    if cell_count >= 3:
        return 12

    if cell_count >= 2:
        return 8

    if cell_count >= 1:
        return 5

    return 0


def vessel_type_score(shiptype):

    if not shiptype:
        return 5

    shiptype = shiptype.upper()

    if any(
        word in shiptype
        for word in [
            "TANKER",
            "OIL",
            "CHEMICAL",
            "CRUDE",
        ]
    ):
        return 20

    if "CARGO" in shiptype:
        return 10

    return 5


# ============================================================
# CREATE SCORED CANDIDATES
# ============================================================

candidates = []

for vessel_id, vessel in vessels.items():

    identity = identity_lookup.get(
        vessel_id,
        {
            "vessel_id": vessel_id,
            "name": None,
            "mmsi": None,
            "imo": None,
            "flag": None,
            "callsign": None,
            "shiptype": None,
        },
    )

    distance = vessel["nearest_distance_km"]
    hours = vessel["hours"]
    cell_count = len(vessel["cells"])

    s_spatial = spatial_score(distance)
    s_presence = presence_score(hours)
    s_consistency = consistency_score(cell_count)
    s_type = vessel_type_score(identity["shiptype"])

    total = (
        s_spatial
        + s_presence
        + s_consistency
        + s_type
    )

    candidates.append(
        {
            "rank": 0,

            "vessel_id": vessel_id,

            "name": identity["name"],
            "mmsi": identity["mmsi"],
            "imo": identity["imo"],
            "flag": identity["flag"],
            "callsign": identity["callsign"],
            "shiptype": identity["shiptype"],

            "nearest_distance_km": round(distance, 2),

            "nearest_cell": vessel["nearest_cell"],

            "presence_hours": hours,

            "cell_count": cell_count,

            "cells": sorted(vessel["cells"]),

            "score_breakdown": {
                "spatial": s_spatial,
                "presence": s_presence,
                "cell_consistency": s_consistency,
                "vessel_type": s_type,
            },

            "total_score": total,

            "max_score": 100,
        }
    )


# ============================================================
# SORT BY SCORE
# ============================================================

candidates.sort(
    key=lambda x: x["total_score"],
    reverse=True
)

for rank, candidate in enumerate(candidates, start=1):
    candidate["rank"] = rank


# ============================================================
# SAVE RESULTS
# ============================================================

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(candidates, f, indent=2)


# ============================================================
# DISPLAY RESULTS
# ============================================================

print()
print("=" * 70)
print("VESSEL ATTRIBUTION CANDIDATES")
print("=" * 70)

for candidate in candidates:

    print()
    print(
        f"Rank {candidate['rank']}: "
        f"{candidate['name'] or 'Unknown'}"
    )

    print(f"  Vessel ID : {candidate['vessel_id']}")
    print(f"  MMSI      : {candidate['mmsi']}")
    print(f"  IMO       : {candidate['imo']}")
    print(f"  Flag      : {candidate['flag']}")
    print(f"  Callsign  : {candidate['callsign']}")
    print(f"  Type      : {candidate['shiptype']}")

    print(
        f"  Nearest   : "
        f"{candidate['nearest_distance_km']} km"
    )

    print(
        f"  Presence  : "
        f"{candidate['presence_hours']} hours"
    )

    print(
        f"  Cells     : "
        f"{candidate['cell_count']} "
        f"{candidate['cells']}"
    )

    print(
        f"  Score     : "
        f"{candidate['total_score']}/100"
    )

    print(
        f"  Breakdown : "
        f"{candidate['score_breakdown']}"
    )

print()
print("=" * 70)
print(f"Saved: {OUTPUT_FILE}")
print("=" * 70)