from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

MASK_FILE = Path("data/results/clean_candidate_mask.png")

mask = np.array(Image.open(MASK_FILE)) > 0

labels, count = ndimage.label(mask)

regions = []

for i in range(1, count + 1):
    pixels = np.where(labels == i)
    area = len(pixels[0])

    if area == 0:
        continue

    y_min, y_max = pixels[0].min(), pixels[0].max()
    x_min, x_max = pixels[1].min(), pixels[1].max()

    centroid_x = pixels[1].mean()
    centroid_y = pixels[0].mean()

    regions.append({
        "area_pixels": area,
        "centroid_x": round(centroid_x, 1),
        "centroid_y": round(centroid_y, 1),
        "bbox": (x_min, y_min, x_max, y_max)
    })

regions.sort(key=lambda x: x["area_pixels"], reverse=True)

print("\nCandidate regions found:", len(regions))
print("-" * 60)

for number, region in enumerate(regions, start=1):
    print(f"Region {number}")
    print(f"  Area: {region['area_pixels']} pixels")
    print(f"  Centroid: ({region['centroid_x']}, {region['centroid_y']})")
    print(f"  Bounding box: {region['bbox']}")
    print()