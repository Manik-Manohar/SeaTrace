from pathlib import Path
import xml.etree.ElementTree as ET

XML_FILE = Path(
    r"data\raw\sentinel1\annotation"
    r"\s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.xml"
)

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

print("\nFirst 10 points:")
for p in points[:10]:
    print(
        f"line={p['line']:.0f}, "
        f"pixel={p['pixel']:.0f}, "
        f"lat={p['latitude']:.6f}, "
        f"lon={p['longitude']:.6f}"
    )