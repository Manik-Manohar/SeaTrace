from pathlib import Path

import numpy as np
import rasterio
from PIL import Image

VV_FILE = Path(
    r"data\raw\sentinel1\measurement"
    r"\s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.tiff"
)

MASK_FILE = Path("data/results/clean_candidate_mask.png")
OUTPUT = Path("data/results/candidate_overlay.png")


# Read VV
with rasterio.open(VV_FILE) as src:
    vv = src.read(1).astype(np.float32)

# Make VV visible
valid = vv > 0
low = np.percentile(vv[valid], 2)
high = np.percentile(vv[valid], 98)

vv = np.clip(vv, low, high)
vv = ((vv - low) / (high - low) * 255).astype(np.uint8)

# Create grayscale RGB image
rgb = np.stack([vv, vv, vv], axis=2)

# Read candidate mask
mask = np.array(Image.open(MASK_FILE)) > 0

# Highlight candidates
rgb[mask] = [255, 0, 0]

# Save
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
Image.fromarray(rgb).save(OUTPUT)

print("Overlay created:")
print(OUTPUT)