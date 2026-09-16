from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

BASE = Path("data/raw/sentinel1/measurement")

VV_FILE = BASE / "s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.tiff"
VH_FILE = BASE / "s1d-ew-grd-vh-20260801t150156-20260801t150247-003933-0071f6-002-cog.tiff"

OUTPUT = Path("data/results/vv_vh_candidate_mask.png")

with rasterio.open(VV_FILE) as src:
    vv = src.read(1).astype(np.float32)

with rasterio.open(VH_FILE) as src:
    vh = src.read(1).astype(np.float32)

# Valid pixels
valid = (vv > 0) & (vh > 0)

# Get thresholds from valid pixels
vv_threshold = np.percentile(vv[valid], 15)
vh_threshold = np.percentile(vh[valid], 15)

print("VV threshold:", vv_threshold)
print("VH threshold:", vh_threshold)

# Dark in BOTH channels
candidate = (
    (vv <= vv_threshold) &
    (vh <= vh_threshold) &
    valid
)

mask = np.zeros(vv.shape, dtype=np.uint8)
mask[candidate] = 255

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

Image.fromarray(mask).save(OUTPUT)

print("Candidate mask created:")
print(OUTPUT)