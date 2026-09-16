from pathlib import Path

import numpy as np
import rasterio
from PIL import Image
from scipy import ndimage

VV_FILE = Path(
    r"data\raw\sentinel1\measurement"
    r"\s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.tiff"
)

OUTPUT = Path("data/results/ocean_mask.png")

with rasterio.open(VV_FILE) as src:
    vv = src.read(1).astype(np.float32)

valid = vv > 0

# Bright pixels are likely to be land in this scene
threshold = np.percentile(vv[valid], 75)

bright = (vv >= threshold) & valid

# Connect nearby bright land pixels
bright = ndimage.binary_closing(
    bright,
    structure=np.ones((15, 15))
)

# Find connected regions
labels, count = ndimage.label(bright)

land = np.zeros(vv.shape, dtype=bool)

for i in range(1, count + 1):
    size = np.sum(labels == i)

    # Keep only large regions
    if size >= 10000:
        land[labels == i] = True

# Ocean = valid pixels that are not land
ocean = valid & ~land

result = (ocean * 255).astype(np.uint8)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
Image.fromarray(result).save(OUTPUT)

print("Ocean mask created:")
print(OUTPUT)