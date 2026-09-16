import os
import json
import requests


# ============================================================
# FILES
# ============================================================

INPUT_FILE = (
    "data/results/"
    "gfw_interaction_2026-08-01.json"
)

OUTPUT_FILE = (
    "data/results/"
    "gfw_vessel_identities_2026-08-01.json"
)


# ============================================================
# GFW SETTINGS
# ============================================================

TOKEN = os.getenv("GFW_API_TOKEN")

if not TOKEN:
    print("ERROR: GFW_API_TOKEN is not loaded.")
    raise SystemExit(1)


API_URL = (
    "https://gateway.api.globalfishingwatch.org"
    "/v3/vessels"
)

DATASET = "public-global-vessel-identity:latest"


# ============================================================
# LOAD INTERACTION RESULT
# ============================================================

print("=" * 70)
print("GFW VESSEL IDENTITY LOOKUP")
print("=" * 70)

print()
print("Loading:")
print(INPUT_FILE)
print()


if not os.path.exists(INPUT_FILE):
    print("ERROR: Interaction result file not found.")
    raise SystemExit(1)


with open(
    INPUT_FILE,
    "r",
    encoding="utf-8"
) as f:

    interaction_data = json.load(f)


# ============================================================
# EXTRACT VESSEL IDs
# ============================================================

vessel_ids = []

entries = interaction_data.get("interaction", {}).get(
    "entries",
    []
)

for entry_group in entries:

    if not isinstance(entry_group, list):
        continue

    for vessel in entry_group:

        vessel_id = vessel.get("id")

        if vessel_id and vessel_id not in vessel_ids:
            vessel_ids.append(vessel_id)


print("Vessel IDs found:", len(vessel_ids))
print()

for i, vessel_id in enumerate(vessel_ids, start=1):

    print(f"{i}. {vessel_id}")


if not vessel_ids:
    print()
    print("ERROR: No vessel IDs found.")
    raise SystemExit(1)


# ============================================================
# BUILD REQUEST
# ============================================================

params = {
    "datasets[0]": DATASET
}

for index, vessel_id in enumerate(vessel_ids):

    params[f"ids[{index}]"] = vessel_id


headers = {
    "Authorization": f"Bearer {TOKEN}"
}


# ============================================================
# REQUEST VESSEL IDENTITIES
# ============================================================

print()
print("=" * 70)
print("REQUESTING VESSEL IDENTITIES")
print("=" * 70)

print()
print("Dataset:")
print(DATASET)

print()
print("Requesting", len(vessel_ids), "vessels...")


response = requests.get(
    API_URL,
    params=params,
    headers=headers,
    timeout=120
)


print()
print("HTTP Status:", response.status_code)


# ============================================================
# HANDLE ERROR
# ============================================================

if response.status_code != 200:

    print()
    print("GFW API ERROR:")
    print(response.text)

    raise SystemExit(1)


# ============================================================
# PARSE RESPONSE
# ============================================================

data = response.json()


print()
print("=" * 70)
print("VESSEL IDENTITY RESPONSE")
print("=" * 70)

print()

print(
    json.dumps(
        data,
        indent=2
    )[:30000]
)


# ============================================================
# SAVE RESULT
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        data,
        f,
        indent=2
    )


print()
print("=" * 70)
print("SUCCESS")
print("=" * 70)

print()
print("Saved vessel identities to:")

print(OUTPUT_FILE)

print()
print("Vessel lookup complete.")