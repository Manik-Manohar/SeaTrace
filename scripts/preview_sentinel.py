from pathlib import Path
import rasterio
import numpy as np
from PIL import Image

VV_FILE = Path(
    r"data\raw\sentinel1\measurement"
    r"\s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.tiff"
)

OUTPUT = Path("data/results/sentinel_vv_preview.png")

with rasterio.open(VV_FILE) as src:
    image = src.read(1)

# Remove extreme values for better visualization
low = np.percentile(image, 2)
high = np.percentile(image, 98)

image = np.clip(image, low, high)
image = ((image - low) / (high - low) * 255).astype(np.uint8)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

Image.fromarray(image).save(OUTPUT)

print("Preview created:")
print(OUTPUT)