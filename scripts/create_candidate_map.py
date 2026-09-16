from pathlib import Path
import csv
import folium


INPUT_FILE = Path("data/results/ai_candidates_localized.csv")
OUTPUT_FILE = Path("data/results/ai_candidate_map.html")


# --------------------------------------------------
# Read localized candidates
# --------------------------------------------------

candidates = []

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for row in reader:
        candidates.append({
            "candidate": int(row["candidate"]),
            "score": float(row["ai_score"]),
            "pixel": int(row["pixel"]),
            "line": int(row["line"]),
            "latitude": float(row["latitude"]),
            "longitude": float(row["longitude"])
        })


# --------------------------------------------------
# Find strongest candidate
# --------------------------------------------------

strongest = max(candidates, key=lambda x: x["score"])


# --------------------------------------------------
# Create map
# --------------------------------------------------

m = folium.Map(
    location=[
        strongest["latitude"],
        strongest["longitude"]
    ],
    zoom_start=6,
    tiles="OpenStreetMap"
)


# --------------------------------------------------
# Add candidates
# --------------------------------------------------

for candidate in candidates:

    score = candidate["score"]

    popup_text = (
        f"<b>AI Candidate #{candidate['candidate']}</b><br>"
        f"AI Score: {score:.3f}<br>"
        f"Latitude: {candidate['latitude']:.6f}<br>"
        f"Longitude: {candidate['longitude']:.6f}<br>"
        f"Pixel: {candidate['pixel']}<br>"
        f"Line: {candidate['line']}"
    )

    folium.CircleMarker(
        location=[
            candidate["latitude"],
            candidate["longitude"]
        ],
        radius=8,
        popup=popup_text,
        tooltip=f"Candidate #{candidate['candidate']} — {score:.3f}",
        fill=True
    ).add_to(m)


# --------------------------------------------------
# Highlight strongest candidate
# --------------------------------------------------

folium.Marker(
    location=[
        strongest["latitude"],
        strongest["longitude"]
    ],
    popup=(
        f"<b>Strongest AI Candidate</b><br>"
        f"Score: {strongest['score']:.3f}<br>"
        f"Latitude: {strongest['latitude']:.6f}<br>"
        f"Longitude: {strongest['longitude']:.6f}"
    ),
    tooltip="Strongest AI Candidate"
).add_to(m)


# --------------------------------------------------
# Save
# --------------------------------------------------

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

m.save(OUTPUT_FILE)

print("Map created successfully!")
print()
print("Strongest candidate:")
print(f"AI Score : {strongest['score']:.3f}")
print(f"Latitude : {strongest['latitude']:.6f}")
print(f"Longitude: {strongest['longitude']:.6f}")
print()
print("Saved:")
print(OUTPUT_FILE)