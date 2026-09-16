from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np


# --------------------------------------------------
# Files
# --------------------------------------------------

XML_FILE = Path(
    r"data\raw\sentinel1\annotation"
    r"\s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.xml"
)

OUTPUT_FILE = Path("data/results/ai_candidates_localized.csv")


# --------------------------------------------------
# AI candidates from our previous Sentinel-1 scan
# --------------------------------------------------

candidates = [
    {"score": 0.193, "pixel": 7200, "line": 4800},
    {"score": 0.084, "pixel": 7200, "line": 6800},
    {"score": 0.073, "pixel": 4800, "line": 800},
    {"score": 0.062, "pixel": 4400, "line": 6400},
    {"score": 0.017, "pixel": 7200, "line": 8000},
    {"score": 0.012, "pixel": 5600, "line": 1600},
    {"score": 0.012, "pixel": 5600, "line": 800},
    {"score": 0.012, "pixel": 6000, "line": 5600},
    {"score": 0.012, "pixel": 6000, "line": 400},
    {"score": 0.009, "pixel": 6000, "line": 800},
]


# --------------------------------------------------
# Read Sentinel-1 geolocation grid
# --------------------------------------------------

tree = ET.parse(XML_FILE)
root = tree.getroot()

points = []

for point in root.iter():

    if point.tag.endswith("geolocationGridPoint"):

        values = {}

        for child in point:

            tag = child.tag.split("}")[-1]

            if tag in ["line", "pixel", "latitude", "longitude"]:
                values[tag] = float(child.text)

        if len(values) == 4:
            points.append(values)


print("Geolocation points found:", len(points))


# --------------------------------------------------
# Pixel/line -> latitude/longitude
# --------------------------------------------------

def pixel_to_latlon(target_pixel, target_line):

    distances = []

    for p in points:

        distance = (
            (p["line"] - target_line) ** 2
            + (p["pixel"] - target_pixel) ** 2
        )

        distances.append((distance, p))

    distances.sort(key=lambda x: x[0])

    nearest = distances[:4]

    weights = []
    lats = []
    lons = []

    for distance, p in nearest:

        if distance == 0:

            return p["latitude"], p["longitude"]

        weight = 1 / distance

        weights.append(weight)
        lats.append(p["latitude"])
        lons.append(p["longitude"])

    latitude = np.average(lats, weights=weights)
    longitude = np.average(lons, weights=weights)

    return latitude, longitude


# --------------------------------------------------
# Localize candidates
# --------------------------------------------------

results = []

for i, candidate in enumerate(candidates, start=1):

    latitude, longitude = pixel_to_latlon(
        candidate["pixel"],
        candidate["line"]
    )

    results.append({
        "candidate": i,
        "ai_score": candidate["score"],
        "pixel": candidate["pixel"],
        "line": candidate["line"],
        "latitude": latitude,
        "longitude": longitude
    })


# --------------------------------------------------
# Save CSV
# --------------------------------------------------

OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    f.write(
        "candidate,ai_score,pixel,line,latitude,longitude\n"
    )

    for r in results:

        f.write(
            f"{r['candidate']},"
            f"{r['ai_score']:.3f},"
            f"{r['pixel']},"
            f"{r['line']},"
            f"{r['latitude']:.6f},"
            f"{r['longitude']:.6f}\n"
        )


# --------------------------------------------------
# Display results
# --------------------------------------------------

print("\nLocalized AI candidates:")
print("-" * 75)

for r in results:

    print(
        f"Candidate {r['candidate']:2d} | "
        f"Score: {r['ai_score']:.3f} | "
        f"Pixel: {r['pixel']:4d} | "
        f"Line: {r['line']:4d} | "
        f"Lat: {r['latitude']:.6f} | "
        f"Lon: {r['longitude']:.6f}"
    )

print("\nSaved:")
print(OUTPUT_FILE)