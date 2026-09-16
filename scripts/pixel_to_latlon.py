from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np


XML_FILE = Path(
    r"data\raw\sentinel1\annotation"
    r"\s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.xml"
)

# AI candidate position from our previous scan
TARGET_PIXEL = 7200
TARGET_LINE = 4800


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
# Find nearest geolocation points
# --------------------------------------------------

distances = []

for p in points:

    distance = (
        (p["line"] - TARGET_LINE) ** 2
        + (p["pixel"] - TARGET_PIXEL) ** 2
    )

    distances.append((distance, p))


distances.sort(key=lambda x: x[0])

nearest = distances[:4]


# --------------------------------------------------
# Weighted interpolation
# --------------------------------------------------

weights = []
lats = []
lons = []

for distance, p in nearest:

    if distance == 0:
        weights = [1]
        lats = [p["latitude"]]
        lons = [p["longitude"]]
        break

    weight = 1 / distance

    weights.append(weight)
    lats.append(p["latitude"])
    lons.append(p["longitude"])


latitude = np.average(lats, weights=weights)
longitude = np.average(lons, weights=weights)


# --------------------------------------------------
# Result
# --------------------------------------------------

print("\nTarget image position:")
print("Pixel:", TARGET_PIXEL)
print("Line :", TARGET_LINE)

print("\nEstimated geographic position:")
print(f"Latitude : {latitude:.6f}")
print(f"Longitude: {longitude:.6f}")

print("\nNearest geolocation points:")

for distance, p in nearest:
    print(
        f"line={p['line']:.0f}, "
        f"pixel={p['pixel']:.0f}, "
        f"lat={p['latitude']:.6f}, "
        f"lon={p['longitude']:.6f}"
    )