from pathlib import Path
import rasterio
import numpy as np
from PIL import Image

BASE = Path("data/raw/sentinel1/measurement")

VV_FILE = BASE / "s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.tiff"
VH_FILE = BASE / "s1d-ew-grd-vh-20260801t150156-20260801t150247-003933-0071f6-002-cog.tiff"

OUTPUT = Path("data/results/sentinel_vv_vh_preview.png")


def normalize(image):
    low = np.percentile(image, 2)
    high = np.percentile(image, 98)

    image = np.clip(image, low, high)
    image = (image - low) / (high - low)

    return image


with rasterio.open(VV_FILE) as src:
    vv = src.read(1).astype(np.float32)

with rasterio.open(VH_FILE) as src:
    vh = src.read(1).astype(np.float32)

vv = normalize(vv)
vh = normalize(vh)

# RGB visualization:
# Red = VV
# Green = VH
# Blue = VV/VH relationship
ratio = vv / (vh + 0.01)
ratio = normalize(ratio)

rgb = np.stack([vv, vh, ratio], axis=2)
rgb = (rgb * 255).astype(np.uint8)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

Image.fromarray(rgb).save(OUTPUT)

print("Preview created:")
print(OUTPUT)