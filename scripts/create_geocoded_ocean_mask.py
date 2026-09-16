import os

import numpy as np
import rasterio
from scipy import ndimage


# ============================================================
# CONFIG
# ============================================================

INPUT_DIR = r"data\processed\sentinel1\geocoded"
OUTPUT_DIR = r"data\results"

VV_FILE = os.path.join(
    INPUT_DIR,
    "sentinel1_vv_sigma0_db_geocoded.tif"
)

VH_FILE = os.path.join(
    INPUT_DIR,
    "sentinel1_vh_sigma0_db_geocoded.tif"
)

MASK_FILE = os.path.join(
    OUTPUT_DIR,
    "geocoded_ocean_mask.png"
)

OVERLAY_FILE = os.path.join(
    OUTPUT_DIR,
    "geocoded_ocean_mask_overlay.png"
)

os.makedirs(
    OUTPUT_DIR,
    exist_ok=True
)


# ============================================================
# MAIN
# ============================================================

print("=" * 70)
print("CREATING CONSERVATIVE GEOCODED OCEAN MASK")
print("=" * 70)


with rasterio.open(VV_FILE) as vv_src:

    vv = vv_src.read(1).astype(np.float32)

    profile = vv_src.profile.copy()

    height = vv_src.height
    width = vv_src.width

    print(f"Size: {width} x {height}")
    print(f"CRS: {vv_src.crs}")
    print(f"Bounds: {vv_src.bounds}")


with rasterio.open(VH_FILE) as vh_src:

    vh = vh_src.read(1).astype(np.float32)


# ============================================================
# VALID DATA
# ============================================================

valid = (
    np.isfinite(vv)
    &
    np.isfinite(vh)
    &
    (vv != 0)
    &
    (vh != 0)
)


# ============================================================
# LAND DETECTION
# ============================================================
#
# Land generally has much stronger SAR backscatter than
# open ocean.
#
# We use TWO conservative tests:
#
#   VV > -10 dB
#   OR
#   VH > -15 dB
#
# This is deliberately conservative. We want to remove
# obvious land rather than classify every pixel perfectly.
#


strong_vv = vv > -10.0
strong_vh = vh > -15.0

land = (
    strong_vv
    |
    strong_vh
)


land &= valid


# ============================================================
# MORPHOLOGICAL CLEANING
# ============================================================

print("\nCleaning land mask...")


# Close small holes inside land.
land = ndimage.binary_closing(
    land,
    structure=np.ones((7, 7)),
)


# Remove tiny isolated objects.
labels, num = ndimage.label(
    land
)

if num > 0:

    sizes = np.bincount(
        labels.ravel()
    )

    keep = sizes >= 500

    keep[0] = False

    land = keep[labels]


# Slightly expand land boundary so coastline pixels are
# safely excluded from oil detection.

land = ndimage.binary_dilation(
    land,
    structure=np.ones((9, 9))
)


# ============================================================
# OPEN OCEAN MASK
# ============================================================

ocean = valid & (~land)


# Remove isolated tiny ocean islands.
#
# We keep only connected ocean regions with reasonable size.

labels, num = ndimage.label(
    ocean
)

if num > 0:

    sizes = np.bincount(
        labels.ravel()
    )

    keep = sizes >= 5000

    keep[0] = False

    ocean_clean = keep[labels]

else:

    ocean_clean = ocean


# ============================================================
# SAVE MASK
# ============================================================

mask = np.zeros(
    (height, width),
    dtype=np.uint8
)

mask[ocean_clean] = 255


from PIL import Image

Image.fromarray(
    mask
).save(
    MASK_FILE
)


print(
    f"\nOcean pixels: "
    f"{np.sum(ocean_clean):,}"
)

print(
    f"Land/invalid pixels: "
    f"{height * width - np.sum(ocean_clean):,}"
)

print(
    f"Ocean coverage: "
    f"{100 * np.mean(ocean_clean):.2f}%"
)

print(
    f"\nSaved mask:"
)

print(
    MASK_FILE
)


# ============================================================
# CREATE VISUAL OVERLAY
# ============================================================

# Normalize VV for visualization.

valid_values = vv[
    valid
]

low = np.percentile(
    valid_values,
    2
)

high = np.percentile(
    valid_values,
    98
)

vv_display = np.clip(
    vv,
    low,
    high
)

vv_display = (
    (vv_display - low)
    /
    (high - low + 1e-8)
    * 255
)

vv_display = np.clip(
    vv_display,
    0,
    255
).astype(
    np.uint8
)


# Make RGB image.

overlay = np.stack(
    [
        vv_display,
        vv_display,
        vv_display
    ],
    axis=-1
)


# Darken excluded areas.

overlay[
    ~ocean_clean
] = (
    overlay[
        ~ocean_clean
    ] * 0.15
).astype(
    np.uint8
)


# Downsample for easier viewing.

scale = max(
    1,
    int(width / 1400)
)

new_width = max(
    1,
    width // scale
)

new_height = max(
    1,
    height // scale
)

overlay_img = Image.fromarray(
    overlay
)

overlay_img = overlay_img.resize(
    (new_width, new_height),
    Image.Resampling.LANCZOS
)

overlay_img.save(
    OVERLAY_FILE
)


print(
    f"Saved overlay:"
)

print(
    OVERLAY_FILE
)


print("\n" + "=" * 70)
print("OCEAN MASK COMPLETE")
print("=" * 70)ljn