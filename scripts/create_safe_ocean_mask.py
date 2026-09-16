from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

INPUT = Path("data/results/ocean_mask.png")
OUTPUT = Path("data/results/safe_ocean_mask.png")

mask = np.array(Image.open(INPUT)) > 0

# Move the ocean boundary away from the coastline
safe_ocean = ndimage.binary_erosion(
    mask,
    structure=np.ones((51, 51))
)

result = (safe_ocean * 255).astype(np.uint8)

Image.fromarray(result).save(OUTPUT)

print("Safe ocean mask created:")
print(OUTPUT)