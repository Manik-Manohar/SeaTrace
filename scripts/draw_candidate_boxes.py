from pathlib import Path

import numpy as np
import rasterio
from PIL import Image, ImageDraw

VV_FILE = Path(
    r"data\raw\sentinel1\measurement"
    r"\s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.tiff"
)

MASK_FILE = Path("data/results/clean_candidate_mask.png")
OUTPUT = Path("data/results/candidate_boxes.png")

with rasterio.open(VV_FILE) as src:
    vv = src.read(1).astype(np.float32)

valid = vv > 0

low = np.percentile(vv[valid], 2)
high = np.percentile(vv[valid], 98)

vv = np.clip(vv, low, high)
vv = ((vv - low) / (high - low) * 255).astype(np.uint8)

image = Image.fromarray(vv).convert("RGB")

mask = np.array(Image.open(MASK_FILE)) > 0

from scipy import ndimage

labels, count = ndimage.label(mask)

draw = ImageDraw.Draw(image)

region_number = 0

for i in range(1, count + 1):
    pixels = np.where(labels == i)

    if len(pixels[0]) == 0:
        continue

    area = len(pixels[0])

    if area < 500:
        continue

    y_min, y_max = pixels[0].min(), pixels[0].max()
    x_min, x_max = pixels[1].min(), pixels[1].max()

    region_number += 1

    draw.rectangle(
        [x_min, y_min, x_max, y_max],
        outline=(0, 255, 0),
        width=8
    )

    draw.text(
        (x_min, y_min),
        str(region_number),
        fill=(0, 255, 0)
    )

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

image.save(OUTPUT)

print("Candidate boxes created:")
print(OUTPUT)