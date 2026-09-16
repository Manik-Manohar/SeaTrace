from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

INPUT = Path("data/results/vv_vh_candidate_mask.png")
OUTPUT = Path("data/results/clean_candidate_mask.png")

mask = np.array(Image.open(INPUT))

# Convert to True/False
binary = mask > 0

# Remove tiny isolated pixels
binary = ndimage.binary_opening(binary, structure=np.ones((5, 5)))

# Join nearby candidate pixels
binary = ndimage.binary_closing(binary, structure=np.ones((9, 9)))

# Remove very small regions
labels, count = ndimage.label(binary)

clean = np.zeros(binary.shape, dtype=bool)

for i in range(1, count + 1):
    size = np.sum(labels == i)

    if size >= 500:
        clean[labels == i] = True

result = (clean * 255).astype(np.uint8)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
Image.fromarray(result).save(OUTPUT)

print("Clean candidate mask created:")
print(OUTPUT)