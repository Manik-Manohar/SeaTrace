from pathlib import Path

import rasterio
import numpy as np
from PIL import Image

VV_FILE = Path(
    r"data\raw\sentinel1\measurement"
    r"\s1d-ew-grd-vv-20260801t150156-20260801t150247-003933-0071f6-001-cog.tiff"
)

OUTPUT = Path("data/results/ai_candidate_01.png")

X = 3600
Y = 5200
SIZE = 400

with rasterio.open(VV_FILE) as src:
    tile = src.read(
        1,
        window=rasterio.windows.Window(X, Y, SIZE, SIZE)
    ).astype(np.float32)

valid = tile > 0

low = np.percentile(tile[valid], 2)
high = np.percentile(tile[valid], 98)

tile = np.clip(tile, low, high)

tile = (
    (tile - low)
    / (high - low)
    * 255
).astype(np.uint8)

Image.fromarray(tile).save(OUTPUT)

print("AI candidate crop created:")
print(OUTPUT)