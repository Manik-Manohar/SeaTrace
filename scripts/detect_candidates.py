from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

VV_FILE = Path(
    r"data\raw\sentinel1\measurement"
    r"\s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.tiff"
)

OUTPUT = Path("data/results/candidate_mask.png")

with rasterio.open(VV_FILE) as src:
    vv = src.read(1).astype(np.float32)

# Ignore NoData pixels
valid = vv > 0

# Get values only from valid pixels
values = vv[valid]

# Find unusually dark pixels
threshold = np.percentile(values, 10)

print("Dark-pixel threshold:", threshold)

# Create mask
mask = np.zeros(vv.shape, dtype=np.uint8)
mask[(vv <= threshold) & valid] = 255

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

Image.fromarray(mask).save(OUTPUT)

print("Candidate mask created:")
print(OUTPUT)